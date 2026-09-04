#!/usr/bin/env python3
"""Resolve machine-specific paths/config for bilibili-auto-transcript.

Priority: environment override > cached .local/runtime.json > one-time legacy discovery > portable default.
Secrets stay in environment/.env; this module only caches non-secret locators/settings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

SKILL_NAME = "bilibili-auto-transcript"
SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from local_state import migrate_local_files, read_kind, write_kind  # noqa: E402


def _existing_or(default: Path, *candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return default


def _runtime_entry() -> tuple[dict[str, Any], dict[str, Any]]:
    migrate_local_files()
    runtime = read_kind("runtime")
    skills = runtime.setdefault("skills", {})
    entry = skills.setdefault(SKILL_NAME, {})
    return runtime, entry


def discover_and_cache() -> dict[str, Any]:
    runtime, entry = _runtime_entry()
    changed = False

    portable_base = ROOT / ".local" / "skills" / SKILL_NAME
    legacy_state = Path.home() / ".openclaw" / "workspace" / ".auto-transcript-state"
    legacy_output = Path.home() / "workspace" / "knowledge" / "bilibili"
    legacy_db = SKILL_DIR / ".db" / "transcripts.db"

    defaults = {
        "state_dir": str(_existing_or(portable_base / "state", legacy_state)),
        "output_dir": str(_existing_or(portable_base / "output", legacy_output)),
        "db_path": str(_existing_or(portable_base / "state" / "transcripts.db", legacy_db)),
        "browser_type": "chromium",
    }

    for key, value in defaults.items():
        if not entry.get(key):
            entry[key] = value
            changed = True

    fav = os.environ.get("FAV_MEDIA_ID", "").strip()
    if fav and not entry.get("favorite_media_id"):
        entry["favorite_media_id"] = fav
        changed = True

    if changed:
        write_kind("runtime", runtime)
    return entry


def config() -> dict[str, Any]:
    return discover_and_cache()


def state_dir() -> Path:
    value = os.environ.get("BILIBILI_STATE_DIR") or config()["state_dir"]
    path = Path(value).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_dir() -> Path:
    value = os.environ.get("BILIBILI_OUTPUT_DIR") or config()["output_dir"]
    path = Path(value).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    value = os.environ.get("BILIBILI_DB_PATH") or config()["db_path"]
    path = Path(value).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def favorite_media_id() -> str:
    return os.environ.get("FAV_MEDIA_ID", "").strip() or str(config().get("favorite_media_id", "")).strip()


def browser_type() -> str:
    return os.environ.get("BILIBILI_BROWSER", "").strip() or str(config().get("browser_type", "chromium"))


def shell_exports() -> dict[str, str]:
    """Values used by the Bash transcript engine without teaching Bash to parse JSON."""
    return {
        "BILIBILI_STATE_DIR": str(state_dir()),
        "BILIBILI_OUTPUT_DIR": str(output_dir()),
        "BILIBILI_DB_PATH": str(db_path()),
        "BILIBILI_BROWSER": browser_type(),
    }


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    get = sub.add_parser("get")
    get.add_argument("key", choices=["state_dir", "output_dir", "db_path", "favorite_media_id", "browser_type"])
    args = parser.parse_args()

    if args.cmd == "show":
        payload = dict(config())
        payload.update(shell_exports())
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    values = {
        "state_dir": str(state_dir()),
        "output_dir": str(output_dir()),
        "db_path": str(db_path()),
        "favorite_media_id": favorite_media_id(),
        "browser_type": browser_type(),
    }
    print(values[args.key])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
