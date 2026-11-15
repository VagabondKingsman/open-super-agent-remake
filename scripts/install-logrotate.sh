#!/usr/bin/env bash
# Cài logrotate cho log của OSA (root, idempotent). Gọi từ net-fast.sh, hoặc chạy riêng:
#   sudo ~/osa/scripts/install-logrotate.sh
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "cần root"; exit 1; }
if ! command -v logrotate >/dev/null; then
  apt-get update -qq && apt-get install -y -qq logrotate || { echo "apt không cài được logrotate"; exit 1; }
fi
# thư mục log theo OSA_DATA_DIR → .env → mặc định của máy; conf là mẫu, đường dẫn điền lúc cài
REPO=$(cd "$(dirname "$0")/.." && pwd); H=$(dirname "$REPO")
DATADIR="${OSA_DATA_DIR:-$(grep -h '^OSA_DATA_DIR=' "$REPO/.env" 2>/dev/null | tail -1 | cut -d= -f2-)}"
DATADIR="${DATADIR:-$H/osa-data}"
SRC=$(cd "$(dirname "$0")" && pwd)/logrotate-osa.conf
tmp=$(mktemp)
sed "s#__LOGDIR__#$DATADIR/logs#" "$SRC" > "$tmp"
install -m 0644 "$tmp" /etc/logrotate.d/osa; rm -f "$tmp"
logrotate -d /etc/logrotate.d/osa >/dev/null 2>&1 && echo "[logrotate] đã cài và conf hợp lệ" || { echo "[logrotate] conf lỗi, xem: logrotate -d /etc/logrotate.d/osa"; exit 1; }
