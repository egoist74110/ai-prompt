#!/usr/bin/env python3
"""Discover stable local machine facts and resolve the data-driven runtime registry.

The code knows no AI runtime names. Starter runtimes are seeded from config/runtime-templates.json;
custom runtimes live only in .local/runtime.json and are discovered by the same generic path.
"""
from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_state import migrate_local_files, read_kind, write_kind
from runtime_registry import detect_all, seed_templates

HOME = Path.home()


def detect_environment() -> dict[str, Any]:
    system = platform.system().lower()
    is_wsl = False
    if system == "linux":
        try:
            is_wsl = "microsoft" in Path("/proc/version").read_text(errors="ignore").lower()
        except OSError:
            pass
    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC") or ""
    return {
        "os": "macos" if system == "darwin" else system,
        "shell": Path(shell).name if shell else None,
        "is_wsl": is_wsl,
        "wsl_distro": os.environ.get("WSL_DISTRO_NAME") if is_wsl else None,
    }


def discover(refresh: bool = False, runtime_name: str | None = None) -> dict[str, Any]:
    migrate_local_files()
    runtime = read_kind("runtime")

    # Seed only once. After that, the local registry is authoritative and user removals stay removed.
    seed_templates(runtime, force=False)

    runtime["environment"] = detect_environment()
    paths = runtime.setdefault("paths", {})
    paths["home"] = str(HOME)

    detect_all(runtime, refresh=refresh, only=runtime_name)

    commands = paths.setdefault("commands", {})
    preferred_python = commands.get("python3") or commands.get("python")
    if preferred_python:
        paths["python"] = preferred_python
    elif refresh:
        paths["python"] = None

    runtime.setdefault("bootstrap", {})["last_discovered"] = datetime.now(timezone.utc).isoformat()
    write_kind("runtime", runtime)
    return runtime


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="refresh cached executable/layout facts")
    parser.add_argument("--runtime", help="only detect one registered runtime id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        runtime = discover(refresh=args.refresh, runtime_name=args.runtime)
    except KeyError as exc:
        parser.error(f"runtime is not registered: {exc.args[0]}")
    if args.json:
        print(json.dumps(runtime, ensure_ascii=False, indent=2))
    else:
        print("bootstrap: runtime registry resolved into .local/runtime.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
