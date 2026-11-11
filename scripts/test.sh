#!/usr/bin/env bash
# Chạy cả bộ test. Máy Linux không có màn hình thì bọc bằng xvfb-run, để mấy test dùng
# Chrome thật (mở trang, bấm, tải file) cũng chạy — thiếu nó chúng tự skip và lỗi chỉ lộ ra trên máy thật.
# Thêm tham số thì chuyển tiếp: scripts/test.sh tests/test_fastsrv.py -x
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v xvfb-run >/dev/null 2>&1; then
  exec xvfb-run -a uv run pytest -q "$@"
fi
exec uv run pytest -q "$@"
