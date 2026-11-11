#!/usr/bin/env bash
# net-fast-rollback.sh — quay lại tailscaled userspace + 3 unit user (đường cũ).
# Chạy bằng root. Không xoá gì của bản mới, chỉ tắt nó.
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "cần root"; exit 1; }
U=boxes; UIDB=1002; H=/home/boxes
say() { echo "[rollback] $*"; }

say "tắt unit system"
systemctl disable --now osa-tailnet.service osa.service tailscaled.service >/dev/null 2>&1
systemctl daemon-reload

# giữ nguyên danh tính: state mới nhất từ /var/lib quay về $HOME
if [ -s /var/lib/tailscale/tailscaled.state ]; then
  cp /var/lib/tailscale/tailscaled.state "$H/.tailscale/tailscaled.state"
  chown "$U:$U" "$H/.tailscale/tailscaled.state"; chmod 600 "$H/.tailscale/tailscaled.state"
fi

say "bật lại unit user"
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user daemon-reload
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user enable --now osa-tailscaled.service osa.service
sleep 3
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user start osa-tailnet.service
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user is-active osa-tailscaled osa osa-tailnet | tr '\n' ' '; echo
