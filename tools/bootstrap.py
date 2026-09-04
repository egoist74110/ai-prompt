#!/usr/bin/env python3
"""Discover stable local machine facts and cache them in .local/runtime.json.

Read-only discovery outside .local: this tool does not install software, change runtime configs, or
read secret bodies. It only records executable/path/layout locators that are already visible.
"""
from __future__ import annotations

import os
import platform
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_state import ROOT, migrate_local_files, read_kind, write_kind

HOME = Path.home()

RUNTIMES = {
    "claude": {"executable": "claude", "entry": HOME / ".claude" / "CLAUDE.md", "skills": HOME / ".claude" / "skills"},
    "codex": {"executable": "codex", "entry": HOME / ".codex" / "AGENTS.md", "skills": HOME / ".codex" / "skills"},
    "gemini": {"executable": "gemini", "entry": HOME / ".gemini" / "GEMINI.md", "skills": HOME / ".gemini" / "skills"},
    "dsh": {"executable": "dsh", "entry": HOME / ".dsh" / "AGENTS.md", "skills": HOME / ".dsh" / "skills"},
    "agy": {"executable": "agy", "entry": None, "skills": None},
}

COMMANDS = (
    "git", "node", "npm", "npx", "python", "python3", "bash", "pwsh", "powershell",
    "gh", "az", "mc", "curl", "ffmpeg", "yt-dlp", "nvidia-smi",
)


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


def is_junction(path: Path) -> bool:
    fn = getattr(path, "is_junction", None)
    if fn is not None:
        try:
            return bool(fn())
        except OSError:
            return False
    if os.name != "nt":
        return False
    try:
        attrs = path.lstat().st_file_attributes
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return bool(attrs & reparse) and path.is_dir() and not path.is_symlink()
    except (AttributeError, OSError):
        return False


def is_linkish(path: Path) -> bool:
    return path.is_symlink() or is_junction(path)


def same_target(path: Path, target: Path) -> bool:
    try:
        return is_linkish(path) and os.path.normcase(str(path.resolve())) == os.path.normcase(str(target.resolve()))
    except OSError:
        return False


def detect_skills_layout(path: Path) -> str | None:
    if not (path.exists() or is_linkish(path)):
        return None
    central = ROOT / "skills"
    if same_target(path, central):
        return "central-dir-link"
    if not path.is_dir():
        return "unknown"

    managed_links = 0
    real_dirs = 0
    central_resolved = central.resolve()
    for child in path.iterdir():
        if child.name == ".system":
            continue
        if is_linkish(child):
            try:
                if child.resolve().parent == central_resolved:
                    managed_links += 1
            except OSError:
                pass
        elif child.is_dir():
            real_dirs += 1

    if managed_links and not real_dirs:
        return "per-skill-link"
    if managed_links and real_dirs:
        return "mixed"
    if real_dirs:
        return "real-dir"
    return "empty-dir"


def discover(refresh: bool = False) -> dict[str, Any]:
    migrate_local_files()
    runtime = read_kind("runtime")

    # These values describe the process actually doing discovery, so refresh them every run.
    runtime["environment"] = detect_environment()
    paths = runtime.setdefault("paths", {})
    paths["home"] = str(HOME)

    commands = paths.setdefault("commands", {})
    for name in COMMANDS:
        found = shutil.which(name)
        if found:
            if refresh or not commands.get(name):
                commands[name] = found
        elif refresh:
            commands.pop(name, None)

    preferred_python = commands.get("python3") or commands.get("python")
    if preferred_python:
        paths["python"] = preferred_python
    elif refresh:
        paths["python"] = None

    runtimes = runtime.setdefault("runtimes", {})
    for name, spec in RUNTIMES.items():
        entry = runtimes.setdefault(name, {})
        executable = shutil.which(spec["executable"])
        if executable:
            entry["executable"] = executable
        elif refresh:
            entry.pop("executable", None)

        entry_path = spec["entry"]
        if entry_path and entry_path.is_file():
            entry["entry_path"] = str(entry_path)
        elif refresh and entry_path:
            entry.pop("entry_path", None)

        skills_path = spec["skills"]
        if skills_path and (skills_path.exists() or is_linkish(skills_path)):
            entry["skills_path"] = str(skills_path)
            entry["skills_layout"] = detect_skills_layout(skills_path)
        elif refresh and skills_path:
            entry.pop("skills_path", None)
            entry.pop("skills_layout", None)

        if not entry:
            runtimes.pop(name, None)

    runtime.setdefault("bootstrap", {})["last_discovered"] = datetime.now(timezone.utc).isoformat()
    write_kind("runtime", runtime)
    return runtime


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="refresh cached executable/layout facts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    runtime = discover(refresh=args.refresh)
    if args.json:
        print(json.dumps(runtime, ensure_ascii=False, indent=2))
    else:
        print(f"bootstrap: cached machine facts in {ROOT / '.local' / 'runtime.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
