#!/bin/bash
# 中央提示词系统体检（严格只读）。
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${AI_PROMPT_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
fail=0
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; fail=1; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

echo "== 0. root / local state =="
ok "AI_PROMPT_ROOT=$ROOT"
if command -v "$PY" >/dev/null 2>&1; then
  if [ -f "$ROOT/.local/runtime.json" ] && [ -f "$ROOT/.local/state.json" ]; then
    ok ".local runtime/state 已初始化"
  else
    warn ".local 尚未初始化 → $PY tools/runtime_state.py init（首次需要缓存时再跑也行）"
  fi
else
  warn "python/python3 不在 PATH；中央规则可读，但 runtime_state 辅助工具不可用"
fi

echo "== 1. 运行时入口（存在的入口应指向当前 router.md） =="
router_posix="$ROOT/router.md"
router_win=""
command -v cygpath >/dev/null 2>&1 && router_win="$(cygpath -w "$router_posix" 2>/dev/null)"
found_entry=0
for f in "$HOME/.claude/CLAUDE.md" "$HOME/.codex/AGENTS.md" "$HOME/.gemini/GEMINI.md" "$HOME/.dsh/AGENTS.md"; do
  [ -f "$f" ] || continue
  found_entry=1
  if grep -qF "$router_posix" "$f" || { [ -n "$router_win" ] && grep -qF "$router_win" "$f"; }; then
    ok "$f → router.md"
  else
    bad "$f 存在但没指向当前 $router_posix"
  fi
done
[ "$found_entry" = "1" ] || warn "未发现已知运行时入口；如果当前运行时靠别的入口加载 router，可忽略"

echo "== 2. router 引用的文件都在 =="
for f in common.md models/high.md models/scout.md \
         capabilities/skills.md capabilities/mcp.md capabilities/search.md capabilities/cross-review.md \
         config/README.md tools/runtime_state.py; do
  [ -f "$ROOT/$f" ] && ok "$f" || bad "$f 缺失（router/README 里有引用）"
done

echo "== 3. skills 部署（只检查当前存在的运行时目录） =="
if [ -d "$HOME/.claude" ]; then
  claude_link_target="$(readlink "$HOME/.claude/skills" 2>/dev/null)"
  if [ -L "$HOME/.claude/skills" ] \
     && { [ "$claude_link_target" = "$ROOT/skills" ] || [ "$claude_link_target" = "$ROOT/skills/" ]; }; then
    ok "~/.claude/skills → 中央"
  elif [ -e "$HOME/.claude/skills" ]; then
    warn "~/.claude/skills 存在但不是当前中央目录链接；具体布局应记录到本地 runtime"
  else
    warn "Claude 目录存在但 skills 未部署"
  fi
fi

if [ -d "$HOME/.codex/skills" ]; then
  missing=0; dangling=0; orphan=0
  for d in "$ROOT"/skills/*/; do
    [ -d "$d" ] || continue
    [ -L "$HOME/.codex/skills/$(basename "$d")" ] || { warn "codex 缺中央 skill 链接: $(basename "$d")"; missing=1; }
  done
  for l in "$HOME/.codex/skills"/*; do
    [ -e "$l" ] || [ -L "$l" ] || continue
    n=$(basename "$l")
    if [ -L "$l" ] && [ ! -e "$l" ]; then warn "codex 悬空 symlink: $n"; dangling=1
    elif [ -d "$l" ] && [ ! -L "$l" ] && [ "$n" != ".system" ]; then
      warn "codex 侧真实目录（可能是本地私有/孤儿）: $n"; orphan=1
    fi
  done
  [ "$missing$dangling" = "00" ] && ok "~/.codex/skills 中央链接完整无悬空"
  [ "$orphan" = "1" ] && warn "私有/孤儿目录若要共享，按 router Skill Contract 同步进中央"
fi

echo "== 4. 索引一致性（--check：只比对，不写文件） =="
if command -v "$PY" >/dev/null 2>&1; then
  if out=$(cd "$ROOT" && "$PY" tools/gen-index.py --check 2>&1); then
    ok "$(echo "$out" | head -1)"
  else
    bad "索引校验未通过："; echo "$out" | sed 's/^/      /'
  fi
else
  warn "无 Python，跳过索引校验"
fi

echo "== 5. pre-commit hook =="
if [ ! -d "$ROOT/.git" ]; then
  warn "$ROOT 不是 git 工作副本（镜像模式部署），跳过 pre-commit 检查"
else
  HOOKDIR="$(cd "$ROOT" && git rev-parse --git-path hooks 2>/dev/null)"
  case "$HOOKDIR" in /*) ;; *) HOOKDIR="$ROOT/$HOOKDIR" ;; esac
  if [ -x "$HOOKDIR/pre-commit" ]; then
    cmp -s "$ROOT/tools/hooks/pre-commit" "$HOOKDIR/pre-commit" \
      && ok "hook 已装且与 tools/hooks/pre-commit 一致" \
      || warn "hook 已装但与仓库正典不一致 → 跑 tools/install-hooks.sh"
  else
    warn "pre-commit hook 未安装 → 编辑机建议跑 tools/install-hooks.sh"
  fi
fi

echo "== 6. 通用命令可用性（不再把单机外部路径当全局真理） =="
for c in git node python3 python az mc gh; do
  command -v "$c" >/dev/null && ok "$c" || warn "$c 不在 PATH"
done

echo
[ "$fail" = "0" ] && echo "doctor: 全部硬性检查通过" || echo "doctor: 有 ✗ 项，按上面提示修"
exit "$fail"
