#!/bin/bash
# Generic compatibility entrypoint for runtime skill syncing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <runtime-id> [extra sync_skills.py args]" >&2
  exit 2
fi

RUNTIME_ID="$1"
shift
exec "$PY" "$ROOT/tools/sync_skills.py" --runtime "$RUNTIME_ID" "$@"
