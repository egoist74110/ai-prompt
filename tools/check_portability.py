#!/usr/bin/env python3
"""Reject machine identities and runtime-name hardcoding from portable core code."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SELF = Path(__file__).resolve()
ROOT = SELF.parents[1]
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml"}
IGNORE_DIRS = {".git", ".local", "__pycache__", ".venv", "node_modules"}

# Real usernames are alnum/._- ; this excludes regex-literal snippets like "[^/]+" that
# other guard/check scripts embed as *examples* of the very paths being forbidden here.
USERNAME = r"[A-Za-z0-9_.\-]+"

PATTERNS = [
    ("concrete macOS home", re.compile(r"/Users/(?![<{\$])" + USERNAME + "/")),
    ("concrete Linux home", re.compile(r"/home/(?![<{\$])" + USERNAME + "/")),
    ("concrete Windows user home", re.compile(r"[A-Za-z]:\\Users\\(?![<{%$])" + USERNAME + r"\\", re.I)),
    ("fixed WSL distro UNC", re.compile(r"\\\\wsl(?:\.localhost|\$)\\(?![<{%$])" + USERNAME + r"\\", re.I)),
]

# Historical concrete identities are kept only inside this guard file; iter_files() excludes SELF.
FORBIDDEN_LITERALS = {
    "PCMClawUbuntu": "fixed WSL distro name",
    "/Users/wesker/": "old canonical-user path",
    "C:\\Users\\wesker\\": "old Windows-user path",
}

# These consumers must remain completely data-driven. Runtime ids may exist in starter template data,
# but must never return as string constants in runtime orchestration code.
RUNTIME_CONSUMERS = [
    ROOT / "tools" / "bootstrap.py",
    ROOT / "tools" / "doctor.py",
    ROOT / "tools" / "sync_skills.py",
    ROOT / "tools" / "runtime_state.py",
    ROOT / "tools" / "runtime_registry.py",
]
RUNTIME_TEMPLATE = ROOT / "config" / "runtime-templates.json"


def iter_files():
    for path in ROOT.rglob("*"):
        if path.resolve() == SELF:
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def starter_runtime_ids() -> list[str]:
    try:
        data = json.loads(RUNTIME_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    runtimes = data.get("runtimes", {}) if isinstance(data, dict) else {}
    return sorted(runtimes) if isinstance(runtimes, dict) else []


def check_runtime_name_hardcoding(problems: list[tuple[Path, int, str, str]]) -> None:
    runtime_ids = starter_runtime_ids()
    for path in RUNTIME_CONSUMERS:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(text.splitlines(), 1):
            for runtime_id in runtime_ids:
                # Match a runtime id used as a Python/shell string literal. Incidental prose substrings do not count.
                pattern = re.compile(rf"(['\"]){re.escape(runtime_id)}\1", re.I)
                if pattern.search(line):
                    problems.append((rel, lineno, "hardcoded starter runtime id in core consumer", runtime_id))


def main() -> int:
    problems: list[tuple[Path, int, str, str]] = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS:
                match = pattern.search(line)
                if match:
                    problems.append((rel, lineno, label, match.group(0)))
            for literal, label in FORBIDDEN_LITERALS.items():
                if literal in line:
                    problems.append((rel, lineno, label, literal))

    check_runtime_name_hardcoding(problems)

    if problems:
        print("portability check failed:", file=sys.stderr)
        for rel, lineno, label, value in problems:
            print(f"  {rel}:{lineno}: {label}: {value}", file=sys.stderr)
        print(
            "机器事实放 .local；runtime 名字只允许作为 registry/template 数据，不得写回核心消费者分支。",
            file=sys.stderr,
        )
        return 1

    print("portability check: machine identities and runtime consumers are data-driven")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
