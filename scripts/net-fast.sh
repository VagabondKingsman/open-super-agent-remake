#!/usr/bin/env bash
# net-fast.sh — chuyển đường vào OSA từ tailscaled userspace-networking sang TUN (kernel),
# và đưa app lên system unit để thứ tự boot rõ ràng. Chạy bằng root. Idempotent.
#
#   sudo ~/osa/scripts/net-fast.sh          (hoặc: root-supervisor-launcher bash ~/osa/scripts/net-fast.sh)
#
# Vì sao nhanh hơn:
#   * TUN  -> gói đi qua kernel, không qua netstack gVisor  => thông lượng cao hơn nhiều, CPU thấp hơn
#   * UDP thật trên cổng 41641 => NAT traversal chạy => kết nối TRỰC TIẾP thay vì DERP (bỏ 1-2 chặng relay)
set -uo pipefail

[ "$(id -u)" = 0 ] || { echo "cần root"; exit 1; }
U=boxes; UIDB=1002; H=/home/boxes
STAMP=$(date +%Y%m%d-%H%M%S)
BK="${OSA_BACKUP_DIR:-$H/osa-backups}/net-backup-$STAMP"
TSSTATE=/var/lib/tailscale/tailscaled.state
# nơi ghi log: theo OSA_DATA_DIR, rồi .env, rồi thư mục mặc định của máy này
DATADIR="${OSA_DATA_DIR:-$(grep -h '^OSA_DATA_DIR=' "$H/osa/.env" 2>/dev/null | tail -1 | cut -d= -f2-)}"
DATADIR="${DATADIR:-$H/osa-data}"
LOGDIR="$DATADIR/logs"
say() { echo "[net-fast] $*"; }

install -d -m 0755 "$LOGDIR"
# log append của systemd không tự lớn-mãi được: logrotate (copytruncate)
bash "$H/osa/scripts/install-logrotate.sh" || say "logrotate chưa cài được, log vẫn lớn dần"
say "backup -> $BK"
install -d -m 0755 "$BK"
cp -a "$H/.config/systemd/user" "$BK/user-units" 2>/dev/null || true
cp -a "$H/.tailscale/tailscaled.state" "$BK/tailscaled.state" 2>/dev/null || true

# 1) binary vào /usr/local/bin (root service không phụ thuộc $HOME 0700 của user)
say "cài binary"
install -m 0755 "$H/.local/tailscale/tailscaled" /usr/local/bin/tailscaled
install -m 0755 "$H/.local/tailscale/tailscale"  /usr/local/bin/tailscale

# 2) dừng & tắt 3 unit cũ của user
say "dừng unit user cũ"
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user stop osa-tailnet.service osa.service osa-tailscaled.service 2>/dev/null || true
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user disable osa-tailnet.service osa.service osa-tailscaled.service 2>/dev/null || true
pkill -x tailscaled 2>/dev/null || true   # dọn daemon mồ côi giữ socket
sleep 1

# 3) state sang /var/lib (giữ nguyên node key + serve config => không phải login lại)
say "chuyển state"
install -d -m 0700 /var/lib/tailscale /run/tailscale
if [ ! -s "$TSSTATE" ]; then cp "$H/.tailscale/tailscaled.state" "$TSSTATE"; fi
chown root:root "$TSSTATE" 2>/dev/null; chmod 600 "$TSSTATE" 2>/dev/null

# 4) unit system
say "ghi unit system"
cat >/etc/systemd/system/tailscaled.service <<'UNIT'
[Unit]
Description=Tailscale node agent (TUN, kernel path)
Documentation=https://tailscale.com/kb/
Wants=network-pre.target
After=network-pre.target
Before=network-online.target

[Service]
Type=notify
# eth0 chỉ có link-local: netmon tưởng offline, login sẽ treo "awaiting unpause" nếu thiếu cờ này
Environment=TS_ASSUME_NETWORK_UP_FOR_TEST=1
ExecStartPre=/usr/local/bin/tailscaled --cleanup
ExecStart=/usr/local/bin/tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/run/tailscale/tailscaled.sock --port=41641
ExecStopPost=/usr/local/bin/tailscaled --cleanup
Restart=on-failure
RestartSec=3
StartLimitIntervalSec=0
RuntimeDirectory=tailscale
RuntimeDirectoryMode=0755
StateDirectory=tailscale
StateDirectoryMode=0700
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
UNIT

# osa là unit USER (một chủ cổng 8765, restart không cần quyền). Ở đây chỉ ghi bản system để .off làm tham chiếu:
cat >/etc/systemd/system/osa.service.off <<'UNIT'
[Unit]
Description=OSA app (127.0.0.1:8765)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=boxes
Group=boxes
WorkingDirectory=/home/boxes/osa
EnvironmentFile=/home/boxes/osa/.env
Environment=HOME=/home/boxes
Environment="PATH=/home/boxes/osa/.venv/bin:/home/boxes/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=/home/boxes/osa/.venv/bin/uvicorn osa.server:app --host 127.0.0.1 --port 8765 --proxy-headers
Restart=always
RestartSec=3
TimeoutStopSec=20
StandardOutput=append:__LOGDIR__/osa.log
StandardError=append:__LOGDIR__/osa.log

[Install]
WantedBy=multi-user.target
UNIT
sed -i "s#__LOGDIR__#$LOGDIR#g" /etc/systemd/system/osa.service.off

cat >/etc/systemd/system/osa-tailnet.service <<'UNIT'
[Unit]
Description=OSA tailnet entry (tailscale serve http=80 -> 127.0.0.1:8765, tailnet only)
After=tailscaled.service osa.service
Wants=tailscaled.service osa.service

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=HOME=/home/boxes
Environment=TS_AUTHKEY_FILE=/home/boxes/osa/.env
ExecStart=/home/boxes/osa/scripts/tailnet-serve.sh
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
# unit user cũ (tailscaled userspace + tailnet serve) nay bị unit system thay: tắt để boot khỏi dựng hai tailscaled
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user disable --now osa-tailscaled.service osa-tailnet.service >/dev/null 2>&1 || true

# 5) sysctl: đệm TCP rộng cho đường dài (kernel này không có BBR/fq, chỉnh được phần đệm)
say "sysctl"
cat >/etc/sysctl.d/99-osa-net.conf <<'SYS'
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.ipv4.tcp_rmem = 4096 262144 33554432
net.ipv4.tcp_wmem = 4096 262144 33554432
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_tw_reuse = 1
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
SYS
sysctl -q -p /etc/sysctl.d/99-osa-net.conf

# 6) bật
say "bật tailscaled"
systemctl enable --now tailscaled.service >/dev/null 2>&1
for i in $(seq 1 60); do
  st=$(/usr/local/bin/tailscale --socket=/run/tailscale/tailscaled.sock status --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("BackendState","?"))' 2>/dev/null)
  [ "$st" = "Running" ] && break; sleep 1
done
if [ "${st:-?}" != "Running" ]; then
  K=$(grep -h '^TS_AUTHKEY=' "$H/osa/.env" 2>/dev/null | tail -1 | cut -d= -f2-)
  say "chưa Running ($st) -> up bằng authkey"
  [ -n "${K:-}" ] && /usr/local/bin/tailscale --socket=/run/tailscale/tailscaled.sock up --authkey="$K" --hostname=osa --accept-dns=false
fi

say "bật app (unit user: không đụng unit system)"
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user daemon-reload >/dev/null 2>&1
runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user enable --now osa.service >/dev/null 2>&1
for i in $(seq 1 40); do curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:8765/manifest.json && break; sleep 1; done

say "bật đường tailnet"
systemctl enable --now osa-tailnet.service

sleep 3
say "== kết quả =="
/usr/local/bin/tailscale --socket=/run/tailscale/tailscaled.sock status | head -5
/usr/local/bin/tailscale --socket=/run/tailscale/tailscaled.sock netcheck 2>/dev/null | grep -E "UDP|Nearest|Mapping|PortMapping"
/usr/local/bin/tailscale --socket=/run/tailscale/tailscaled.sock serve status
systemctl is-active tailscaled osa-tailnet | tr '\n' ' '; runuser -u "$U" -- env XDG_RUNTIME_DIR=/run/user/$UIDB systemctl --user is-active osa | tr '\n' ' '; echo
say "xong. rollback: net-fast-rollback.sh $STAMP"
