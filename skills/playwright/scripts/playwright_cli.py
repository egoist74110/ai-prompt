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

from local_state import migrate_local_files, read_kind, write_kind  # noqa: E402


def executable_exists(value: str) -> bool:
    path = Path(value).expanduser()
    return path.exists() or shutil.which(value) is not None


def discover_launcher() -> list[str]:
    migrate_local_files()
    runtime = read_kind("runtime")
    entry = runtime.setdefault("skills", {}).setdefault(SKILL, {})
    cached = entry.get("launcher")
    if isinstance(cached, list) and cached and executable_exists(str(cached[0])):
        return [str(x) for x in cached]

    npx = os.environ.get("PLAYWRIGHT_NPX", "").strip() or shutil.which("npx")
    if not npx:
        raise RuntimeError("未找到 npx；安装 Node.js/npm 后重试")

    launcher: list[str]
    npx_path = Path(npx)
    if os.name == "nt" and npx_path.suffix.lower() in {".cmd", ".bat"}:
        # Avoid passing user arguments through cmd.exe. Standard Node Windows installs ship
        # npx.cmd beside node.exe + node_modules/npm/bin/npx-cli.js; call the JS entry directly.
        node = npx_path.parent / "node.exe"
        npx_cli = npx_path.parent / "node_modules" / "npm" / "bin" / "npx-cli.js"
        if node.is_file() and npx_cli.is_file():
            launcher = [str(node), str(npx_cli)]
        else:
            node_cmd = shutil.which("node")
            if not node_cmd or not npx_cli.is_file():
                raise RuntimeError(
                    f"找到 {npx_path}，但无法解析安全的 Node/npx-cli 启动链；"
                    "可设置 PLAYWRIGHT_NPX 指向可直接执行的 npx launcher"
                )
            launcher = [node_cmd, str(npx_cli)]
    else:
        launcher = [str(npx)]

    entry["launcher"] = launcher
    write_kind("runtime", runtime)
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
