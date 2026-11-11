#!/usr/bin/env bash
# Kiểm tra nhanh: mọi thứ trình duyệt tải qua gzip phải giải nén ra đúng byte gốc.
# Chạy sau mỗi lần sửa code server hoặc rebuild frontend. Exit != 0 nghĩa là trang sẽ trắng/đen.
set -uo pipefail
U="${OSA_URL:-http://127.0.0.1:8765}"
H=(); [ -n "${OSA_HOST:-}" ] && H=(-H "Host: $OSA_HOST")
D="$(cd "$(dirname "$0")/.." && pwd)/osa/static/dist"
bad=0
chk() { # $1 url, $2 file gốc (rỗng = chỉ so với bản không nén)
  local tmp got want
  tmp=$(mktemp)
  curl -fsS "${H[@]}" -H 'Accept-Encoding: gzip' "$U$1" -o "$tmp" || { echo "  FAIL $1 (không tải được)"; bad=1; rm -f "$tmp"; return; }
  got=$(gunzip -c "$tmp" 2>/dev/null | wc -c)
  if [ -n "${2:-}" ] && [ -f "$2" ]; then want=$(stat -c%s "$2")
  else want=$(curl -fsS "${H[@]}" -H 'Accept-Encoding: identity' "$U$1" | wc -c); fi
  if [ "$got" = "$want" ]; then echo "  ok   $1  $got B"; else echo "  FAIL $1  giải nén $got B, phải $want B"; bad=1; fi
  rm -f "$tmp"
}
chk /login
for f in $(grep -oE '/assets/[^"]+' "$D/index.html" | tr -d '"'); do chk "$f" "$D/${f#/}"; done
exit $bad
