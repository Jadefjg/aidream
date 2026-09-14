#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$ROOT/backend"
if [ ! -d .venv ]; then
  PYTHON_BIN="${PYTHON_BIN:-python3.11}"
  command -v "$PYTHON_BIN" >/dev/null || PYTHON_BIN=python3
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
uvicorn app.main:app --reload --port 8000 --app-dir "$ROOT/backend" &
BACK_PID=$!

cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null || true' INT TERM
wait
