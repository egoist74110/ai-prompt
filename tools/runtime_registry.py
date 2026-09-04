#!/usr/bin/env python3
"""Data-driven AI runtime registry.

Runtime names are data, never code branches. Starter entries come from
config/runtime-templates.json only during initialization; users may add any CLI/runtime locally.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_state import ROOT
from platform_fs import is_linkish, points_to

TEMPLATE_FILE = ROOT / "config" / "runtime-templates.json"


def load_template_catalog(path: Path = TEMPLATE_FILE) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"runtime template root must be an object: {path}")
    runtimes = data.get("runtimes", {})
    if not isinstance(runtimes, dict):
        raise RuntimeError(f"runtime template runtimes must be an object: {path}")
    return data


def _merge_missing(target: dict[str, Any], defaults: dict[str, Any]) -> bool:
    """Recursively add missing template fields without replacing local values."""
    changed = False
    for key, value in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
            changed = True
        elif isinstance(value, dict) and isinstance(target[key], dict):
            changed |= _merge_missing(target[key], value)
    return changed


def seed_templates(runtime: dict[str, Any], force: bool = False) -> bool:
    """Seed/migrate starter specs without overwriting local edits.

    On the first seed, pre-registry entries from older schema versions receive only the missing
    declarative fields from matching starter templates. Entries explicitly marked source=user are
    never template-merged. force=True allows newly added starter entries/fields to be merged later.
    """
    catalog = load_template_catalog()
    meta = runtime.setdefault("runtime_registry", {})
    already_seeded = bool(meta.get("templates_seeded"))
    if already_seeded and not force:
        return False

    changed = False
    entries = runtime.setdefault("runtimes", {})
    for name, spec in catalog.get("runtimes", {}).items():
        if name not in entries:
            item = copy.deepcopy(spec)
            item.setdefault("enabled", True)
            item.setdefault("source", "template")
            entries[name] = item
            changed = True
            continue

        existing = entries[name]
        if not isinstance(existing, dict):
            continue
        # Old discovered entries had no source marker. Treat them as template-derived for migration.
        if existing.get("source") == "user":
            continue
        changed |= _merge_missing(existing, spec)
        if "source" not in existing:
            existing["source"] = "template"
            changed = True
        if "enabled" not in existing:
            existing["enabled"] = True
            changed = True

    probes = runtime.setdefault("probe_commands", [])
    if not isinstance(probes, list):
        probes = []
        runtime["probe_commands"] = probes
        changed = True
    for command in catalog.get("support_commands", []):
        if command not in probes:
            probes.append(command)
            changed = True

    new_meta = {
        "templates_seeded": True,
        "template_version": catalog.get("version", 1),
        "template_source": "config/runtime-templates.json",
    }
    if any(meta.get(k) != v for k, v in new_meta.items()):
        meta.update(new_meta)
        changed = True
    return changed


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def _resolve_command(candidate: str) -> str | None:
    expanded = os.path.expandvars(os.path.expanduser(candidate))
    if any(sep in expanded for sep in (os.sep, "/", "\\")):
        path = Path(expanded)
        if path.is_file():
            return str(path.resolve())
    return shutil.which(expanded)


def _first_existing_path(candidates: list[str], *, want_dir: bool) -> Path | None:
    for raw in candidates:
        path = _expand_path(raw)
        if want_dir:
            if path.is_dir() or is_linkish(path):
                return path
        elif path.is_file():
            return path
    return None


def detect_skills_layout(path: Path) -> str:
    central = ROOT / "skills"
    if points_to(path, central):
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


def detect_runtime(name: str, entry: dict[str, Any], refresh: bool = False) -> bool:
    """Resolve one registry entry. Returns whether the entry changed."""
    before = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    if not entry.get("enabled", True):
        return False

    executable = entry.get("executable")
    if executable:
        resolved_existing = _resolve_command(str(executable))
        if resolved_existing:
            entry["executable"] = resolved_existing
        else:
            executable = None
    if not executable:
        resolved = None
        for candidate in entry.get("command_candidates", []) or []:
            resolved = _resolve_command(str(candidate))
            if resolved:
                break
        if resolved:
            entry["executable"] = resolved
        elif refresh:
            entry.pop("executable", None)

    current_entry = entry.get("entry_path")
    if not (current_entry and _expand_path(str(current_entry)).is_file()):
        found = _first_existing_path(
            [str(x) for x in (entry.get("entry_candidates", []) or [])], want_dir=False
        )
        if found:
            entry["entry_path"] = str(found)
        elif refresh:
            entry.pop("entry_path", None)

    current_skills = entry.get("skills_path")
    current_skills_path = _expand_path(str(current_skills)) if current_skills else None
    if not (current_skills_path and (current_skills_path.is_dir() or is_linkish(current_skills_path))):
        found = _first_existing_path(
            [str(x) for x in (entry.get("skills_candidates", []) or [])], want_dir=True
        )
        if found:
            entry["skills_path"] = str(found)
            current_skills_path = found
        elif refresh:
            entry.pop("skills_path", None)
            entry.pop("skills_layout", None)
            current_skills_path = None

    if current_skills_path and (current_skills_path.is_dir() or is_linkish(current_skills_path)):
        entry["skills_layout"] = detect_skills_layout(current_skills_path)

    entry["last_detected"] = datetime.now(timezone.utc).isoformat()
    after = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    return before != after


def detect_all(runtime: dict[str, Any], refresh: bool = False, only: str | None = None) -> bool:
    changed = False
    entries = runtime.setdefault("runtimes", {})
    if only is not None:
        if only not in entries:
            raise KeyError(only)
        targets = [(only, entries[only])]
    else:
        targets = list(entries.items())

    for name, entry in targets:
        if isinstance(entry, dict):
            changed |= detect_runtime(name, entry, refresh=refresh)

    commands = runtime.setdefault("paths", {}).setdefault("commands", {})
    probe_names = set(str(x) for x in (runtime.get("probe_commands", []) or []))
    for entry in entries.values():
        if isinstance(entry, dict):
            probe_names.update(str(x) for x in (entry.get("command_candidates", []) or []))

    for name in sorted(probe_names):
        found = _resolve_command(name)
        if found:
            if commands.get(name) != found:
                commands[name] = found
                changed = True
        elif refresh and name in commands:
            commands.pop(name, None)
            changed = True
    return changed


def register_runtime(
    runtime: dict[str, Any],
    name: str,
    *,
    display_name: str | None = None,
    command_candidates: list[str] | None = None,
    entry_candidates: list[str] | None = None,
    skills_candidates: list[str] | None = None,
    capabilities: list[str] | None = None,
    skills_sync_mode: str | None = None,
    auto_sync_skills: bool | None = None,
    review_args: list[str] | None = None,
    review_priority: int | None = None,
) -> dict[str, Any]:
    entries = runtime.setdefault("runtimes", {})
    is_new = name not in entries
    entry = entries.setdefault(name, {})
    entry["source"] = "user"
    entry["enabled"] = True
    if display_name is not None:
        entry["display_name"] = display_name
    if command_candidates is not None:
        entry["command_candidates"] = command_candidates
    if entry_candidates is not None:
        entry["entry_candidates"] = entry_candidates
    if skills_candidates is not None:
        entry["skills_candidates"] = skills_candidates
    if capabilities is not None:
        entry["capabilities"] = capabilities
    elif is_new:
        entry["capabilities"] = ["agent"]
    if skills_sync_mode is not None:
        entry["skills_sync_mode"] = skills_sync_mode
    if auto_sync_skills is not None:
        entry["auto_sync_skills"] = auto_sync_skills
    if review_args is not None or review_priority is not None:
        review = entry.setdefault("review", {})
        if review_args is not None:
            review["args"] = review_args
        if review_priority is not None:
            review["priority"] = review_priority
        caps = entry.setdefault("capabilities", [])
        if "review" not in caps:
            caps.append("review")
    return entry


def runtime_summary(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, entry in sorted(runtime.get("runtimes", {}).items()):
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "name": name,
                "display_name": entry.get("display_name", name),
                "enabled": entry.get("enabled", True),
                "executable": entry.get("executable"),
                "entry_path": entry.get("entry_path"),
                "skills_path": entry.get("skills_path"),
                "capabilities": entry.get("capabilities", []),
                "review_priority": entry.get("review", {}).get("priority"),
                "source": entry.get("source"),
            }
        )
    return rows
