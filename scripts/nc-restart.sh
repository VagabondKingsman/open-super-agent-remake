#!/usr/bin/env bash
# nc-restart.sh — restart the nodecode GATEWAY on a devbox without killing a CLI.
#
# Why: `kill` mọi pid có exe=*nodecode* giết luôn CLI đang giữ session của người;
# daemon có dựng lại một CLI mới nhưng nó không mở session nào, nên màn hình của
# người thành cửa sổ chết. Ở đây mặc định chỉ giết gateway; CLI để yên.
#
#   nc-restart.sh                 # chỉ gateway (an toàn cho người đang dùng)
#   nc-restart.sh --all           # giết cả CLI (mất màn hình; dùng --session để mở lại)
#   nc-restart.sh --session ID    # sau khi --all, mở lại session ID trên gateway mới
#   nc-restart.sh --dry-run       # chỉ in ra sẽ giết ai
#
# Mã thoát: 0 gateway lên lại; 1 không lên lại được; 2 có cảnh báo (CLI bị giết, session chưa mở lại).
set -uo pipefail

ALL=0 DRY=0 SESSION=""
while [ $# -gt 0 ]; do
  case "$1" in
    --all) ALL=1 ;;
    --dry-run) DRY=1 ;;
    --session) SESSION="${2:-}"; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "lạ: $1" >&2; exit 64 ;;
  esac
  shift
done

PORT="${NC_PORT:-37177}"
say() { printf '%s\n' "$*"; }

classify() {  # in ra "<pid> <kind>" cho từng tiến trình nodecode thật
  local p pid exe cmd kind
  for p in /proc/[0-9]*; do
    pid=${p#/proc/}
    [ "$pid" = "$$" ] && continue
    exe=$(readlink -f "$p/exe" 2>/dev/null) || continue
    case "$exe" in *nodecode) ;; *) continue ;; esac
    cmd=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
    case "$cmd" in
      *"gateway run"*) kind=gateway ;;
      *) kind=cli ;;
    esac
    printf '%s %s|%s\n' "$pid" "$kind" "${cmd:0:110}"
  done
}

mapfile -t PROCS < <(classify)
GW=() CLIS=()
for row in "${PROCS[@]:-}"; do
  [ -n "$row" ] || continue
  pid=${row%% *}; rest=${row#* }; kind=${rest%%|*}
  [ "$kind" = gateway ] && GW+=("$pid") || CLIS+=("$pid")
done

say "gateway: ${GW[*]:-（không có）}"
say "cli    : ${CLIS[*]:-（không có）}"
for row in "${PROCS[@]:-}"; do [ -n "$row" ] && say "  $row"; done

if [ "$DRY" = 1 ]; then
  if [ "$ALL" = 1 ]; then say "sẽ giết gateway + cli"; else say "sẽ giết gateway, giữ cli"; fi
  exit 0
fi

kill_set() {
  local pid
  for pid in "$@"; do
    say "TERM $pid"
    kill -TERM "$pid" 2>/dev/null || { say "TERM $pid lỗi, dùng -9"; kill -9 "$pid" 2>/dev/null; }
  done
}

[ ${#GW[@]} -gt 0 ] && kill_set "${GW[@]}"
if [ "$ALL" = 1 ] && [ ${#CLIS[@]} -gt 0 ]; then
  say "cảnh báo: giết cả CLI — màn hình của người sẽ mất, mở lại bằng --session"
  kill_set "${CLIS[@]}"
fi

# chờ daemon dựng lại; nếu quá 20 giây thì tự dựng (headless, không chiếm màn hình)
for i in $(seq 1 20); do
  sleep 1
  if ss -ltn 2>/dev/null | grep -q ":$PORT "; then
    say "port $PORT sống lại sau ${i}s"
    ss -ltnp 2>/dev/null | grep ":$PORT " | head -2
    if [ -n "$SESSION" ]; then
      say "mở lại session $SESSION (nền)"
      setsid nohup nodecode resume "$SESSION" >/tmp/nc-resume-$SESSION.log 2>&1 &
      sleep 2; say "log: /tmp/nc-resume-$SESSION.log"
    fi
    exit 0
  fi
done

say "port $PORT vẫn trống sau 20s — dựng gateway headless"
setsid nohup nodecode serve >/tmp/nc-serve.log 2>&1 &
for i in $(seq 1 20); do sleep 1; ss -ltn 2>/dev/null | grep -q ":$PORT " && { say "gateway lên sau ${i}s"; exit 0; }; done
say "KHÔNG lên lại được — xem /tmp/nc-serve.log"; exit 1
