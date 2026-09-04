#!/bin/bash
# Backward-compatible entrypoint. Cross-platform core lives in sync_skills.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
exec "$PY" "$ROOT/tools/sync_skills.py" --runtime codex "$@"
