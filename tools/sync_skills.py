#!/usr/bin/env python3
"""Sync central skills into any registered runtime that declares a skills sync mode."""
from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from local_state import ROOT, migrate_local_files, read_kind, write_kind
from platform_fs import create_dir_link, is_junction, is_linkish, link_target, points_to, remove_linkish


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def resolve_target(entry: dict) -> Path | None:
    configured = entry.get("skills_path")
    if configured:
        return _expand(str(configured))
    candidates = entry.get("skills_candidates", []) or []
    if candidates:
        return _expand(str(candidates[0]))
    return None


def _record(state: dict, runtime_name: str, central: Path, target: Path, mode: str, managed_names=None) -> None:
    record = {
        "verified": True,
        "central": str(central),
        "target": str(target),
        "mode": mode,
        "last_verified": datetime.now(timezone.utc).isoformat(),
    }
    if managed_names is not None:
        record["managed_names"] = sorted(managed_names)
    state.setdefault("skills_sync", {})[runtime_name] = record


def sync_central_dir(runtime_name: str, entry: dict, central: Path, target: Path, state: dict) -> bool:
    if points_to(target, central):
        _record(state, runtime_name, central, target, "central-dir-link")
        print(f"{runtime_name}: central skills link 已是最新")
        return False

    if target.exists() or is_linkish(target):
        raise RuntimeError(
            f"{runtime_name}: {target} 已存在且不是中央目录链接；为避免覆盖运行时私有数据，不自动替换"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    link_kind = create_dir_link(central, target)
    entry.update({"skills_path": str(target), "skills_layout": "central-dir-link", "link_kind": link_kind})
    _record(state, runtime_name, central, target, "central-dir-link")
    print(f"{runtime_name}: added central skills {link_kind}")
    return True


def sync_per_skill(runtime_name: str, entry: dict, central: Path, target: Path, state: dict) -> bool:
    if not target.exists():
        if not entry.get("executable"):
            print(f"{runtime_name}: runtime 未检测到且 skills 目录不存在，skip")
            return False
        target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise RuntimeError(f"{runtime_name}: skills target is not a directory: {target}")

    changed = False
    link_kind: str | None = None
    central_names = {p.name for p in central.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}
    previous = state.get("skills_sync", {}).get(runtime_name, {})
    previously_managed = set(previous.get("managed_names", []) or [])
    managed_now: set[str] = set()

    for name in sorted(central_names):
        source = central / name
        dest = target / name

        if is_linkish(dest):
            current = link_target(dest)
            if current == source.resolve():
                managed_now.add(name)
                if link_kind is None:
                    link_kind = "junction" if is_junction(dest) else "symlink"
                continue
            if name not in previously_managed:
                print(f"{runtime_name}: preserve unmanaged link {name}; central skill not synced")
                continue
            remove_linkish(dest)
            link_kind = create_dir_link(source, dest)
            managed_now.add(name)
            print(f"{runtime_name}: fixed managed {name}")
            changed = True
            continue

        if dest.exists():
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup = dest.with_name(f"{dest.name}.bak-{stamp}")
            shutil.move(str(dest), str(backup))
            link_kind = create_dir_link(source, dest)
            managed_now.add(name)
            print(f"{runtime_name}: replaced {name} (backup: {backup.name})")
            changed = True
            continue

        link_kind = create_dir_link(source, dest)
        managed_now.add(name)
        print(f"{runtime_name}: added {name}")
        changed = True

    # Remove only links this synchronizer previously recorded as managed. Unknown
    # dangling links may belong to private plugins or temporarily unavailable mounts.
    for name in sorted(previously_managed - central_names):
        dest = target / name
        if not is_linkish(dest):
            continue
        remove_linkish(dest)
        print(f"{runtime_name}: removed obsolete managed {name}")
        changed = True

    entry.update({
        "skills_path": str(target),
        "skills_layout": "per-skill-link",
        "link_kind": link_kind or entry.get("link_kind"),
    })
    _record(state, runtime_name, central, target, "per-skill-link", managed_now)
    print(f"{runtime_name}: skills 同步完成" if changed else f"{runtime_name}: skills 已是最新")
    return changed


def sync(runtime_name: str) -> int:
    migrate_local_files()
    runtime = read_kind("runtime")
    state = read_kind("state")
    entries = runtime.setdefault("runtimes", {})
    if runtime_name not in entries:
        raise KeyError(runtime_name)

    entry = entries[runtime_name]
    if not entry.get("enabled", True):
        print(f"{runtime_name}: disabled, skip")
        return 0

    mode = entry.get("skills_sync_mode", "none")
    if mode in (None, "none"):
        print(f"{runtime_name}: no skills sync mode, skip")
        return 0

    target = resolve_target(entry)
    if target is None:
        print(f"{runtime_name}: no skills path/candidates, skip")
        return 0

    central = ROOT / "skills"
    if not central.is_dir():
        raise RuntimeError(f"central skills directory missing: {central}")

    if mode == "central-dir-link":
        sync_central_dir(runtime_name, entry, central, target, state)
    elif mode == "per-skill-link":
        sync_per_skill(runtime_name, entry, central, target, state)
    else:
        raise RuntimeError(f"{runtime_name}: unsupported skills_sync_mode: {mode}")

    write_kind("runtime", runtime)
    write_kind("state", state)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--runtime", help="registered runtime id")
    group.add_argument("--all", action="store_true", help="sync all eligible registered runtimes")
    parser.add_argument("--auto-only", action="store_true", help="with --all, only entries with auto_sync_skills=true")
    args = parser.parse_args()

    runtime = read_kind("runtime")
    if args.runtime:
        names = [args.runtime]
    else:
        names = [
            name
            for name, entry in runtime.get("runtimes", {}).items()
            if isinstance(entry, dict)
            and entry.get("enabled", True)
            and entry.get("skills_sync_mode") not in (None, "none")
            and (not args.auto_only or entry.get("auto_sync_skills", False))
        ]

    failed = False
    for name in names:
        try:
            sync(name)
        except KeyError:
            print(f"sync-skills: runtime not registered: {name}")
            failed = True
        except Exception as exc:
            print(f"sync-skills: {name}: {exc}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
