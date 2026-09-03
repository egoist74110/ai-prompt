#!/bin/bash
# 中央提示词系统体检（只读，不改任何东西）。
# 覆盖那些"文档说是这样、现实可能不是这样"的点：四个运行时入口、两组 symlink、
# 索引一致性、hook 是否装了、search.md 声明的后端是否真的在。
# 改完环境（换机、重装运行时、动了 skills 目录）跑一次。
set -uo pipefail
ROOT="${AI_PROMPT_HOME:-$HOME/.ai-prompt}"
fail=0
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; fail=1; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }

echo "== 1. 运行时入口（应为指向 router.md 的薄指针） =="
for f in "$HOME/.claude/CLAUDE.md" "$HOME/.codex/AGENTS.md" "$HOME/.gemini/GEMINI.md" "$HOME/.dsh/AGENTS.md"; do
  if [ ! -f "$f" ]; then bad "$f 不存在"
  elif grep -q "$ROOT/router.md" "$f"; then ok "$f → router.md"
  else bad "$f 存在但没指向 $ROOT/router.md"; fi
done

echo "== 2. router 引用的文件都在 =="
for f in common.md models/high.md models/scout.md \
         capabilities/skills.md capabilities/mcp.md capabilities/search.md capabilities/cross-review.md; do
  [ -f "$ROOT/$f" ] && ok "$f" || bad "$f 缺失（router/README 里有引用）"
done

echo "== 3. skills symlink 部署 =="
if [ -L "$HOME/.claude/skills" ] && [ "$(readlink "$HOME/.claude/skills")" = "$ROOT/skills" ]; then
  ok "~/.claude/skills 整目录 symlink → 中央"
else
  bad "~/.claude/skills 不是指向 $ROOT/skills 的 symlink（Claude 会看不到中央 skill）"
fi
if [ -d "$HOME/.codex/skills" ]; then
  missing=0; dangling=0; orphan=0
  for d in "$ROOT"/skills/*/; do
    [ -d "$d" ] || continue
    [ -L "$HOME/.codex/skills/$(basename "$d")" ] || { bad "codex 缺 symlink: $(basename "$d")"; missing=1; }
  done
  for l in "$HOME/.codex/skills"/*; do
    [ -e "$l" ] || [ -L "$l" ] || continue
    n=$(basename "$l")
    if [ -L "$l" ] && [ ! -e "$l" ]; then bad "codex 悬空 symlink: $n"; dangling=1
    elif [ -d "$l" ] && [ ! -L "$l" ] && [ "$n" != ".system" ]; then
      warn "codex 侧真实目录（中央无记录，Skill Contract 之外的孤儿）: $n"; orphan=1
    fi
  done
  [ "$missing$dangling" = "00" ] && ok "~/.codex/skills 单 skill symlink 完整无悬空"
  [ "$orphan" = "1" ] && warn "→ 孤儿目录要么同步进中央，要么删掉（见 router.md Skill Contract 第 5 条）"
else
  warn "~/.codex/skills 不存在，跳过 codex 检查"
fi

echo "== 4. 索引一致性 =="
if out=$(cd "$ROOT" && python3 tools/gen-index.py 2>&1); then
  ok "$(echo "$out" | head -1)"
  (cd "$ROOT" && git diff --quiet -- capabilities/skills.md 2>/dev/null) \
    || warn "Auto 登记表与 skills/ 不同步，已重新生成——记得 commit"
else
  bad "索引校验未通过："; echo "$out" | sed 's/^/      /'
fi

echo "== 5. pre-commit hook =="
if [ -x "$ROOT/.git/hooks/pre-commit" ]; then
  cmp -s "$ROOT/tools/hooks/pre-commit" "$ROOT/.git/hooks/pre-commit" \
    && ok "hook 已装且与 tools/hooks/pre-commit 一致" \
    || warn "hook 已装但与仓库里的正典不一致 → 跑 tools/install-hooks.sh"
else
  bad "pre-commit hook 未安装 → 跑 tools/install-hooks.sh（否则索引/同步闭环失效）"
fi

echo "== 6. search.md 声明的后端 =="
for p in "$HOME/brave_search.sh" "$HOME/tavily_search.sh" \
         "$HOME/.config/tavily/.env" "$HOME/.config/brave/.env" \
         "$HOME/.wigolo-mcp/node_modules/wigolo/dist/index.js"; do
  [ -e "$p" ] && ok "${p/#$HOME/~}" || bad "$p 缺失（capabilities/search.md 里有声明）"
done
for c in gh az mc node python3; do
  command -v "$c" >/dev/null && ok "$c" || warn "$c 不在 PATH（部分 skill/搜索路径会不可用）"
done

echo
[ "$fail" = "0" ] && echo "doctor: 全部通过" || echo "doctor: 有 ✗ 项，按上面提示修"
exit "$fail"
