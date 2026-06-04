#!/usr/bin/env bash
# Serve dataset-grader on a dedicated port (avoids conflict with other Panel apps on 5006).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export GRADER_MANIFEST="${GRADER_MANIFEST:-$ROOT/example/manifest.csv}"
export GRADER_USERS_FILE="${GRADER_USERS_FILE:-$ROOT/config/users.json}"
export GRADER_DB_PATH="${GRADER_DB_PATH:-$ROOT/data/grader.sqlite}"

HOST="${GRADER_HOST:-127.0.0.1}"
PORT="${GRADER_PORT:-8765}"

PYTHON="${ROOT}/.venv/bin/python"
PANEL="${ROOT}/.venv/bin/panel"
if [[ ! -x "$PANEL" ]]; then
  PYTHON="python3"
  PANEL="panel"
fi

echo "Dataset grader: http://${HOST}:${PORT}/app"
echo "Manifest: $GRADER_MANIFEST"
echo "Users:    $GRADER_USERS_FILE"
exec "$PANEL" serve src/dataset_grader/app.py \
  --address "$HOST" \
  --port "$PORT" \
  --autoreload \
  --show \
  "$@"
