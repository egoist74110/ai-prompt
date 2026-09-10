#!/usr/bin/env python3
"""Portable Playwright CLI launcher with local runtime caching."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = "playwright"
SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from local_state import migrate_local_files, read_kind, update_kind  # noqa: E402


def executable_exists(value: str) -> bool:
    path = Path(value).expanduser()
    return path.is_file() or shutil.which(value) is not None


def launcher_exists(launcher: list[str]) -> bool:
    if not launcher or not executable_exists(str(launcher[0])):
        return False
    # Windows safe launchers may include a JS entrypoint after node.exe.
    if len(launcher) > 1 and str(launcher[1]).lower().endswith(".js"):
        return Path(str(launcher[1])).expanduser().is_file()
    return True


def resolve_npx(npx: str) -> list[str]:
    if not executable_exists(npx):
        raise RuntimeError(f"PLAYWRIGHT_NPX/npx launcher does not exist: {npx}")
    npx_path = Path(npx).expanduser()
    if os.name == "nt" and npx_path.suffix.lower() in {".cmd", ".bat"}:
        node = npx_path.parent / "node.exe"
        npx_cli = npx_path.parent / "node_modules" / "npm" / "bin" / "npx-cli.js"
        node_cmd = str(node) if node.is_file() else shutil.which("node")
        if not node_cmd or not npx_cli.is_file():
            raise RuntimeError(
                f"Found {npx_path}, but could not resolve a safe Node/npx-cli launch chain; "
                "set PLAYWRIGHT_NPX to a directly executable npx launcher"
            )
        return [node_cmd, str(npx_cli)]
    return [str(npx)]


def cache_launcher(launcher: list[str]) -> None:
    def mutate(runtime: dict) -> None:
        runtime.setdefault("skills", {}).setdefault(SKILL, {})["launcher"] = launcher
    update_kind("runtime", mutate)


def discover_launcher() -> list[str]:
    migrate_local_files()

    # Explicit current-session configuration outranks cached machine facts.
    override = os.environ.get("PLAYWRIGHT_NPX", "").strip()
    if override:
        launcher = resolve_npx(override)
        cache_launcher(launcher)
        return launcher

    runtime = read_kind("runtime")
    cached = runtime.get("skills", {}).get(SKILL, {}).get("launcher")
    if isinstance(cached, list) and launcher_exists([str(x) for x in cached]):
        return [str(x) for x in cached]

    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx not found; install Node.js/npm and retry")
    launcher = resolve_npx(npx)
    cache_launcher(launcher)
    return launcher


def main() -> int:
    try:
        launcher = discover_launcher()
    except RuntimeError as exc:
        print(f"playwright: {exc}", file=sys.stderr)
        return 2

    args = sys.argv[1:]
    has_session = any(arg == "--session" or arg.startswith("--session=") for arg in args)
    command = launcher + ["--yes", "--package", "@playwright/cli", "playwright-cli"]
    session = os.environ.get("PLAYWRIGHT_CLI_SESSION", "").strip()
    if session and not has_session:
        command += ["--session", session]
    command += args
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
