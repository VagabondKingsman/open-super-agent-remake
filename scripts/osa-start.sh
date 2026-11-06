#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs data
if [[ -f .env ]]; then
  set -a
  # Only source a trusted, shell-compatible local environment file.
  # shellcheck disable=SC1091
  source .env
  set +a
fi
if [[ -f logs/osa.pid ]]; then
  read -r pid < logs/osa.pid
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    if [[ "$(readlink "/proc/$pid/cwd")" == "$ROOT" ]] && [[ "$(ps -p "$pid" -o args=)" == *"uvicorn osa.server:app"* ]]; then
      echo "already running pid=$pid http://127.0.0.1:8765"
      exit 0
    fi
    echo "PID file belongs to another process; inspect $ROOT/logs/osa.pid" >&2
    exit 1
  fi
fi
nohup uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765 > logs/osa.log 2>&1 &
echo $! > logs/osa.pid
echo "started pid=$! URL=http://127.0.0.1:8765 log=$ROOT/logs/osa.log; check HTTP readiness"
