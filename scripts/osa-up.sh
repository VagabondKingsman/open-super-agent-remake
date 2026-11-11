#!/usr/bin/env bash
# Bật OSA đầy đủ: tailscaled (TUN, system) + app 127.0.0.1:8765 + serve http=80 (tailnet only).
# Sau reboot cả 3 tự lên (system unit, WantedBy=multi-user.target) — script này để bật/kiểm tra ngay.
#   osa-up.sh            -> system unit nếu đã cài, không thì unit user, cuối cùng là kiểu nohup cũ
#   osa-up.sh --fallback -> ép kiểu cũ (nohup + tailnet-ensure.sh)
set -uo pipefail
R="$(cd "$(dirname "$0")" && pwd)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
AS_ROOT=""; [ "$(id -u)" = 0 ] || AS_ROOT="sudo -n"

# 预压缩静态资源（fastsrv.py 发 .gz）：前端重建后自动补上
"$R/fast-assets.sh" >/dev/null 2>&1 || true

if [ "${1:-}" != "--fallback" ] && systemctl is-enabled tailscaled.service >/dev/null 2>&1 && command -v systemctl >/dev/null; then
  $AS_ROOT systemctl start tailscaled.service osa.service osa-tailnet.service || exit $?
  for i in $(seq 1 60); do
    curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:8765/manifest.json 2>/dev/null && break; sleep 1
  done
  systemctl is-active tailscaled osa osa-tailnet | tr '\n' ' '; echo
elif [ "${1:-}" != "--fallback" ] && systemctl --user is-enabled osa.service >/dev/null 2>&1; then
  systemctl --user start osa.service osa-tailnet.service || exit $?
  for i in $(seq 1 60); do
    curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:8765/manifest.json 2>/dev/null && break; sleep 1
  done
  systemctl --user is-active osa osa-tailnet | tr '\n' ' '; echo
else
  "$R/osa-start.sh" "$@" || exit $?
  "$R/tailnet-ensure.sh"
fi
"$R/osa-smoke.sh" >/dev/null 2>&1 || echo "⚠  gzip 自检失败：scripts/osa-smoke.sh 看详情"
echo "vào: $(cat "$HOME/osa-data/public-url.txt" 2>/dev/null || echo '?')  (hoặc http://127.0.0.1:8765 trên máy này)"
