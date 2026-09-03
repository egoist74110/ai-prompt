#!/usr/bin/env python3
"""扫描 skills/*/SKILL.md 的 frontmatter，重建 capabilities/skills.md 的自动登记表。

用法：python3 tools/gen-index.py            （重建索引并落盘）
      python3 tools/gen-index.py --check    （只比对+校验，不改任何文件；doctor.sh 用这个）
      两种模式都在 ~/.ai-prompt 仓库里运行，任意 cwd
pre-commit hook 会自动调用；手工加/删 skill 后也可手动跑一次。

设计：自动登记表是「安全网」——保证 skills/ 下每个 skill 都出现在索引里
（哪怕忘了手写条目）。手写条目（带 Guardrails 的详细段）不受影响、优先级更高。

除了「防漏」，还做两项「防多 / 防对不上」校验，发现问题以退出码 1 结束
（pre-commit 会因此拦下提交）：
  1. 手写段里出现的 skill 名，必须在 skills/ 下有同名目录——否则就是幽灵条目
     （历史上 ui-ux-pro-max / knowledge-rag 就是这样在索引里活了很久）。
  2. SKILL.md frontmatter 的 name 必须等于目录名——不一致时运行时按目录名加载、
     索引按 name 显示，两边对不上。
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


# 手写段里允许出现、但故意不落地成 skills/ 目录的名字
# （运行时插件/连接器 skill，由运行时自己提供，见 skills.md「Runtime Plugin Skills」）
PLUGIN_WHITELIST = {
    "github", "gh-fix-ci", "gh-address-comments", "yeet",
    "documents", "spreadsheets", "presentations",
    "control-in-app-browser", "control-chrome", "computer-use",
}
# 只在这些手写段里查幽灵条目（Runtime Plugin Skills 段之前的部分）
HANDWRITTEN_END = "## Runtime Plugin Skills"
# 顶层条目名：允许 `name` 后面跟说明文字，不再要求整行只有反引号名
BULLET = re.compile(r"^- +`([A-Za-z0-9][A-Za-z0-9._-]*)`", re.MULTILINE)
# 结构锚点：带缩进的 "- Path:" 行，是一条 skill 登记的可靠标志
PATH_LINE = re.compile(r"^\s+- +Path:", re.MULTILINE)
BACKTICKED = re.compile(r"`([^`]+)`")


def _handwritten_head(text):
    """手写段区域：Runtime Plugin Skills 段和 Auto 登记表之前的部分。"""
    return text.split(HANDWRITTEN_END, 1)[0].split(BEGIN, 1)[0]


def collect_registered_names(head):
    """返回 [(name, 行号)]，两条互补路径都收：

    1. 顶层 `- \`name\`` 条目（宽松匹配，允许后面跟说明）。
    2. 从每个缩进的 "- Path:" 行往回找最近的顶层 "- " 条目，取其第一个反引号名。
       这条是**结构锚点**，不依赖名字行的具体写法——加粗、链接、破折号说明都能抓到，
       补上纯正则匹配漏掉的格式变体。
    """
    found = {}
    for m in BULLET.finditer(head):
        found.setdefault(m.group(1), head[: m.start()].count("\n") + 1)

    lines = head.splitlines()
    for i, line in enumerate(lines):
        if not PATH_LINE.match(line):
            continue
        for j in range(i - 1, -1, -1):
            if lines[j].startswith("- "):
                bt = BACKTICKED.search(lines[j])
                if bt:
                    found.setdefault(bt.group(1), j + 1)
                break
            if lines[j].startswith("#"):
                break
    return sorted(found.items(), key=lambda kv: kv[1])


def check_index_consistency(dirs, text=None):
    """返回问题列表：手写段引用了不存在的 skill。"""
    problems = []
    if text is None:
        if not os.path.isfile(INDEX):
            return problems
        with open(INDEX, encoding="utf-8") as f:
            text = f.read()
    head = _handwritten_head(text)
    for name, line_no in collect_registered_names(head):
        if name in dirs or name in PLUGIN_WHITELIST:
            continue
        problems.append(
            f"capabilities/skills.md:{line_no}: 手写段登记了 `{name}`，"
            f"但 skills/{name}/ 不存在（幽灵条目）。"
            f"→ 同步进中央、改成明确的外部路径、或删掉这条。"
        )
    return problems


def main():
    check_only = "--check" in sys.argv[1:]
    entries = []
    problems = []
    dirs = set()
    for d in sorted(os.listdir(SKILLS)):
        skill_md = os.path.join(SKILLS, d, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        dirs.add(d)
        name, desc = parse_frontmatter(skill_md)
        if name and name != d:
            problems.append(
                f"skills/{d}/SKILL.md: frontmatter name `{name}` != 目录名 `{d}`。"
                f"运行时按目录名加载、索引按 name 显示，会对不上 → 改成一致。"
            )
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

    problems += check_index_consistency(dirs, text)

    if check_only:
        # 体检模式：只比对不落盘，doctor.sh 用这个，保证"只读"名副其实
        current = ""
        if os.path.isfile(INDEX):
            with open(INDEX, encoding="utf-8") as f:
                current = f.read()
        if current != text:
            problems.append(
                "capabilities/skills.md: Auto 登记表与 skills/ 不同步 "
                "→ 跑 `python3 tools/gen-index.py` 重新生成并 commit。"
            )
        if not problems:
            print(f"gen-index --check: {len(entries)} 个 skill，索引一致")
    else:
        with open(INDEX, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"gen-index: {len(entries)} 个 skill 已登记到 capabilities/skills.md")

    if problems:
        print("\ngen-index: 索引一致性校验未通过：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
