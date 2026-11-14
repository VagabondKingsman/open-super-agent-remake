#!/usr/bin/env bash
# Đường vào OSA qua Tailscale (KHÔNG funnel): serve http=80 -> 127.0.0.1:8765 (tailnet only).
# Tự chọn daemon: system (root, /run/tailscale) nếu có, ngược lại user (~/.tailscale).
set -uo pipefail
REPO=$(cd "$(dirname "$0")" 2>/dev/null && cd .. && pwd)   # 仓库在哪都成立，不再写死 /home/boxes
H=$(dirname "$REPO")
PORT="${OSA_PORT:-8765}"
ENVF="$REPO/.env"
DATADIR="${OSA_DATA_DIR:-$(grep -h '^OSA_DATA_DIR=' "$ENVF" 2>/dev/null | tail -1 | cut -d= -f2-)}"
DATADIR="${DATADIR:-$H/osa-data}"
if [ -S /run/tailscale/tailscaled.sock ] && [ -x /usr/local/bin/tailscale ] \
   && /usr/local/bin/tailscale --socket=/run/tailscale/tailscaled.sock status >/dev/null 2>&1; then
  TB=/usr/local/bin/tailscale; S="--socket=/run/tailscale/tailscaled.sock"   # daemon system đang chạy: dùng nó, kể cả khi chạy bằng user
else
  TB="$H/.local/tailscale/tailscale"; S="--socket=$H/.tailscale/tailscaled.sock"
fi
OUT="$DATADIR/public-url.txt"
mkdir -p "$DATADIR" 2>/dev/null || true

key_from_env() { grep -h '^TS_AUTHKEY=' "$ENVF" 2>/dev/null | tail -1 | cut -d= -f2-; }
st() { "$TB" $S status --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("BackendState","?"))' 2>/dev/null; }

# chờ app trả lời (tối đa 20s) để serve không trỏ vào cổng câm lúc boot
for i in $(seq 1 20); do curl -fsS -o /dev/null --max-time 2 "http://127.0.0.1:$PORT/manifest.json" 2>/dev/null && break; sleep 1; done

s=""
for i in $(seq 1 90); do
  s=$(st); [ "$s" = "Running" ] && break; sleep 1
done
if [ "$s" != "Running" ]; then
  K=$(key_from_env)
  if [ -n "${K:-}" ]; then timeout 60 "$TB" $S up --authkey="$K" --hostname=osa --accept-dns=false >/dev/null 2>&1; fi
  s=$(st)
fi

"$TB" $S serve --bg --http=80 "http://127.0.0.1:$PORT" >/dev/null 2>&1
SERVE=$("$TB" $S serve status 2>/dev/null | grep -c "proxy http://127.0.0.1:$PORT")
DNS=$("$TB" $S status --json 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print((d.get("Self") or {}).get("DNSName","").rstrip("."))' 2>/dev/null)
IP=$("$TB" $S status --json 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(" ".join([i for i in ((d.get("Self") or {}).get("TailscaleIPs") or []) if ":" not in i]))' 2>/dev/null)
CUR=$("$TB" $S status --json 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print((d.get("Self") or {}).get("CurAddr",""))' 2>/dev/null)
echo "tailscale=$s serve=$([ "${SERVE:-0}" -gt 0 ] && echo on || echo off) dns=${DNS:-none} ip=${IP:-none} cur=${CUR:-relay}"
[ -n "${DNS:-}" ] && echo "http://$DNS" > "$OUT" 2>/dev/null
# quyền file cho user boxes khi chạy bằng root
if [ "$(id -u)" = 0 ]; then chown "$(stat -c %U "$H"):$(stat -c %G "$H")" "$OUT" 2>/dev/null || true; fi
[ "$s" = "Running" ] && [ "${SERVE:-0}" -gt 0 ]
