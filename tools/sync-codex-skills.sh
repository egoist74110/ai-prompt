#!/bin/bash
# 把中央 skills 同步成 ~/.codex/skills 下的 symlink（codex 无整目录 symlink，
# 因其 skills 目录内 .system 由 codex 自管）。
# 已存在的真实目录会被挪成 <name>.bak-<ts> 再替换为 symlink（安全网，不删数据）。
#
# Windows（git-bash/MSYS）注意：非管理员/未开发者模式时没有 SeCreateSymbolicLinkPrivilege，
# `ln -s` 对目录会静默退化成整树复制（不报错、但不是链接，内容会跟中央脱节且体积翻倍——
# 实测踩过）。这里在 Windows 下改用 NTFS Junction（`mklink /J`，目录场景等价、不需要
# 特殊权限）；MSYS 的 `-L` / `readlink` / `rm` 对 junction 和真 symlink 一视同仁，
# 下面的判断/清理逻辑不用跟着分叉。
set -euo pipefail

CENTRAL="${AI_PROMPT_HOME:-$HOME/.ai-prompt}/skills"
TARGET="$HOME/.codex/skills"

is_windows() {
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

make_dir_link() {
  local target="$1" link="$2"
  if is_windows; then
    cmd.exe //c mklink //J "$(cygpath -w "$link")" "$(cygpath -w "$target")" >/dev/null
  else
    ln -s "$target" "$link"
  fi
}

[ -d "$CENTRAL" ] || { echo "sync-codex-skills: 中央目录不存在：$CENTRAL" >&2; exit 1; }
[ -d "$TARGET" ] || { echo "sync-codex-skills: 未检测到 ~/.codex/skills，跳过"; exit 0; }

changed=0
for d in "$CENTRAL"/*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  link="$TARGET/$name"
  if [ -L "$link" ]; then
    if [ "$(readlink "$link")" != "${d%/}" ] && [ "$(readlink "$link")" != "$d" ]; then
      rm "$link"; make_dir_link "$d" "$link"; echo "fixed: $name"; changed=1
    fi
  elif [ -e "$link" ]; then
    mv "$link" "$link.bak-$(date +%Y%m%d%H%M%S)"; make_dir_link "$d" "$link"; echo "replaced: $name"; changed=1
  else
    make_dir_link "$d" "$link"; echo "added: $name"; changed=1
  fi
done

# 中央已删除的 skill：悬空 symlink 清理
# 注意：这里必须用 "$TARGET"/* 而不是 "$TARGET"/*/ ——带斜杠的 glob 要求路径能解析成目录，
# 悬空 symlink 解析失败因此永远匹配不到（实测），旧写法是死代码。
shopt -s nullglob 2>/dev/null || true
for l in "$TARGET"/*; do
  [ -L "$l" ] || continue        # 只动 symlink（含 Windows junction），真实目录不碰
  [ -e "$l" ] && continue        # 能解析 = 没悬空
  echo "removed dangling: $(basename "$l")"; rm "$l"; changed=1
done

[ "$changed" = "1" ] && echo "sync-codex-skills: 完成" || echo "sync-codex-skills: 已是最新"
exit 0
