# 2026-11-10: PR #37 stream stall và CI chạy test sandbox

Người làm: Build Bot. Giờ ghi theo Asia/Saigon (UTC+7).

## PR #37: model call bị treo stream

- Nguyên nhân: task Nova #253 bị Watchdog hủy ("Không có tiến triển trong 3 phút") vì stream xAI im khoảng 183 giây giữa câu trả lời. OSA không có timeout khi stream im và không retry sau khi stream đã mở.
- Sửa: `limits.stream_idle_s` (mặc định 120 giây, ngắn hơn 3 phút của Watchdog) đóng stream im; `limits.stream_retries` (mặc định 1) gọi lại khi stream treo, rớt kết nối, gặp 5xx hoặc báo "at capacity". Lỗi quota và request sai không retry. Router chỉ retry khi UI chưa nhận chữ nào.
- Test: 9 test mới trong `tests/test_stream_stall.py`. Local 828 passed, 1 skipped (chỉ macOS). Chạy lại cùng goal ở task #259: done sau 597 giây. Đường retry chưa được kích hoạt thật vì lần chạy lại không bị treo.
- Merge vào `i18n-vi` tại `0500666`. CI backend, frontend, docker xanh.

## CI chạy đủ 3 test sandbox

- Trước đây runner GitHub không có `bwrap`, nên 3 test trong `tests/test_local_checks.py` SKIP trên CI.
- Bây giờ job backend cài `bubblewrap`, đặt `kernel.apparmor_restrict_unprivileged_userns=0`, thử `bwrap` một lần, rồi chạy `pytest -q -rs` với `OSA_REQUIRE_SANDBOX=1`.
- Khi `OSA_REQUIRE_SANDBOX=1`, ba test không SKIP. Thiếu sandbox thì chúng FAIL. Đã thử trên box bằng PATH không có `bwrap`: 3 failed, 6 passed.
- Local có `bwrap`: `pytest -q` 828 passed, 1 skipped (`test_host_desktop`, chỉ macOS).

## Còn mở

- `test_host_desktop` vẫn SKIP trên Linux, vì cần macOS và `OSA_TEST_DESKTOP=1`.
- `test_real_chrome` đã chạy trên CI (xem mục dưới).

## CI chạy test_real_chrome

- Nguyên nhân timeout ở PR #36: runner không có màn hình (`DISPLAY` trống), Chrome có giao diện không khởi động được nên không ghi `DevToolsActivePort`, helper báo "không mở cổng debug trong 20 giây". Đã tái hiện trên box: bỏ `DISPLAY` thì test fail đúng lỗi này, chạy trong `xvfb-run -a` thì pass sau 3,8 giây.
- Sửa: job backend cài thêm `xvfb`, in `google-chrome --version`, đặt `OSA_TEST_CHROME=1` và chạy `xvfb-run -a uv run pytest -q -rs`. Sandbox Chrome dùng user namespace, đã mở ở bước bubblewrap.
- Code sản phẩm không đổi.
