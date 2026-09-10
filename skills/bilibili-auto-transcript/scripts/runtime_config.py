#!/usr/bin/env python3
"""Resolve machine-specific paths/config for bilibili-auto-transcript.

Priority: environment override > cached .local/runtime.json > one-time legacy discovery > portable default.
Secrets stay in environment/.env; this module only caches non-secret locators/settings.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

SKILL_NAME = "bilibili-auto-transcript"
SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path: sys.path.insert(0, str(TOOLS_DIR))

from local_state import migrate_local_files, update_kind  # noqa: E402


def _existing_or(default: Path, *candidates: Path) -> Path:
    return next((candidate for candidate in candidates if candidate.exists()), default)


def discover_and_cache() -> dict[str, Any]:
    migrate_local_files()
    portable_base = ROOT / ".local" / "skills" / SKILL_NAME
    defaults = {
        "state_dir": str(_existing_or(portable_base / "state", Path.home() / ".openclaw" / "workspace" / ".auto-transcript-state")),
        "output_dir": str(_existing_or(portable_base / "output", Path.home() / "workspace" / "knowledge" / "bilibili")),
        "db_path": str(_existing_or(portable_base / "state" / "transcripts.db", SKILL_DIR / ".db" / "transcripts.db")),
        "browser_type": "chromium",
    }
    bash = os.environ.get("BILIBILI_BASH", "").strip() or shutil.which("bash")
    if bash: defaults["bash"] = bash
    fav = os.environ.get("FAV_MEDIA_ID", "").strip()
    holder: dict[str, Any] = {}

    def mutate(runtime: dict[str, Any]) -> None:
        entry = runtime.setdefault("skills", {}).setdefault(SKILL_NAME, {})
        for key, value in defaults.items():
            if not entry.get(key): entry[key] = value
        if fav and not entry.get("favorite_media_id"): entry["favorite_media_id"] = fav
        holder.update(entry)

    update_kind("runtime", mutate)
    return holder


def config() -> dict[str, Any]: return discover_and_cache()


def state_dir() -> Path:
    path = Path(os.environ.get("BILIBILI_STATE_DIR") or config()["state_dir"]).expanduser(); path.mkdir(parents=True, exist_ok=True); return path


def output_dir() -> Path:
    path = Path(os.environ.get("BILIBILI_OUTPUT_DIR") or config()["output_dir"]).expanduser(); path.mkdir(parents=True, exist_ok=True); return path


def db_path() -> Path:
    path = Path(os.environ.get("BILIBILI_DB_PATH") or config()["db_path"]).expanduser(); path.parent.mkdir(parents=True, exist_ok=True); return path


def favorite_media_id() -> str: return os.environ.get("FAV_MEDIA_ID", "").strip() or str(config().get("favorite_media_id", "")).strip()
def browser_type() -> str: return os.environ.get("BILIBILI_BROWSER", "").strip() or str(config().get("browser_type", "chromium"))
def bash_executable() -> str | None: return os.environ.get("BILIBILI_BASH", "").strip() or config().get("bash") or shutil.which("bash")


def shell_exports() -> dict[str, str]:
    return {"BILIBILI_STATE_DIR": str(state_dir()), "BILIBILI_OUTPUT_DIR": str(output_dir()), "BILIBILI_DB_PATH": str(db_path()), "BILIBILI_BROWSER": browser_type()}


def main() -> int:
    import argparse, json
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="cmd", required=True); sub.add_parser("show"); get = sub.add_parser("get"); get.add_argument("key", choices=["state_dir", "output_dir", "db_path", "favorite_media_id", "browser_type", "bash"]); args = parser.parse_args()
    if args.cmd == "show":
        payload = dict(config()); payload.update(shell_exports()); print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0
    values = {"state_dir": str(state_dir()), "output_dir": str(output_dir()), "db_path": str(db_path()), "favorite_media_id": favorite_media_id(), "browser_type": browser_type(), "bash": bash_executable() or ""}
    print(values[args.key]); return 0


if __name__ == "__main__": raise SystemExit(main())
