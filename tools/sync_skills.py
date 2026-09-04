#!/usr/bin/env python3
"""Sync central skills into a runtime-specific skills directory.

Currently used for Codex. Core logic is Python so Windows/macOS/Linux/WSL share one implementation.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from local_state import ROOT, migrate_local_files, read_kind, set_value, write_kind


def is_windows() -> bool:
    return os.name == "nt"


def is_junction(path: Path) -> bool:
    fn = getattr(path, "is_junction", None)
    return bool(fn and fn())


def is_linkish(path: Path) -> bool:
    return path.is_symlink() or is_junction(path)


def remove_linkish(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif is_junction(path):
        os.rmdir(path)
    else:
        raise RuntimeError(f"not a link/junction: {path}")


def link_target(path: Path) -> Path | None:
    try:
        if path.is_symlink():
            raw = os.readlink(path)
            return (path.parent / raw).resolve() if not os.path.isabs(raw) else Path(raw).resolve()
        if is_junction(path):
            return path.resolve()
    except OSError:
        return None
    return None


def create_dir_link(target: Path, link: Path) -> str:
    if is_windows():
        # Directory junction avoids Windows symlink privilege / Developer Mode requirements.
        subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        return "junction"
    link.symlink_to(target, target_is_directory=True)
    return "symlink"


def resolve_target(runtime: dict, runtime_name: str) -> Path:
    configured = (
        runtime.get("runtimes", {})
        .get(runtime_name, {})
        .get("skills_path")
    )
    if configured:
        return Path(configured).expanduser()
    if runtime_name == "codex":
        return Path.home() / ".codex" / "skills"
    raise ValueError(f"no default skills path for runtime: {runtime_name}")


def sync(runtime_name: str) -> int:
    migrate_local_files()
    runtime = read_kind("runtime")
    state = read_kind("state")

    central = ROOT / "skills"
    target = resolve_target(runtime, runtime_name)

    if not central.is_dir():
        raise RuntimeError(f"central skills directory missing: {central}")
    if not target.is_dir():
        print(f"sync-skills: runtime skills directory not found, skip: {target}")
        return 0

    changed = False
    link_kind: str | None = None
    central_names = {p.name for p in central.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}

    for name in sorted(central_names):
        source = central / name
        dest = target / name

        if is_linkish(dest):
            current = link_target(dest)
            if current == source.resolve():
                if link_kind is None:
                    link_kind = "junction" if is_junction(dest) else "symlink"
                continue
            remove_linkish(dest)
            link_kind = create_dir_link(source, dest)
            print(f"fixed: {name}")
            changed = True
            continue

        if dest.exists():
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup = dest.with_name(f"{dest.name}.bak-{stamp}")
            shutil.move(str(dest), str(backup))
            link_kind = create_dir_link(source, dest)
            print(f"replaced: {name} (backup: {backup.name})")
            changed = True
            continue

        link_kind = create_dir_link(source, dest)
        print(f"added: {name}")
        changed = True

    # Remove only dangling managed links. Never delete real directories or runtime-owned .system.
    for dest in target.iterdir():
        if dest.name == ".system" or not is_linkish(dest):
            continue
        current = link_target(dest)
        if current is None or not current.exists():
            remove_linkish(dest)
            print(f"removed dangling: {dest.name}")
            changed = True

    runtime.setdefault("runtimes", {}).setdefault(runtime_name, {}).update(
        {
            "skills_path": str(target),
            "skills_layout": "per-skill-link",
            "link_kind": link_kind or runtime.get("runtimes", {}).get(runtime_name, {}).get("link_kind"),
        }
    )
    state.setdefault("skills_sync", {})[runtime_name] = {
        "verified": True,
        "central": str(central),
        "target": str(target),
    }
    write_kind("runtime", runtime)
    write_kind("state", state)

    print("sync-skills: 完成" if changed else "sync-skills: 已是最新")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default="codex", choices=["codex"])
    args = parser.parse_args()
    return sync(args.runtime)


if __name__ == "__main__":
    raise SystemExit(main())
