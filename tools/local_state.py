#!/usr/bin/env python3
"""Local machine runtime/state storage shared by ai-prompt tools.

Only non-secret machine facts belong here. Never store token/password/cookie/private-key bodies.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
FILES = {
    "runtime": LOCAL / "runtime.json",
    "state": LOCAL / "state.json",
}


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
        "search": {"backends": {}},
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


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def ensure_files() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    defaults = {"runtime": default_runtime(), "state": default_state()}
    for kind, path in FILES.items():
        if not path.exists():
            _atomic_write(path, defaults[kind])


def read_kind(kind: str) -> dict[str, Any]:
    if kind not in FILES:
        raise KeyError(kind)
    ensure_files()
    path = FILES[kind]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return data


def write_kind(kind: str, data: dict[str, Any]) -> None:
    if kind not in FILES:
        raise KeyError(kind)
    _atomic_write(FILES[kind], data)


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
        data = read_kind(kind)
        if merge_defaults(data, defaults):
            write_kind(kind, data)
