#!/usr/bin/env python3
"""Local machine runtime/state storage shared by ai-prompt tools.

Only non-secret machine facts belong here. Never store token/password/cookie/private-key bodies.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
FILES = {
    "runtime": LOCAL / "runtime.json",
    "state": LOCAL / "state.json",
}
LOCK_TIMEOUT = 10.0
STALE_LOCK_AGE = 30.0


def default_runtime() -> dict[str, Any]:
    system = platform.system().lower()
    is_wsl = False
    if system == "linux":
        try:
            is_wsl = "microsoft" in Path("/proc/version").read_text(errors="ignore").lower()
        except OSError:
            pass
    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC") or ""
    return {
        "version": 1,
        "environment": {
            "os": "macos" if system == "darwin" else system,
            "shell": Path(shell).name if shell else None,
            "is_wsl": is_wsl,
            "wsl_distro": os.environ.get("WSL_DISTRO_NAME") if is_wsl else None,
        },
        "paths": {
            "home": str(Path.home()),
            "python": shutil.which("python3") or shutil.which("python"),
            "commands": {},
        },
        "runtime_registry": {},
        "probe_commands": [],
        "credentials": {},
        "services": {},
        "runtimes": {},
        "skills": {},
        "search": {"contexts": {}, "backends": {}},
    }


def default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "skills": {},
        "mcp": {},
        "services": {},
        "search": {"backends": {}},
        "cross_review": {"runtimes": {}},
        "skills_sync": {},
    }


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """Portable short-lived cross-process lock for one local JSON file."""
    lock = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + LOCK_TIMEOUT
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}\n".encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > STALE_LOCK_AGE:
                    lock.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for local state lock: {lock}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def ensure_files() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    defaults = {"runtime": default_runtime(), "state": default_state()}
    for kind, path in FILES.items():
        if path.exists():
            continue
        with _file_lock(path):
            if not path.exists():
                _atomic_write(path, defaults[kind])


def _read_path(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return data


def read_kind(kind: str) -> dict[str, Any]:
    if kind not in FILES:
        raise KeyError(kind)
    ensure_files()
    return _read_path(FILES[kind])


def write_kind(kind: str, data: dict[str, Any]) -> None:
    """Replace one document under a write lock.

    Callers performing read-modify-write should use update_kind() instead so the
    read and write occur in the same transaction and cannot lose concurrent updates.
    """
    if kind not in FILES:
        raise KeyError(kind)
    ensure_files()
    path = FILES[kind]
    with _file_lock(path):
        _atomic_write(path, data)


def update_kind(kind: str, updater: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    """Atomically re-read, mutate, and replace a local document under one lock."""
    if kind not in FILES:
        raise KeyError(kind)
    ensure_files()
    path = FILES[kind]
    with _file_lock(path):
        data = _read_path(path)
        updater(data)
        _atomic_write(path, data)
        return data


def parts(key: str) -> list[str]:
    return [p for p in key.split(".") if p]


def get_value(data: dict[str, Any], key: str) -> Any:
    cur: Any = data
    for part in parts(key):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(key)
        cur = cur[part]
    return cur


def set_value(data: dict[str, Any], key: str, value: Any) -> None:
    path = parts(key)
    if not path:
        raise ValueError("key cannot be empty")
    cur: dict[str, Any] = data
    for part in path[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[path[-1]] = value


def unset_value(data: dict[str, Any], key: str) -> bool:
    path = parts(key)
    if not path:
        return False
    cur: Any = data
    for part in path[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return isinstance(cur, dict) and cur.pop(path[-1], None) is not None


def merge_defaults(data: dict[str, Any], defaults: dict[str, Any]) -> bool:
    """Recursively add missing default keys without overwriting user values."""
    changed = False
    for key, value in defaults.items():
        if key not in data:
            data[key] = value
            changed = True
        elif isinstance(value, dict) and isinstance(data[key], dict):
            changed |= merge_defaults(data[key], value)
    return changed


def migrate_local_files() -> None:
    """Add newly introduced schema keys to existing local files without destroying cache."""
    ensure_files()
    for kind, defaults in (("runtime", default_runtime()), ("state", default_state())):
        def migrate(data: dict[str, Any], defaults=defaults) -> None:
            merge_defaults(data, defaults)
        update_kind(kind, migrate)
