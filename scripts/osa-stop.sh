#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "${OSA_DOTENV:-1}" != "0" && -f .env ]]; then
  set -a
  # Only source a trusted, shell-compatible local environment file.
  # shellcheck disable=SC1091
  source .env
  set +a
fi
if [[ -n "${OSA_DATA_DIR:-}" ]]; then
  DATA_DIR="${OSA_DATA_DIR/#\~/$HOME}"
  if [[ "$DATA_DIR" != /* ]]; then
    DATA_DIR="$ROOT/$DATA_DIR"
  fi
  LOG_DIR="$DATA_DIR/logs"
else
  LOG_DIR="$ROOT/logs"
fi
PIDFILE="$LOG_DIR/osa.pid"
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
