#!/usr/bin/env python3
"""Generate/check a portable skill discovery index from skills/*/SKILL.md.

SKILL.md frontmatter is the single metadata source. capabilities/skills.md is only a
lightweight discovery cache; it must not contain machine-specific absolute paths.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
INDEX = ROOT / "capabilities" / "skills.md"
ENTRY = re.compile(r"^- `([^`]+)`", re.MULTILINE)


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
            problems.append(f"{skill_md.relative_to(ROOT)}: 缺 frontmatter name")
        if name != directory.name:
            problems.append(
                f"{skill_md.relative_to(ROOT)}: name `{name}` != 目录名 `{directory.name}`"
            )
        if not desc:
            desc = "（缺 description，请补 SKILL.md frontmatter）"
        desc = re.sub(r"\s+", " ", desc).strip()
        if len(desc) > 240:
            desc = desc[:240] + "…"
        entries.append((name, directory.name, desc))
    return entries, problems


def render(entries):
    lines = [
        "# Skills Index",
        "",
        "本文件只负责 **skill 发现**。`skills/<name>/SKILL.md` frontmatter 才是唯一元数据源；",
        "仓库内路径全部相对 `router.md` 所在目录解析，本索引禁止保存机器绝对路径。",
        "",
        "规则：只有用户点名 skill，或任务明显匹配 description 时，才读取对应 `SKILL.md`；不要全量读取。",
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
        "运行时原生或插件提供的 skill/tool 以**当前会话实际暴露**为准，不在本仓库维护固定清单或本机路径。",
        "",
    ]
    return "\n".join(lines)


def check(entries, problems):
    if not INDEX.is_file():
        problems.append("capabilities/skills.md 不存在")
        return problems
    text = INDEX.read_text(encoding="utf-8")
    registered = set(ENTRY.findall(text))
    expected = {name for name, _, _ in entries}
    missing = sorted(expected - registered)
    ghosts = sorted(registered - expected)
    if missing:
        problems.append("skills.md 漏登记: " + ", ".join(missing))
    if ghosts:
        problems.append("skills.md 幽灵条目: " + ", ".join(ghosts))
    if re.search(r"(?:/Users/[^/]+|[A-Za-z]:\\\\Users\\\\[^\\]+).*?\.ai-prompt", text):
        problems.append("skills.md 含机器绝对 ai-prompt 路径，应改成 skills/<name>/... 相对路径")
    return problems


def main():
    check_only = "--check" in sys.argv[1:]
    entries, problems = collect()
    if check_only:
        problems = check(entries, problems)
        if problems:
            print("gen-index --check: 未通过", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(f"gen-index --check: {len(entries)} 个 skill，发现索引完整")
        return 0

    INDEX.write_text(render(entries), encoding="utf-8")
    print(f"gen-index: {len(entries)} 个 skill 已生成到 capabilities/skills.md")
    if problems:
        print("gen-index: frontmatter 仍有问题：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
