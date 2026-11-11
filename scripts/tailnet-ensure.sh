#!/usr/bin/env bash
# Nhịp tim: bảo đảm tailscaled đang chạy và serve http=80 trỏ vào app. Idempotent, chạy tay hay từ cron.
set -uo pipefail
R="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" = 0 ]; then
  systemctl is-active --quiet tailscaled.service || systemctl start tailscaled.service
  exec "$R/tailnet-serve.sh"
fi

if systemctl is-enabled tailscaled.service >/dev/null 2>&1; then
  exec sudo -n "$R/tailnet-serve.sh"
fi

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
systemctl --user start osa-tailscaled.service >/dev/null 2>&1
exec "$R/tailnet-serve.sh"
