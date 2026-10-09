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
FILES = {"runtime": LOCAL / "runtime.json", "state": LOCAL / "state.json"}
LOCK_TIMEOUT = 10.0


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
        "environment": {"os": "macos" if system == "darwin" else system, "shell": Path(shell).name if shell else None, "is_wsl": is_wsl, "wsl_distro": os.environ.get("WSL_DISTRO_NAME") if is_wsl else None},
        "paths": {"home": str(Path.home()), "python": shutil.which("python3") or shutil.which("python"), "commands": {}},
        "runtime_registry": {}, "probe_commands": [], "credentials": {}, "services": {}, "runtimes": {}, "skills": {},
        "search": {"contexts": {}, "backends": {}},
    }


def default_state() -> dict[str, Any]:
    return {"version": 1, "skills": {}, "mcp": {}, "services": {}, "search": {"backends": {}}, "cross_review": {"runtimes": {}}, "skills_sync": {}}


def _try_lock(handle) -> bool:
    """Acquire one OS-owned exclusive byte/file lock without blocking."""
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False


def _unlock(handle) -> None:
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """Portable OS-backed cross-process lock for one local JSON document.

    The lock file is persistent; ownership is held by the OS file lock, not by file
    age. A crashed process releases ownership automatically, so another process can
    never steal a live lock or delete a successor's lock.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    handle = open(lock, "a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    deadline = time.monotonic() + LOCK_TIMEOUT
    acquired = False
    try:
        while not acquired:
            acquired = _try_lock(handle)
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for local state lock: {lock}")
            time.sleep(0.05)
        yield
    finally:
        if acquired:
            _unlock(handle)
        handle.close()


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass


def ensure_files() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    defaults = {"runtime": default_runtime(), "state": default_state()}
    for kind, path in FILES.items():
        if path.exists(): continue
        with _file_lock(path):
            if not path.exists(): _atomic_write(path, defaults[kind])


def _read_path(path: Path) -> dict[str, Any]:
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc: raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict): raise RuntimeError(f"{path} must contain a JSON object")
    return data


def read_kind(kind: str) -> dict[str, Any]:
    if kind not in FILES: raise KeyError(kind)
    ensure_files(); return _read_path(FILES[kind])


def write_kind(kind: str, data: dict[str, Any]) -> None:
    """Replace one document under a write lock. Use update_kind for read-modify-write."""
    if kind not in FILES: raise KeyError(kind)
    ensure_files(); path = FILES[kind]
    with _file_lock(path): _atomic_write(path, data)


def update_kind(kind: str, updater: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    """Atomically re-read, mutate, and replace a local document under one OS lock."""
    if kind not in FILES: raise KeyError(kind)
    ensure_files(); path = FILES[kind]
    with _file_lock(path):
        data = _read_path(path); updater(data); _atomic_write(path, data); return data


def parts(key: str) -> list[str]: return [p for p in key.split(".") if p]


def get_value(data: dict[str, Any], key: str) -> Any:
    cur: Any = data
    for part in parts(key):
        if not isinstance(cur, dict) or part not in cur: raise KeyError(key)
        cur = cur[part]
    return cur


def set_value(data: dict[str, Any], key: str, value: Any) -> None:
    path = parts(key)
    if not path: raise ValueError("key cannot be empty")
    cur: dict[str, Any] = data
    for part in path[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict): nxt = {}; cur[part] = nxt
        cur = nxt
    cur[path[-1]] = value


def unset_value(data: dict[str, Any], key: str) -> bool:
    path = parts(key)
    if not path: return False
    cur: Any = data
    for part in path[:-1]:
        if not isinstance(cur, dict) or part not in cur: return False
        cur = cur[part]
    if not isinstance(cur, dict) or path[-1] not in cur:
        return False
    del cur[path[-1]]
    return True


def merge_defaults(data: dict[str, Any], defaults: dict[str, Any]) -> bool:
    changed = False
    for key, value in defaults.items():
        if key not in data: data[key] = value; changed = True
        elif isinstance(value, dict) and isinstance(data[key], dict): changed |= merge_defaults(data[key], value)
    return changed


def migrate_local_files() -> None:
    ensure_files()
    for kind, defaults in (("runtime", default_runtime()), ("state", default_state())):
        def migrate(data: dict[str, Any], defaults=defaults) -> None: merge_defaults(data, defaults)
        update_kind(kind, migrate)


# --- document diagnostics -------------------------------------------------
# A malformed `.local` document is invisible until something writes: read_kind()
# raises on it, every tool built on it dies, and nothing reports it at rest. These
# helpers let a routine check catch it instead of the next write.

def _content_quote_spans(text: str) -> list[tuple[int, str]]:
    """Offsets of unescaped quotes sitting INSIDE a string value.

    While inside a string, a quote ends it only when the next non-space character
    is structural (, } ] :). Anything else means prose swallowed a real quote
    character -- the classic way these documents go bad. Valid JSON yields [].
    """
    spans: list[tuple[int, str]] = []
    i, n, in_str = 0, len(text), False
    while i < n:
        ch = text[i]
        if not in_str:
            if ch == '"':
                in_str = True
            i += 1
            continue
        if ch == "\\":
            i += 2
            continue
        if ch == '"':
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in ",}]:":
                in_str = False
            else:
                spans.append((i, text[max(0, i - 50):i + 50]))
            i += 1
            continue
        i += 1
    return spans


def _atomic_write_text(path: Path, text: str) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8")); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass


def diagnose(kind: str) -> list[str]:
    """Report what is wrong with one local document; [] means healthy."""
    if kind not in FILES: raise KeyError(kind)
    path = FILES[kind]
    if not path.is_file(): return [f"{kind}: {path.name} is missing ({path})"]
    try: text = path.read_bytes().decode("utf-8")
    except OSError as exc: return [f"{kind}: unreadable ({exc})"]
    except UnicodeDecodeError as exc: return [f"{kind}: not valid UTF-8 ({exc})"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        problems = [f"{kind}: invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}"]
        spans = _content_quote_spans(text)
        if spans:
            problems.append(f"{kind}: {len(spans)} unescaped quote(s) inside a string value -- escape each as a backslash-escaped quote or use CJK quotes")
            for pos, ctx in spans[:5]: problems.append(f"{kind}:   offset {pos}: ...{ctx.strip()}...")
            if len(spans) > 5: problems.append(f"{kind}:   (+{len(spans) - 5} more)")
            problems.append(f"{kind}: repair with: python tools/runtime_state.py check --fix-quotes")
        return problems
    if not isinstance(data, dict): return [f"{kind}: root must be a JSON object, found {type(data).__name__}"]
    return []


def repair_content_quotes(kind: str) -> tuple[bool, str]:
    """Escape content quotes in one document. Returns (changed, message)."""
    if kind not in FILES: raise KeyError(kind)
    path = FILES[kind]
    try: text = path.read_bytes().decode("utf-8")
    except OSError as exc: return False, f"unreadable ({exc})"
    spans = _content_quote_spans(text)
    if not spans: return False, "no unescaped quotes found"
    try:
        json.loads(text)
        return False, "document already parses; left untouched"
    except json.JSONDecodeError:
        pass
    out: list[str] = []
    i, n, in_str = 0, len(text), False
    while i < n:
        ch = text[i]
        if not in_str:
            out.append(ch)
            if ch == '"': in_str = True
            i += 1
            continue
        if ch == "\\":
            out.append(text[i:i + 2]); i += 2; continue
        if ch == '"':
            j = i + 1
            while j < n and text[j] in " \t\r\n": j += 1
            if j < n and text[j] in ",}]:":
                out.append('"'); in_str = False
            else:
                out.append('\\"')
            i += 1
            continue
        out.append(ch); i += 1
    fixed = "".join(out)
    try:
        json.loads(fixed)
    except json.JSONDecodeError as exc:
        return False, f"repair would still be invalid JSON ({exc}); left untouched"
    backup = path.with_name(path.name + ".bak-" + time.strftime("%Y%m%d-%H%M%S") + "-jsonquote")
    shutil.copy2(path, backup)
    with _file_lock(path): _atomic_write_text(path, fixed)
    return True, f"escaped {len(spans)} quote(s); backup -> {backup.name}"
