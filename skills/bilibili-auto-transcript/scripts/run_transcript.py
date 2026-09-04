#!/usr/bin/env python3
"""Portable entrypoint for the legacy Bash transcript engine.

Machine-specific Bash/output/state/browser locators come from .local/runtime.json and are cached
by runtime_config.py. This keeps agents from rediscovering paths on every invocation.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from runtime_config import (
    SKILL_DIR,
    bash_executable,
    browser_type,
    output_dir,
    shell_exports,
)

ENGINE = SKILL_DIR / "scripts" / "bilibili_transcript.sh"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--output")
    parser.add_argument("--browser")
    args = parser.parse_args()

    bash = bash_executable()
    if not bash:
        print(
            "bilibili-auto-transcript: 未找到 Bash。首次在此机器使用时请安装 Git Bash/bash，"
            "或设置 BILIBILI_BASH；成功路径会缓存到 .local/runtime.json。"
        )
        return 2

    target_output = Path(args.output).expanduser() if args.output else output_dir()
    target_output.mkdir(parents=True, exist_ok=True)
    browser = args.browser or browser_type()

    env = os.environ.copy()
    env.update(shell_exports())
    proc = subprocess.run(
        [bash, str(ENGINE), args.url, str(target_output), browser],
        cwd=str(SKILL_DIR),
        env=env,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
