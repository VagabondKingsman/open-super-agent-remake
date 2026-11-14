# Phiên 2026-11-14 · cursor · vòng 2: lỗ đã rà, phần còn sót (OSA-042)

- Bắt đầu/kết thúc: 13:05 → 14:30 Asia/Saigon
- Repo/base/branch: `VagabondKingsman/open-super-agent-remake`, base `i18n-vi`; nhánh `fix/holes-round2` (trên `fix/data-dir-holes` của PR #96)
- Approval/scope: theo yêu cầu “plan deep fix các vấn đề còn hở tránh phát sinh lỗi về sau, sau đó rà soát các vấn đề còn lại”. Không đụng `main`, không release.

## Vì sao có phiên này

Log của OSA-041 có danh sách phần còn hở. Phiên này đóng những cái sửa được bằng code, mỗi cái kèm một lý do “để sau này không phải đoán”.

## Đã làm

1. **Ba script đọc/ghi cứng `/home/boxes/osa-data`** (`ask.py`, `probe_run.py`, `scenario_from_log.py`, cùng dòng usage của `worker_cache.py`). Thêm `scripts/_paths.py` (chỉ stdlib): `OSA_DATA_DIR` → `.env` → thư mục của máy; script dùng `_paths.db()` / `_paths.password()`. Đo: mặc định ra `osa-data`, `OSA_DATA_DIR=/tmp/fakedata` ra `/tmp/fakedata`.
2. **`net-fast.sh` viết unit với đường log cứng.** Nay `DATADIR`/`LOGDIR` theo cùng nguồn, heredoc dùng `__LOGDIR__` rồi `sed` thay, và trước khi ghi unit system thì tắt unit user cũ (`osa-tailscaled`, `osa-tailnet`) để boot khỏi dựng hai `tailscaled`.
3. **Unit user cũ đã tắt.** `osa-tailscaled.service` đang `enabled` mà không chạy: lần boot sau là một `tailscaled` userspace thứ hai. Đã `disable`, và ghi đầu hai tệp rằng chúng chỉ dùng cho `net-fast-rollback.sh`.
4. **Log không có vòng xoay, và máy chưa có `logrotate`.** Thêm `scripts/logrotate-osa.conf` (copytruncate — systemd `append:` không nhận tín hiệu mở lại tệp) + `scripts/install-logrotate.sh` (cài gói nếu thiếu, kiểm bằng `logrotate -d`), `net-fast.sh` gọi nó.
5. **Điều tra task #1610 mất câu trả lời** (bị Watchdog huỷ sau 900 giây “không tiến triển”): từ 09:38:44 tới 09:49:57 không một dòng log nào — kể cả nhịp poll máy 60 giây/lần. Vậy không phải stream chậm: **cả event loop bị chặn ~11 phút**, mà timer của stream (60 giây) và của Watchdog đều không chạy được khi loop chặn. Hai vá:
   - `osa/looplag.py`: một luồng thường giữ nhịp, loop chặn quá `limits.loop_lag_s` (mặc định 5 giây) thì ghi WARNING và `faulthandler` đổ toàn bộ stack (tối đa 1 lần/phút cho mỗi lần chặn). Gắn vào lifespan cạnh `watchdog`.
   - `_cancel_text()` + `tasklog.tail()`: tin nhắn huỷ kèm 5 tên tool đã chạy xong. Trước đó người dùng chỉ thấy “[任务 #N 已取消]”, toàn bộ việc đã làm biến mất cùng task.
6. **`start.out`** đã xoá ở phiên trước, xác nhận không script nào ghi.

## Evidence

| Việc | Bằng chứng |
|---|---|
| Loop chặn 11 phút | log 09:38:44 → 09:49:57 trống hoàn toàn; không có `llm_calls` row cho lượt treo |
| Vẫn còn guard sống | 11:37:52 và 12:11:57 có `WARNING osa.router: ... không gửi thêm nội dung trong 60 giây` |
| Test mới | `tests/test_looplag.py`, `tests/test_cancel_digest.py` — 6 passed |
| Cả bộ | `pytest -q` 1269 passed, 3 skipped |
| i18n | `python -m osa.i18n`: 0 thiếu |

## Còn hở (không sửa bằng code được, chờ quyết)

- `gmail-reg-watchdog` đang tắt: Google chặn luồng QR. Cần quyết định dùng hay bỏ.
- `logrotate` chỉ vào máy khi có người chạy `net-fast.sh` (hoặc `install-logrotate.sh`) bằng root.
- Nguyên nhân đúng của cú chặn 11 phút chưa biết: chờ lần tới `looplag` in stack.
