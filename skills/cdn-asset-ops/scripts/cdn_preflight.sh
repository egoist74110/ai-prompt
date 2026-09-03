#!/usr/bin/env bash
# cdn_preflight.sh — 只读探测，绝不写、不删、不打印任何密钥。
#
# 用途：在做任何 CDN(MinIO/S3) 操作前，回答两件事：
#   1) mc 是否安装、目标 host 是否已经配过 alias（配过就直接用，不要重新跑教程）。
#   2) 目标 host 的 S3 API 端口是哪个（Console 端口 != API 端口，这是最大的坑）。
#
# 用法：
#   cdn_preflight.sh <console_url_or_host>
# 例：
#   cdn_preflight.sh http://43.198.44.29:9000/browser/cg-cdn-minio/cHVibGlj
#   cdn_preflight.sh 43.198.44.29
#
# 输出是给 AI 看的结构化文本；不做任何修改性操作。

set -u

INPUT="${1:-}"
if [ -z "$INPUT" ]; then
  echo "ERROR: 需要一个参数：MinIO Console 的 URL 或 host"
  echo "用法: cdn_preflight.sh <console_url_or_host>"
  exit 2
fi

# 从输入里抠出 host（去掉 scheme、path、端口）
HOST="$INPUT"
HOST="${HOST#http://}"
HOST="${HOST#https://}"
HOST="${HOST%%/*}"      # 去掉 path
HOST="${HOST%%:*}"      # 去掉端口

echo "===== CDN PREFLIGHT (read-only) ====="
echo "input : $INPUT"
echo "host  : $HOST"
echo

# --- 1. mc 是否安装 ---
echo "----- mc client -----"
if command -v mc >/dev/null 2>&1; then
  echo "mc: installed ($(mc --version 2>/dev/null | head -n1))"
else
  echo "mc: NOT installed  -> 安装: brew install minio/stable/mc"
fi
echo

# --- 2. 已配置的 alias（脱敏，只看是否已经指向目标 host）---
echo "----- existing aliases (secrets hidden) -----"
if command -v mc >/dev/null 2>&1; then
  # mc alias ls 默认会显示 SecretKey，这里只抓 alias 名和 URL 行，丢弃 AccessKey/SecretKey
  mc alias ls 2>/dev/null | grep -iE '^[^ ]|URL' | grep -viE 'AccessKey|SecretKey' | sed 's/^/  /'
  echo
  if mc alias ls 2>/dev/null | grep -q "$HOST"; then
    echo "MATCH: 已存在指向 $HOST 的 alias。直接复用，不要重新配置。"
  else
    echo "NO MATCH: 没有指向 $HOST 的 alias，需要按 references/setup.md 配置。"
  fi
else
  echo "  (mc 未安装，无法列出 alias)"
fi
echo

# --- 3. 探测 S3 API 端口（Console != API）---
echo "----- probing S3 API port on $HOST -----"
echo "(Server: MinIO = API 可用; Server: MinIO Console = 控制台端口, 不能拿来 alias)"
API_PORTS=()
for scheme in http https; do
  for p in 9000 9001 9002 9003 9004 9005 80 443; do
    url="$scheme://$HOST:$p/minio/health/live"
    server=$(curl -s -I --max-time 3 "$url" 2>/dev/null | grep -i '^Server:' | tr -d '\r' | sed 's/^[Ss]erver: *//')
    [ -z "$server" ] && continue
    if echo "$server" | grep -qi 'console'; then
      echo "  $scheme :$p -> $server   [CONSOLE, 不可用作 alias]"
    elif echo "$server" | grep -qi 'minio'; then
      echo "  $scheme :$p -> $server   [S3 API ✓]"
      API_PORTS+=("$scheme://$HOST:$p")
    else
      echo "  $scheme :$p -> $server"
    fi
  done
done
echo

if [ "${#API_PORTS[@]}" -gt 0 ]; then
  echo "RESULT: S3 API endpoint(s) =>"
  for e in "${API_PORTS[@]}"; do echo "  $e"; done
  echo "用这个 endpoint 做 mc alias set，不要用 Console 端口。"
else
  echo "RESULT: 没探到 'Server: MinIO' 的 API 端口。"
  echo "  可能 API 端口非常规 / 走了网关 / 只开了 Console。向用户确认真实 S3 API endpoint 再继续。"
fi
