#!/usr/bin/env python3
"""Generate shared AnySearch constants into the four CLI implementations.

Only declarative constants are generated. Runtime help/error-handling code is normal
implementation code and must not be overwritten by this generator.
"""
from __future__ import annotations

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.join(SCRIPT_DIR, "shared")
MARKERS = {
    ".py": ("# BEGIN GENERATED:{name}", "# END GENERATED:{name}"),
    ".js": ("// BEGIN GENERATED:{name}", "// END GENERATED:{name}"),
    ".ps1": ("# BEGIN GENERATED:{name}", "# END GENERATED:{name}"),
    ".sh": ("# BEGIN GENERATED:{name}", "# END GENERATED:{name}"),
}


def load_constants():
    with open(os.path.join(SHARED_DIR, "constants.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def render_constants(ext: str, constants: dict) -> str:
    domains = constants["available_domains"]
    content_types = constants["content_types"]
    freshness = constants["freshness_values"]
    zones = constants["zones"]

    if ext == ".py":
        lines = ["AVAILABLE_DOMAINS = ["]
        for i in range(0, len(domains), 6):
            lines.append("    " + ", ".join(f'\"{d}\"' for d in domains[i:i + 6]) + ",")
        lines += ["]", "", "CONTENT_TYPES = [", "    " + ", ".join(f'\"{c}\"' for c in content_types) + ",", "]", "", "FRESHNESS_VALUES = [" + ", ".join(f'\"{x}\"' for x in freshness) + "]", "ZONES = [" + ", ".join(f'\"{x}\"' for x in zones) + "]"]
        return "\n".join(lines)
    if ext == ".js":
        lines = ["const AVAILABLE_DOMAINS = ["]
        for i in range(0, len(domains), 6):
            lines.append("  " + ",".join(f'\"{d}\"' for d in domains[i:i + 6]) + ",")
        lines += ["];", "", "const CONTENT_TYPES = [", "  " + ",".join(f'\"{c}\"' for c in content_types) + ",", "];", "", "const FRESHNESS_VALUES = [" + ",".join(f'\"{x}\"' for x in freshness) + "];", "const ZONES = [" + ",".join(f'\"{x}\"' for x in zones) + "];"]
        return "\n".join(lines)
    if ext == ".ps1":
        lines = ["$AVAILABLE_DOMAINS = @("]
        chunks = [domains[i:i + 6] for i in range(0, len(domains), 6)]
        for idx, chunk in enumerate(chunks):
            lines.append("    " + ", ".join(f'\"{d}\"' for d in chunk) + ("," if idx < len(chunks) - 1 else ""))
        lines += [")", "", "$CONTENT_TYPES = @(" + ", ".join(f'\"{x}\"' for x in content_types) + ")", "$FRESHNESS_VALUES = @(" + ", ".join(f'\"{x}\"' for x in freshness) + ")", "$ZONES = @(" + ", ".join(f'\"{x}\"' for x in zones) + ")"]
        return "\n".join(lines)
    if ext == ".sh":
        return "\n".join([
            "AVAILABLE_DOMAINS=(" + " ".join(f'\"{x}\"' for x in domains) + ")",
            "CONTENT_TYPES=(" + " ".join(f'\"{x}\"' for x in content_types) + ")",
            "FRESHNESS_VALUES=(" + " ".join(f'\"{x}\"' for x in freshness) + ")",
            "ZONES=(" + " ".join(f'\"{x}\"' for x in zones) + ")",
        ])
    raise ValueError(f"unsupported extension: {ext}")


def inject(source: str, ext: str, name: str, content: str) -> str | None:
    begin = MARKERS[ext][0].format(name=name)
    end = MARKERS[ext][1].format(name=name)
    begin_idx = source.find(begin)
    end_idx = source.find(end)
    if begin_idx < 0 or end_idx < 0 or end_idx <= begin_idx:
        return None
    after_begin = source.index("\n", begin_idx) + 1
    return source[:after_begin] + content + "\n" + source[end_idx:]


def process_file(path: str, constants: dict, check_only: bool) -> bool:
    ext = os.path.splitext(path)[1]
    with open(path, "r", encoding="utf-8") as f:
        original = f.read()
    generated = inject(original, ext, "CONSTANTS", render_constants(ext, constants))
    if generated is None:
        print(f"  {os.path.basename(path)}: CONSTANTS markers missing")
        return False
    if generated == original:
        print(f"  {os.path.basename(path)}: up to date")
        return True
    if check_only:
        print(f"  {os.path.basename(path)}: OUT OF DATE")
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(generated)
    print(f"  {os.path.basename(path)}: updated")
    return True


def main() -> int:
    check_only = "--check" in sys.argv
    constants = load_constants()
    scripts = [os.path.join(SCRIPT_DIR, "anysearch_cli" + ext) for ext in (".py", ".js", ".ps1", ".sh")]
    ok = all(os.path.isfile(path) and process_file(path, constants, check_only) for path in scripts)
    if check_only and not ok:
        print("FAILED: generated constants are out of date. Run: python skills/anysearch/scripts/generate.py")
        return 1
    print("OK: generated constants are current." if check_only else "Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
