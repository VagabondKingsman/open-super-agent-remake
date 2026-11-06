#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="$ROOT/logs/osa.pid"
if [[ -f "$PIDFILE" ]]; then
  pid=$(cat "$PIDFILE")
  kill "$pid" 2>/dev/null || true
  rm -f "$PIDFILE"
  echo "stopped $pid"
else
  pkill -f 'uvicorn osa.server:app' 2>/dev/null || true
  echo "stopped (no pidfile)"
fi
