#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
exec "$PY" "$SCRIPT_DIR/playwright_cli.py" "$@"
