#!/usr/bin/env python3
"""Sync central skills into a runtime-specific skills directory.

Currently used for Codex. Core logic is Python so Windows/macOS/Linux/WSL share one implementation.
"""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from local_state import ROOT, migrate_local_files, read_kind, write_kind
from platform_fs import create_dir_link, is_junction, is_linkish, link_target, remove_linkish


def resolve_target(runtime: dict, runtime_name: str) -> Path:
    configured = runtime.get("runtimes", {}).get(runtime_name, {}).get("skills_path")
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

    runtime_entry = runtime.setdefault("runtimes", {}).setdefault(runtime_name, {})
    runtime_entry.update(
        {
            "skills_path": str(target),
            "skills_layout": "per-skill-link",
            "link_kind": link_kind or runtime_entry.get("link_kind"),
        }
    )
    state.setdefault("skills_sync", {})[runtime_name] = {
        "verified": True,
        "central": str(central),
        "target": str(target),
        "last_verified": datetime.now(timezone.utc).isoformat(),
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
