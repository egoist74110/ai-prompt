#!/usr/bin/env python3
"""Read/write local machine runtime + verified state without third-party deps."""
from __future__ import annotations

import argparse
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


def _default_runtime() -> dict[str, Any]:
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
        },
        "credentials": {},
        "services": {},
    }


def _default_state() -> dict[str, Any]:
    return {"version": 1, "skills": {}, "mcp": {}, "services": {}}


def ensure_files() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    defaults = {"runtime": _default_runtime(), "state": _default_state()}
    for kind, path in FILES.items():
        if not path.exists():
            _write(path, defaults[kind])


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _parts(key: str) -> list[str]:
    return [p for p in key.split(".") if p]


def _get(data: dict[str, Any], key: str) -> Any:
    cur: Any = data
    for part in _parts(key):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(key)
        cur = cur[part]
    return cur


def _set(data: dict[str, Any], key: str, value: Any) -> None:
    parts = _parts(key)
    if not parts:
        raise ValueError("key cannot be empty")
    cur: dict[str, Any] = data
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _unset(data: dict[str, Any], key: str) -> bool:
    parts = _parts(key)
    if not parts:
        return False
    cur: Any = data
    for part in parts[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return isinstance(cur, dict) and cur.pop(parts[-1], None) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")

    show = sub.add_parser("show")
    show.add_argument("kind", choices=FILES)

    get = sub.add_parser("get")
    get.add_argument("kind", choices=FILES)
    get.add_argument("key")

    setp = sub.add_parser("set")
    setp.add_argument("kind", choices=FILES)
    setp.add_argument("key")
    setp.add_argument("value", help="JSON value; strings need JSON quotes")

    unset = sub.add_parser("unset")
    unset.add_argument("kind", choices=FILES)
    unset.add_argument("key")

    args = parser.parse_args()
    ensure_files()

    if args.cmd == "init":
        print(str(LOCAL))
        return 0

    path = FILES[args.kind]
    data = _read(path)

    if args.cmd == "show":
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "get":
        try:
            value = _get(data, args.key)
        except KeyError:
            return 2
        print(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
        return 0
    if args.cmd == "set":
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError as exc:
            parser.error(f"value is not valid JSON: {exc}")
        _set(data, args.key, value)
        _write(path, data)
        return 0
    if args.cmd == "unset":
        changed = _unset(data, args.key)
        if changed:
            _write(path, data)
        return 0 if changed else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
