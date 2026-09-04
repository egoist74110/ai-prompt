#!/usr/bin/env python3
"""Portable AnySearch launcher with one-time runtime discovery and local caching."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL = "anysearch"
SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from local_state import migrate_local_files, read_kind, write_kind  # noqa: E402


def _executable_ok(command: str) -> bool:
    path = Path(command).expanduser()
    return path.exists() or shutil.which(command) is not None


def _python_has_requests() -> bool:
    return subprocess.run(
        [sys.executable, "-c", "import requests"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def discover_launcher(runtime: dict) -> list[str]:
    entry = runtime.setdefault("skills", {}).setdefault(SKILL, {})
    cached = entry.get("launcher")
    if isinstance(cached, list) and cached and _executable_ok(str(cached[0])):
        return [str(x) for x in cached]

    scripts = SKILL_DIR / "scripts"
    launcher = None

    if _python_has_requests():
        launcher = [sys.executable, str(scripts / "anysearch_cli.py")]
    else:
        node = shutil.which("node")
        if node:
            launcher = [node, str(scripts / "anysearch_cli.js")]
        elif os.name == "nt":
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell:
                launcher = [powershell, "-ExecutionPolicy", "Bypass", "-File", str(scripts / "anysearch_cli.ps1")]
        else:
            bash = shutil.which("bash") or shutil.which("sh")
            if bash:
                launcher = [bash, str(scripts / "anysearch_cli.sh")]

    if not launcher:
        raise RuntimeError("没有可用 AnySearch runtime（Python+requests / Node / PowerShell / bash）")

    entry["launcher"] = launcher
    entry["legacy_runtime_conf"] = str(SKILL_DIR / "runtime.conf") if (SKILL_DIR / "runtime.conf").exists() else None
    write_kind("runtime", runtime)
    return launcher


def main() -> int:
    migrate_local_files()
    runtime = read_kind("runtime")
    state = read_kind("state")
    try:
        launcher = discover_launcher(runtime)
    except RuntimeError as exc:
        print(f"anysearch: {exc}", file=sys.stderr)
        return 2

    proc = subprocess.run(launcher + sys.argv[1:], cwd=str(SKILL_DIR))
    skill_state = state.setdefault("skills", {}).setdefault(SKILL, {})
    if proc.returncode == 0:
        skill_state.update({
            "verified": True,
            "launcher": launcher,
            "last_verified": datetime.now(timezone.utc).isoformat(),
        })
    else:
        skill_state.update({
            "verified": False,
            "last_error_code": proc.returncode,
            "retry": "invalidate-launcher-if-runtime-error; keep launcher for query/service errors",
            "last_verified": datetime.now(timezone.utc).isoformat(),
        })
    write_kind("state", state)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
