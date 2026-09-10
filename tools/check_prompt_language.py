#!/usr/bin/env python3
"""Reject CJK prose from AI-facing prompt documents.

Human-facing README/CONTRIBUTING docs are intentionally outside this guard.
Business data, fixtures, scripts, and reference docs are not classified here unless
explicitly added to AI_FILE_PATTERNS.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AI_FILES = [
    ROOT / "router.md",
    ROOT / "common.md",
]
AI_DIR_PATTERNS = [
    (ROOT / "models", "*.md"),
    (ROOT / "capabilities", "*.md"),
    (ROOT / "skills", "*/SKILL.md"),
]

# Han + Hiragana + Katakana + Hangul. AI-facing instructions should be English.
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")

# Keep narrowly scoped exceptions for literal user-facing output/examples only.
# Prefer removing an exception once the machine document no longer needs it.
ALLOW_LINE_PATTERNS = [
    re.compile(r"Simplified Chinese", re.I),
]


def iter_ai_files():
    seen: set[Path] = set()
    for path in AI_FILES:
        if path.is_file() and path not in seen:
            seen.add(path)
            yield path
    for base, pattern in AI_DIR_PATTERNS:
        if not base.is_dir():
            continue
        for path in sorted(base.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def main() -> int:
    problems: list[tuple[Path, int, str]] = []
    for path in iter_ai_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"cannot read {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
            return 2
        for lineno, line in enumerate(lines, 1):
            if not CJK.search(line):
                continue
            if any(pattern.search(line) for pattern in ALLOW_LINE_PATTERNS):
                continue
            problems.append((path.relative_to(ROOT), lineno, line.strip()[:180]))

    if problems:
        print("AI-facing language check failed: CJK text found in machine instructions.", file=sys.stderr)
        for rel, lineno, excerpt in problems:
            print(f"  {rel}:{lineno}: {excerpt}", file=sys.stderr)
        print(
            "Use concise English for AI-facing instructions. Put human explanations in README/CONTRIBUTING docs.",
            file=sys.stderr,
        )
        return 1

    print("AI-facing language check: machine instructions are English")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
