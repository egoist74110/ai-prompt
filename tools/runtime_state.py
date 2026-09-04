#!/usr/bin/env python3
"""CLI for reading/writing local machine runtime + verified state."""
from __future__ import annotations

import argparse
import json

from local_state import (
    FILES,
    LOCAL,
    ensure_files,
    get_value,
    migrate_local_files,
    read_kind,
    set_value,
    unset_value,
    write_kind,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("migrate")

    show = sub.add_parser("show")
    show.add_argument("kind", choices=FILES)

    get = sub.add_parser("get")
    get.add_argument("kind", choices=FILES)
    get.add_argument("key")

    setp = sub.add_parser("set")
    setp.add_argument("kind", choices=FILES)
    setp.add_argument("key")
    setp.add_argument("value", help="JSON value; strings need JSON quotes")

    unset = sub.add_parser("unset")
    unset.add_argument("kind", choices=FILES)
    unset.add_argument("key")

    args = parser.parse_args()
    ensure_files()

    if args.cmd == "init":
        migrate_local_files()
        print(str(LOCAL))
        return 0
    if args.cmd == "migrate":
        migrate_local_files()
        print("local schema migrated")
        return 0

    data = read_kind(args.kind)

    if args.cmd == "show":
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "get":
        try:
            value = get_value(data, args.key)
        except KeyError:
            return 2
        print(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
        return 0
    if args.cmd == "set":
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError as exc:
            parser.error(f"value is not valid JSON: {exc}")
        set_value(data, args.key, value)
        write_kind(args.kind, data)
        return 0
    if args.cmd == "unset":
        changed = unset_value(data, args.key)
        if changed:
            write_kind(args.kind, data)
        return 0 if changed else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
