#!/usr/bin/env bash
# Create project .venv with Python 3.10+ (required by dataset-grader).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

choose_python() {
  for candidate in python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PY="$(choose_python)" || {
  echo "dataset-grader needs Python 3.10 or newer (python3.10, python3.11, or python3.12)." >&2
  echo "On lwacalim, /usr/bin/python3.11 is available." >&2
  exit 1
}

echo "Using $PY ($("$PY" --version))"
"$PY" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -U pip setuptools wheel
"$ROOT/.venv/bin/pip" install -e ".[dev]"
echo "Installed into $ROOT/.venv"
echo "Run: source .venv/bin/activate && ./scripts/serve.sh"
