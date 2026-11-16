#!/usr/bin/env bash
# pr-merge-wait.sh — chốt PR mà không tự viết vòng `for i in $(seq 1 40) … sleep 10`.
#
# Vì sao: vòng poll tay vừa chặt (không nhịn được rate limit) vừa chết theo máy —
# máy bị treo 5 giờ là 5 giờ nằm trong một lệnh shell. Ở đây: bật auto-merge để
# GitHub tự merge khi xanh, chỉ khi repo không cho auto-merge mới ngồi chờ checks
# với nhịp 30 giây, có trần thời gian, và bỏ qua được nhịp khi bị 429.
#
#   pr-merge-wait.sh 148              # auto-merge #148 khi xanh
#   pr-merge-wait.sh --watch 148 149  # không dùng auto-merge; ngồi chờ rồi merge
#   pr-merge-wait.sh --cap 45 148     # trần 45 phút cho mỗi PR (mặc định 60)
#   pr-merge-wait.sh --dry-run 148    # chỉ in trạng thái
#
# Mã thoát: 0 tất cả đã merge/đã bật auto-merge; 1 có PR không chốt được; 2 PR có xung đột.
set -uo pipefail

WATCH=0 DRY=0 CAP=60; PRS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --watch) WATCH=1 ;;
    --dry-run) DRY=1 ;;
    --cap) CAP="${2:-60}"; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    [0-9]*) PRS+=("$1") ;;
    *) echo "lạ: $1" >&2; exit 64 ;;
  esac
  shift
done
[ ${#PRS[@]} -gt 0 ] || { echo "cần số PR" >&2; exit 64; }

say() { printf '%s\n' "$*"; }
state() { gh pr view "$1" --json state,mergeable,mergeStateStatus --jq '"\(.state) \(.mergeable) \(.mergeStateStatus)"' 2>/dev/null || echo "?"; }

fails=0; conflicts=0
for n in "${PRS[@]}"; do
  s=$(state "$n"); say "#$n hiện tại: $s"
  case "$s" in
    MERGED*) say "#$n đã merge rồi"; continue ;;
    *CONFLICTING*) say "#$n XUNG ĐỘT — cần rebase"; conflicts=$((conflicts+1)); continue ;;
  esac
  if [ "$DRY" = 1 ]; then continue; fi

  if [ "$WATCH" = 0 ]; then
    if gh pr merge "$n" --auto --merge --delete-branch 2>/tmp/pmw-$n.err; then
      say "#$n → đã bật auto-merge (GitHub merge khi xanh)"
      continue
    fi
    say "#$n auto-merge không bật được: $(tr -d '\n' < /tmp/pmw-$n.err | cut -c1-160) — chuyển sang chờ"
  fi

  deadline=$(( $(date +%s) + CAP*60 ))
  while :; do
    s=$(state "$n")
    case "$s" in
      MERGED*) say "#$n đã merge"; break ;;
      *CONFLICTING*) say "#$n XUNG ĐỘT giữa chừng"; conflicts=$((conflicts+1)); break ;;
      CLEAN*|HAS_HOOKS*|*UNSTABLE*)
        if gh pr merge "$n" --merge --delete-branch 2>/tmp/pmw-$n.err; then say "#$n đã merge"; break; fi ;;
      *BLOCKED*) say "#$n bị chặn (review/rules) — để nguyên"; fails=$((fails+1)); break ;;
    esac
    [ "$(date +%s)" -ge "$deadline" ] && { say "#$n quá trần ${CAP} phút, trạng thái: $s"; fails=$((fails+1)); break; }
    gh pr checks "$n" --watch --interval 30 --fail-fast >/dev/null 2>&1 || sleep 30
    # nhịp chờ nghỉ có trần: mỗi vòng tối đa 30 giây, không giữ shell lâu hơn mức cần
    sleep 10
  done
done

say "—— xong: ${#PRS[@]} PR, lỗi=$fails, xung đột=$conflicts"
[ "$conflicts" -gt 0 ] && exit 2
[ "$fails" -gt 0 ] && exit 1
exit 0
