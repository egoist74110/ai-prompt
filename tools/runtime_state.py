#!/usr/bin/env python3
"""CLI for local machine runtime/state plus the extensible AI runtime registry."""
from __future__ import annotations

import argparse
import json

from local_state import FILES, LOCAL, ensure_files, get_value, migrate_local_files, read_kind, set_value, unset_value, update_kind


def _json_list(value: str, parser: argparse.ArgumentParser, label: str) -> list[str]:
    try: parsed = json.loads(value)
    except json.JSONDecodeError as exc: parser.error(f"{label} is not valid JSON: {exc}")
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed): parser.error(f"{label} must be a JSON array of strings")
    return parsed


def _optional_json_list(value: str | None, parser: argparse.ArgumentParser, label: str) -> list[str] | None:
    return None if value is None else _json_list(value, parser, label)


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init"); sub.add_parser("migrate")
    detect = sub.add_parser("detect"); detect.add_argument("--refresh", action="store_true"); detect.add_argument("--runtime")
    show = sub.add_parser("show"); show.add_argument("kind", choices=FILES)
    get = sub.add_parser("get"); get.add_argument("kind", choices=FILES); get.add_argument("key")
    setp = sub.add_parser("set"); setp.add_argument("kind", choices=FILES); setp.add_argument("key"); setp.add_argument("value", help="JSON value; strings need JSON quotes")
    unset = sub.add_parser("unset"); unset.add_argument("kind", choices=FILES); unset.add_argument("key")
    runtime_cmd = sub.add_parser("runtime", help="manage locally registered AI runtimes"); runtime_sub = runtime_cmd.add_subparsers(dest="runtime_cmd", required=True); runtime_sub.add_parser("list")
    seed = runtime_sub.add_parser("seed"); seed.add_argument("--refresh-templates", action="store_true")
    add = runtime_sub.add_parser("add", help="add or patch any local AI runtime")
    add.add_argument("name"); add.add_argument("--display-name"); add.add_argument("--runtime-identity", help="stable execution identity; aliases/wrappers of the same reviewer must share this value"); add.add_argument("--commands-json"); add.add_argument("--entries-json"); add.add_argument("--skills-json"); add.add_argument("--capabilities-json"); add.add_argument("--skills-sync-mode", choices=["per-skill-link", "central-dir-link", "none"]); add.add_argument("--auto-sync-skills", action=argparse.BooleanOptionalAction, default=None); add.add_argument("--review-args-json"); add.add_argument("--review-priority", type=int); add.add_argument("--no-detect", action="store_true")
    remove = runtime_sub.add_parser("remove"); remove.add_argument("name")
    for action in ("enable", "disable"): p = runtime_sub.add_parser(action); p.add_argument("name")
    runtime_detect = runtime_sub.add_parser("detect"); runtime_detect.add_argument("name", nargs="?"); runtime_detect.add_argument("--refresh", action="store_true")
    args = parser.parse_args(); ensure_files()

    if args.cmd in {"init", "migrate"}:
        migrate_local_files(); from runtime_registry import seed_templates
        update_kind("runtime", lambda runtime: seed_templates(runtime, force=False))
        if args.cmd == "init":
            from bootstrap import discover
            discover(refresh=False); print(str(LOCAL))
        else: print("local schema migrated")
        return 0
    if args.cmd == "detect":
        from bootstrap import discover
        try: discover(refresh=args.refresh, runtime_name=args.runtime)
        except KeyError as exc: parser.error(f"runtime is not registered: {exc.args[0]}")
        print("machine facts refreshed" if args.refresh else "machine facts discovered"); return 0

    if args.cmd == "runtime":
        from bootstrap import discover
        from runtime_registry import register_runtime, runtime_summary, seed_templates
        if args.runtime_cmd == "list": print(json.dumps(runtime_summary(read_kind("runtime")), ensure_ascii=False, indent=2)); return 0
        if args.runtime_cmd == "seed":
            holder = {"changed": False}
            update_kind("runtime", lambda runtime: holder.update(changed=seed_templates(runtime, force=args.refresh_templates)))
            print("runtime templates merged" if holder["changed"] else "runtime templates already seeded"); return 0
        if args.runtime_cmd == "add":
            def add_mut(runtime: dict) -> None:
                register_runtime(runtime, args.name, display_name=args.display_name, runtime_identity=args.runtime_identity, command_candidates=_optional_json_list(args.commands_json, parser, "--commands-json"), entry_candidates=_optional_json_list(args.entries_json, parser, "--entries-json"), skills_candidates=_optional_json_list(args.skills_json, parser, "--skills-json"), capabilities=_optional_json_list(args.capabilities_json, parser, "--capabilities-json"), skills_sync_mode=args.skills_sync_mode, auto_sync_skills=args.auto_sync_skills, review_args=_optional_json_list(args.review_args_json, parser, "--review-args-json"), review_priority=args.review_priority)
            update_kind("runtime", add_mut)
            if not args.no_detect: discover(refresh=True, runtime_name=args.name)
            print(f"runtime registered: {args.name}"); return 0
        if args.runtime_cmd == "remove":
            holder = {"found": False, "template": False}
            def remove_mut(runtime: dict) -> None:
                entries = runtime.setdefault("runtimes", {})
                if args.name not in entries: return
                holder["found"] = True
                if entries[args.name].get("source") == "template": holder["template"] = True; entries[args.name]["enabled"] = False; entries[args.name]["template_suppressed"] = True
                else: del entries[args.name]
            update_kind("runtime", remove_mut)
            if not holder["found"]: return 2
            print(f"starter runtime suppressed: {args.name}" if holder["template"] else f"runtime removed: {args.name}"); return 0
        if args.runtime_cmd in {"enable", "disable"}:
            holder = {"found": False}
            def toggle_mut(runtime: dict) -> None:
                entries = runtime.setdefault("runtimes", {})
                if args.name not in entries: return
                holder["found"] = True; entries[args.name]["enabled"] = args.runtime_cmd == "enable"
                if args.runtime_cmd == "enable": entries[args.name].pop("template_suppressed", None)
            update_kind("runtime", toggle_mut)
            if not holder["found"]: return 2
            print(f"runtime {args.runtime_cmd}d: {args.name}"); return 0
        if args.runtime_cmd == "detect":
            try: discover(refresh=args.refresh, runtime_name=args.name)
            except KeyError as exc: parser.error(f"runtime is not registered: {exc.args[0]}")
            print("runtime discovery complete"); return 0
        return 1

    if args.cmd == "show": print(json.dumps(read_kind(args.kind), ensure_ascii=False, indent=2)); return 0
    if args.cmd == "get":
        try: value = get_value(read_kind(args.kind), args.key)
        except KeyError: return 2
        print(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value); return 0
    if args.cmd == "set":
        try: value = json.loads(args.value)
        except json.JSONDecodeError as exc: parser.error(f"value is not valid JSON: {exc}")
        update_kind(args.kind, lambda data: set_value(data, args.key, value)); return 0
    if args.cmd == "unset":
        holder = {"changed": False}; update_kind(args.kind, lambda data: holder.update(changed=unset_value(data, args.key))); return 0 if holder["changed"] else 2
    return 1


if __name__ == "__main__": raise SystemExit(main())
