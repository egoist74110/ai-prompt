#!/bin/bash
# 把中央 skills 同步成 ~/.codex/skills 下的 symlink（codex 无整目录 symlink，
# 因其 skills 目录内 .system 由 codex 自管）。
# 已存在的真实目录会被挪成 <name>.bak-<ts> 再替换为 symlink（安全网，不删数据）。
set -euo pipefail

CENTRAL="${AI_PROMPT_HOME:-$HOME/.ai-prompt}/skills"
TARGET="$HOME/.codex/skills"

[ -d "$CENTRAL" ] || { echo "sync-codex-skills: 中央目录不存在：$CENTRAL" >&2; exit 1; }
[ -d "$TARGET" ] || { echo "sync-codex-skills: 未检测到 ~/.codex/skills，跳过"; exit 0; }

changed=0
for d in "$CENTRAL"/*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  link="$TARGET/$name"
  if [ -L "$link" ]; then
    if [ "$(readlink "$link")" != "${d%/}" ] && [ "$(readlink "$link")" != "$d" ]; then
      rm "$link"; ln -s "$d" "$link"; echo "fixed: $name"; changed=1
    fi
  elif [ -e "$link" ]; then
    mv "$link" "$link.bak-$(date +%Y%m%d%H%M%S)"; ln -s "$d" "$link"; echo "replaced: $name"; changed=1
  else
    ln -s "$d" "$link"; echo "added: $name"; changed=1
  fi
done

# 中央已删除的 skill：悬空 symlink 清理
for l in "$TARGET"/*/; do
  [ -L "${l%/}" ] || continue
  [ -e "$l" ] || { echo "removed dangling: $(basename "$l")"; rm "${l%/}"; }
done

[ "$changed" = "1" ] && echo "sync-codex-skills: 完成" || echo "sync-codex-skills: 已是最新"
exit 0
