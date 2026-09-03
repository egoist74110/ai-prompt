#!/usr/bin/env python3
"""扫描 skills/*/SKILL.md 的 frontmatter，重建 capabilities/skills.md 的自动登记表。

用法：python3 tools/gen-index.py   （在 ~/.ai-prompt 仓库里运行，任意 cwd）
pre-commit hook 会自动调用；手工加/删 skill 后也可手动跑一次。

设计：自动登记表是「安全网」——保证 skills/ 下每个 skill 都出现在索引里
（哪怕忘了手写条目）。手写条目（带 Guardrails 的详细段）不受影响、优先级更高。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
INDEX = os.path.join(ROOT, "capabilities", "skills.md")
BEGIN = "<!-- AUTO:SKILLS:BEGIN -->"
END = "<!-- AUTO:SKILLS:END -->"


def parse_frontmatter(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return None, None
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None, None
    name = desc = None
    for line in m.group(1).splitlines():
        if line.startswith("name:"):
            name = line[5:].strip().strip("'\"")
        elif line.startswith("description:"):
            desc = line[12:].strip().strip("'\"")
    return name, desc


def main():
    entries = []
    for d in sorted(os.listdir(SKILLS)):
        skill_md = os.path.join(SKILLS, d, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        name, desc = parse_frontmatter(skill_md)
        if not name:
            name = d
        if not desc:
            desc = "（SKILL.md 缺 description，请补 frontmatter）"
        # 压缩成一行，避免索引膨胀
        desc = re.sub(r"\s+", " ", desc).strip()
        if len(desc) > 220:
            desc = desc[:220] + "…"
        entries.append(f"- `{name}`（目录 `{d}/`）：{desc}")

    block = f"{BEGIN}\n" + "\n".join(entries) + f"\n{END}"
    section = "## Auto 登记表（tools/gen-index.py 自动生成，勿手工编辑）\n\n" + block + "\n"

    if os.path.isfile(INDEX):
        with open(INDEX, encoding="utf-8") as f:
            text = f.read()
        if BEGIN in text and END in text:
            text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END),
                          lambda _m: block, text, flags=re.DOTALL)
        elif BEGIN in text:
            text = text.replace(BEGIN, block)
        else:
            text = text.rstrip() + "\n\n" + section
    else:
        text = "# Skills Index\n\n" + section

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"gen-index: {len(entries)} 个 skill 已登记到 capabilities/skills.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
