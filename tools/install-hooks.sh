#!/bin/bash
# 把 tools/hooks/ 下的 hook 装进 .git/hooks/。
# 为什么需要这个脚本：.git/hooks 不随 git 分发——clone 到新机器后 Skill Contract
# 的自动闭环（索引重建 + codex symlink 同步）会静默消失。换机/重装后跑一次。
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/tools/hooks"
DST="$(git rev-parse --git-path hooks)"   # 兼容 linked worktree / .git 为文件的布局
mkdir -p "$DST"

for h in "$SRC"/*; do
  [ -f "$h" ] || continue
  name=$(basename "$h")
  cp "$h" "$DST/$name"
  chmod 755 "$DST/$name"
  echo "installed: .git/hooks/$name"
done
echo "install-hooks: 完成。跑 tools/doctor.sh 可体检整套部署。"
