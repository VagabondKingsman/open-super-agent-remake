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

# Default layout keeps data/ and logs/ inside the checkout.
# OSA_DATA_DIR moves the database (Python) and these logs/PID files out of the repo.
if [[ -n "${OSA_DATA_DIR:-}" ]]; then
  DATA_DIR="${OSA_DATA_DIR/#\~/$HOME}"
  if [[ "$DATA_DIR" != /* ]]; then
    DATA_DIR="$ROOT/$DATA_DIR"
  fi
  LOG_DIR="$DATA_DIR/logs"
else
  DATA_DIR="$ROOT/data"
  LOG_DIR="$ROOT/logs"
fi
mkdir -p "$DATA_DIR" "$LOG_DIR"
PIDFILE="$LOG_DIR/osa.pid"
LOGFILE="$LOG_DIR/osa.log"

if [[ "${OSA_START_DRY_RUN:-}" == "1" ]]; then
  printf 'data=%s\nlog=%s\npid=%s\n' "$DATA_DIR" "$LOGFILE" "$PIDFILE"
  exit 0
fi

if [[ -f "$PIDFILE" ]]; then
  read -r pid < "$PIDFILE"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    if [[ "$(readlink "/proc/$pid/cwd")" == "$ROOT" ]] && [[ "$(ps -p "$pid" -o args=)" == *"uvicorn osa.server:app"* ]]; then
      echo "already running pid=$pid http://127.0.0.1:8765"
      exit 0
    fi
    echo "PID file belongs to another process; inspect $PIDFILE" >&2
    exit 1
  fi
fi
nohup uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765 > "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "started pid=$! URL=http://127.0.0.1:8765 log=$LOGFILE; check HTTP readiness"
