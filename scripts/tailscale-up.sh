#!/usr/bin/env bash
# Tailscale cho OSA — mặc định KHÔNG dùng Funnel: chỉ vào tailnet, truy cập riêng qua WireGuard
# (http://osa:8765 hoặc http://100.x.y.z:8765). Ổn định, không phụ thuộc quick tunnel.
#   tailscale-up.sh tskey-auth-xxx        -> login (giữ key vào ~/osa/.env để watchdog dùng lại)
#   tailscale-up.sh --funnel              -> bật Funnel (https công khai) nếu thật sự cần
#   tailscale-up.sh --status              -> xem trạng thái + URL vào OSA
set -uo pipefail
TS="$HOME/.local/tailscale/tailscaled"; TB="$HOME/.local/tailscale/tailscale"
S="--socket=$HOME/.tailscale/tailscaled.sock"
ENVF="$HOME/osa/.env"; PORT=8765
KEY=""; MODE="up"
for a in "$@"; do
  case "$a" in
    --funnel) MODE="funnel" ;;
    --status) MODE="status" ;;
    tskey-*) KEY="$a" ;;
  esac
done

tailscaled_up() { pgrep -f "tailscaled .*--socket=$HOME/.tailscale/tailscaled.sock" >/dev/null; }
start_daemon() {
  tailscaled_up && return 0
  # máy này eth0 chỉ có 169.254.x (link-local) nên netmon tưởng offline và pause control client;
  # TS_ASSUME_NETWORK_UP_FOR_TEST=1 bắt tailscaled coi như có mạng (đã chứng minh: hết treo, login đi được)
  TS_ASSUME_NETWORK_UP_FOR_TEST=1 setsid nohup "$TS" --tun=userspace-networking --state="$HOME/.tailscale/tailscaled.state" \
    --socket="$HOME/.tailscale/tailscaled.sock" --port=0 >>"$HOME/osa-data/logs/tailscaled.log" 2>&1 &
  sleep 3
}
state() { "$TB" $S status --json 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("BackendState","?"))' 2>/dev/null; }
addresses() { "$TB" $S status --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); s=d.get("Self") or {}
print(s.get("DNSName","").rstrip("."), " ".join(s.get("TailscaleIPs") or []))' 2>/dev/null; }

start_daemon || { echo "FAIL: tailscaled không chạy" >&2; exit 1; }

if [ -n "$KEY" ]; then
  echo "login tailscale (hostname=osa)…"
  timeout 60 "$TB" $S up --authkey="$KEY" --hostname=osa --accept-dns=false --reset || { echo "FAIL: up thất bại" >&2; exit 1; }
  if grep -q '^TS_AUTHKEY=' "$ENVF" 2>/dev/null; then
    sed -i "s|^TS_AUTHKEY=.*|TS_AUTHKEY=$KEY|" "$ENVF"
  else
    echo "TS_AUTHKEY=$KEY" >> "$ENVF"
  fi
  chmod 600 "$ENVF"
fi

st=$(state)
read -r DNS IPS <<<"$(addresses)"
echo "state=$st"
[ -n "${DNS:-}" ] && echo "magicdns=https://$DNS  http://$DNS:$PORT"
[ -n "${IPS:-}" ] && for ip in $IPS; do echo "ip=$ip  http://$ip:$PORT"; done

if [ "$MODE" = "funnel" ]; then
  "$TB" $S cert "$DNS" >/dev/null 2>&1 || echo "WARN: chưa lấy được cert HTTPS" >&2
  "$TB" $S funnel --bg "$PORT" >/dev/null 2>&1 || "$TB" $S funnel "$PORT" on >/dev/null 2>&1 || echo "WARN: bật funnel thất bại" >&2
  "$TB" $S funnel status 2>&1 | head -6
fi
[ "$MODE" = "up" ] && "$TB" $S funnel reset >/dev/null 2>&1 && echo "funnel: off (chỉ dùng tailnet)"

# URL vào OSA hiện tại (ghi cho heartbeat/osa-url)
if [ "$st" = "Running" ] && [ -n "${DNS:-}" ]; then echo "http://$DNS:$PORT" > "$HOME/osa-data/public-url.txt"; fi
exit 0
