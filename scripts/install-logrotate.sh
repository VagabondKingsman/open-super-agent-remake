#!/usr/bin/env bash
# Cài logrotate cho log của OSA (root, idempotent). Gọi từ net-fast.sh, hoặc chạy riêng:
#   sudo ~/osa/scripts/install-logrotate.sh
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "cần root"; exit 1; }
if ! command -v logrotate >/dev/null; then
  apt-get update -qq && apt-get install -y -qq logrotate || { echo "apt không cài được logrotate"; exit 1; }
fi
SRC=$(cd "$(dirname "$0")" && pwd)/logrotate-osa.conf
install -m 0644 "$SRC" /etc/logrotate.d/osa
logrotate -d /etc/logrotate.d/osa >/dev/null 2>&1 && echo "[logrotate] đã cài và conf hợp lệ" || { echo "[logrotate] conf lỗi, xem: logrotate -d /etc/logrotate.d/osa"; exit 1; }
