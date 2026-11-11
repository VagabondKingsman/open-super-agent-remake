#!/usr/bin/env bash
# 给前端构建产物做预压缩（.gz），fastsrv.py 直接发它：慢链路首屏 ~965KB -> ~305KB。
# 幂等：只压比源文件旧的。前端重建后跑一次即可（osa-up.sh 会自动跑）。
set -uo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)/osa/static/dist/assets"
[ -d "$D" ] || exit 0
n=0
for f in "$D"/*.js "$D"/*.css "$D"/*.svg "$D"/*.json; do
  [ -f "$f" ] || continue
  if [ ! -f "$f.gz" ] || [ "$f" -nt "$f.gz" ]; then
    gzip -9 -n -c "$f" > "$f.gz.tmp" && mv "$f.gz.tmp" "$f.gz" && n=$((n+1))
  fi
done
echo "fast-assets: $n 个文件已压缩"
