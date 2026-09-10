#!/usr/bin/env python3
"""Generate/check the AI-facing skill discovery index from skills/*/SKILL.md.

SKILL.md frontmatter is the single metadata source. capabilities/skills.md is a
machine-facing discovery cache and therefore must stay concise, English, and portable.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
INDEX = ROOT / "capabilities" / "skills.md"
ENTRY = re.compile(r"^- `([^`]+)`", re.MULTILINE)
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")


def parse_frontmatter(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, None
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return None, None
    name = desc = None
    for line in match.group(1).splitlines():
        if line.startswith("name:"):
            name = line[5:].strip().strip("'\"")
        elif line.startswith("description:"):
            desc = line[12:].strip().strip("'\"")
    return name, desc


def collect():
    entries = []
    problems = []
    for directory in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        skill_md = directory / "SKILL.md"
        if not skill_md.is_file():
            continue
        name, desc = parse_frontmatter(skill_md)
        if not name:
            name = directory.name
            problems.append(f"{skill_md.relative_to(ROOT)}: missing frontmatter name")
        if name != directory.name:
            problems.append(f"{skill_md.relative_to(ROOT)}: name `{name}` != directory `{directory.name}`")
        if not desc:
            desc = "Missing description; add it to SKILL.md frontmatter."
            problems.append(f"{skill_md.relative_to(ROOT)}: missing frontmatter description")
        desc = re.sub(r"\s+", " ", desc).strip()
        if CJK.search(desc):
            problems.append(f"{skill_md.relative_to(ROOT)}: description must be English")
        if len(desc) > 240:
            desc = desc[:240] + "..."
        entries.append((name, directory.name, desc))
    return entries, problems


def render(entries):
    lines = [
        "# Skills Index",
        "",
        "This file is for skill discovery only. `skills/<name>/SKILL.md` frontmatter is the sole metadata source.",
        "Resolve repository paths relative to the directory containing `router.md`; never store machine absolute paths here.",
        "",
        "Load a `SKILL.md` only when the user names the skill or the task clearly matches its description. Never load all skills by default.",
        "",
        "## Skills",
        "",
    ]
    for name, directory, desc in entries:
        lines.append(f"- `{name}` — `skills/{directory}/SKILL.md` — {desc}")
    lines += [
        "",
        "## Runtime / Plugin Skills",
        "",
        "Runtime-native or plugin-provided skills/tools are determined by what the current session actually exposes. Do not maintain a fixed central list or machine-local paths here.",
        "",
    ]
    return "\n".join(lines)


def check(entries, problems):
    if not INDEX.is_file():
        problems.append("capabilities/skills.md is missing")
        return problems
    text = INDEX.read_text(encoding="utf-8")
    registered = set(ENTRY.findall(text))
    expected = {name for name, _, _ in entries}
    missing = sorted(expected - registered)
    ghosts = sorted(registered - expected)
    if missing:
        problems.append("skills.md missing entries: " + ", ".join(missing))
    if ghosts:
        problems.append("skills.md contains ghost entries: " + ", ".join(ghosts))
    if CJK.search(text):
        problems.append("skills.md contains CJK text; regenerate after translating SKILL frontmatter")
    if re.search(r"(?:/Users/[^/]+|[A-Za-z]:\\\\Users\\\\[^\\]+).*?\.ai-prompt", text):
        problems.append("skills.md contains a machine absolute ai-prompt path")
    return problems


def main():
    check_only = "--check" in sys.argv[1:]
    entries, problems = collect()
    if check_only:
        problems = check(entries, problems)
        if problems:
            print("gen-index --check: failed", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(f"gen-index --check: {len(entries)} skills; discovery index is valid")
        return 0

    INDEX.write_text(render(entries), encoding="utf-8", newline="\n")
    print(f"gen-index: generated {len(entries)} skills in capabilities/skills.md")
    if problems:
        print("gen-index: frontmatter problems remain:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
