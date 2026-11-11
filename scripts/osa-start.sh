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
PORTFILE="$LOG_DIR/osa.port"
LOGFILE="$LOG_DIR/osa.log"
# A7：日志只留一份旧的。uvicorn 直接把输出写到这个文件，自己不会转，久了会一直长。
MAX_LOG_BYTES="${OSA_LOG_MAX_BYTES:-20971520}"   # 20 MB
# OSA_PORT picks the port (default 8765). The server always binds 127.0.0.1; put a reverse proxy in front for LAN access.
PORT="${OSA_PORT:-8765}"
if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "OSA_PORT must be a port number (1-65535), got: $PORT" >&2
  exit 2
fi
URL="http://127.0.0.1:$PORT"
# How long to wait for /manifest.json before giving up (seconds).
TIMEOUT="${OSA_START_TIMEOUT:-60}"

if [[ "${OSA_START_DRY_RUN:-}" == "1" ]]; then
  printf 'data=%s\nlog=%s\npid=%s\nport=%s\n' "$DATA_DIR" "$LOGFILE" "$PIDFILE" "$PORT"
  exit 0
fi

ready() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -o /dev/null --max-time 2 "$URL/manifest.json" 2>/dev/null
  else
    python3 -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)' "$URL/manifest.json" 2>/dev/null
  fi
}

if [[ -f "$PIDFILE" ]]; then
  read -r pid < "$PIDFILE"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    if [[ "$(readlink "/proc/$pid/cwd")" == "$ROOT" ]] && [[ "$(ps -p "$pid" -o args=)" == *"uvicorn osa.server:app"* ]]; then
      running_port="$(cat "$PORTFILE" 2>/dev/null || echo "$PORT")"
      echo "already running pid=$pid http://127.0.0.1:$running_port"
      exit 0
    fi
    echo "PID file belongs to another process; inspect $PIDFILE" >&2
    exit 1
  fi
fi
if ready; then
  echo "port $PORT already answers $URL/manifest.json (another server?); set OSA_PORT or stop it first" >&2
  exit 1
fi
if [[ -f "$LOGFILE" ]] && (( $(stat -c%s "$LOGFILE" 2>/dev/null || echo 0) > MAX_LOG_BYTES )); then
  mv -f "$LOGFILE" "$LOGFILE.1"
fi
nohup uv run uvicorn osa.server:app --host 127.0.0.1 --port "$PORT" >> "$LOGFILE" 2>&1 &
pid=$!
echo "$pid" > "$PIDFILE"
echo "$PORT" > "$PORTFILE"
echo "starting pid=$pid URL=$URL log=$LOGFILE; waiting up to ${TIMEOUT}s for /manifest.json"
deadline=$((SECONDS + TIMEOUT))
while (( SECONDS < deadline )); do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "server exited before it was ready; last log lines:" >&2
    tail -n 20 "$LOGFILE" >&2 || true
    rm -f "$PIDFILE" "$PORTFILE"
    exit 1
  fi
  if ready; then
    echo "started pid=$pid URL=$URL log=$LOGFILE"
    exit 0
  fi
  sleep 0.5
done
echo "server pid=$pid did not answer $URL/manifest.json within ${TIMEOUT}s; it is still running, see $LOGFILE (stop it with scripts/osa-stop.sh)" >&2
exit 1
