#!/usr/bin/env python3
"""Reject machine-specific absolute identities from central tracked text.

This is intentionally narrower than a generic path linter: generic `$HOME`, `<skill_dir>`, localhost,
service URLs and explicit legacy-discovery code are allowed. What is forbidden is baking a concrete
user/home/WSL identity into portable central rules.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SELF = Path(__file__).resolve()
ROOT = SELF.parents[1]
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml"}
IGNORE_DIRS = {".git", ".local", "__pycache__", ".venv", "node_modules"}

PATTERNS = [
    ("concrete macOS home", re.compile(r"/Users/(?![<{\$])[^/\s`'\"]+/")),
    ("concrete Linux home", re.compile(r"/home/(?![<{\$])[^/\s`'\"]+/")),
    ("concrete Windows user home", re.compile(r"[A-Za-z]:\\Users\\(?![<{%$])[^\\\s`'\"]+\\", re.I)),
    ("fixed WSL distro UNC", re.compile(r"\\\\wsl(?:\.localhost|\$)\\(?![<{%$])[^\\\s`'\"]+\\", re.I)),
]

# Historical concrete identities are kept only inside this guard file; iter_files() excludes SELF.
FORBIDDEN_LITERALS = {
    "PCMClawUbuntu": "fixed WSL distro name",
    "/Users/wesker/": "old canonical-user path",
    "C:\\Users\\wesker\\": "old Windows-user path",
}


def iter_files():
    for path in ROOT.rglob("*"):
        if path.resolve() == SELF:
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def main() -> int:
    problems = []
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

    if problems:
        print("portability check failed:", file=sys.stderr)
        for rel, lineno, label, value in problems:
            print(f"  {rel}:{lineno}: {label}: {value}", file=sys.stderr)
        print(
            "把机器事实移到 .local/runtime.json/.local/state.json；中央只保留变量、相对路径或 discovery 规则。",
            file=sys.stderr,
        )
        return 1

    print("portability check: no concrete machine identity paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
