#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="$ROOT/logs/osa.pid"
if [[ ! -f "$PIDFILE" ]]; then
  echo "No PID file; inspect the listener on :8765. No processes were killed."
  exit 0
fi
read -r pid < "$PIDFILE"
if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
  echo "Invalid PID file; inspect $PIDFILE" >&2
  exit 1
fi
if kill -0 "$pid" 2>/dev/null; then
  if [[ "$(readlink "/proc/$pid/cwd")" != "$ROOT" ]] || [[ "$(ps -p "$pid" -o args=)" != *"uvicorn osa.server:app"* ]]; then
    echo "PID $pid does not belong to this checkout; nothing stopped" >&2
    exit 1
  fi
  kill "$pid"
fi
rm -f "$PIDFILE"
echo "stop requested for $pid; confirm port :8765 is released before starting again"
