#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs data
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
export OSA_LOCALE="${OSA_LOCALE:-vi}"
if [[ -f logs/osa.pid ]] && kill -0 "$(cat logs/osa.pid)" 2>/dev/null; then
  echo "already running pid=$(cat logs/osa.pid) http://127.0.0.1:8765"
  exit 0
fi
nohup uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765 > logs/osa.log 2>&1 &
echo $! > logs/osa.pid
echo "started pid=$(cat logs/osa.pid) URL=http://127.0.0.1:8765 log=$ROOT/logs/osa.log locale=$OSA_LOCALE"
