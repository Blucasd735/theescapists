#!/usr/bin/env bash
set -euo pipefail

GAME_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON_BIN="${GOGEXTRACT_PYTHON:-python3}"

exec "$PYTHON_BIN" "$GAME_DIR/gogextract.py" --game-dir "$GAME_DIR" "$@"
