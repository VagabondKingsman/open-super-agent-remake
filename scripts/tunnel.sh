#!/usr/bin/env bash
# Cloudflare quick tunnel cho OSA (127.0.0.1:8765).
#   tunnel.sh url      -> in URL đang dùng
#   tunnel.sh ensure   -> kiểm tra URL từ ngoài; hỏng thì restart rồi in URL mới (exit 1 nếu vẫn hỏng)
#   tunnel.sh restart  -> restart, in URL mới
set -uo pipefail
LOG="$HOME/osa-data/logs/tunnel.log"
OLDLOG="$HOME/.local/share/cfd.log"
STATE="$HOME/osa-data/public-url.txt"
BIN="$HOME/.local/bin/cloudflared"
TARGET="http://127.0.0.1:8765"
mkdir -p "$(dirname "$LOG")"

url_now() {
  u=$(grep -ho 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -1)
  if [ -z "${u:-}" ]; then
    u=$(grep -ho 'https://[a-z0-9-]*\.trycloudflare\.com' "$OLDLOG" 2>/dev/null | tail -1)
  fi
  echo "${u:-}"
}
alive() { pgrep -f "cloudflared tunnel .*--url $TARGET" >/dev/null 2>&1; }
reachable() { [ -n "${1:-}" ] && curl -fsS -o /dev/null --max-time 15 "$1/login"; }

start() {
  setsid nohup "$BIN" tunnel --no-autoupdate --url "$TARGET" >>"$LOG" 2>&1 &
  u=""
  for _ in $(seq 1 30); do
    sleep 1
    u=$(url_now); [ -n "${u:-}" ] && break
  done
  if [ -z "${u:-}" ]; then echo "FAIL: cloudflared không in URL sau 30s (xem $LOG)" >&2; return 1; fi
  echo "$u" > "$STATE"
  sleep 2
  if reachable "$u"; then echo "OK new tunnel: $u"; else echo "FAIL: tunnel mới chưa trả lời: $u" >&2; return 1; fi
}

case "${1:-ensure}" in
  url) u=$(url_now); echo "${u:-NONE}"; [ -n "${u:-}" ] ;;
  ensure)
    u=$(url_now)
    if alive && reachable "$u"; then echo "OK $u"; echo "$u" > "$STATE"; exit 0; fi
    echo "tunnel hỏng (alive=$(alive && echo yes || echo no), url=${u:-NONE}) -> restart" >&2
    pkill -f "cloudflared tunnel .*--url $TARGET" 2>/dev/null; sleep 1; start ;;
  restart)
    pkill -f "cloudflared tunnel .*--url $TARGET" 2>/dev/null; sleep 1; start ;;
  *) echo "usage: $0 url|ensure|restart" >&2; exit 2 ;;
esac
