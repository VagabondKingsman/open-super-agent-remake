# Phiên 2026-11-17 · cursor · tác vụ lỗi không được trình bày kết quả

- Bắt đầu/kết thúc: 19:07–19:25 UTC (02:07–02:25 Asia/Saigon 18/11)
- Repo/base/branch: `origin/i18n-vi` = `63c99f6`, branch `fix/task-failed-no-results`, head = commit này
- Approval/scope: operator chọn hướng "sửa ở tầng OSA: worker lỗi 402/timeout thì không được trình bày kết quả, chỉ báo lỗi"
- AC: (1) tin `[任务 #N 结果]` của tác vụ lỗi mang luật rõ ràng; (2) câu trả lời ngay sau đó mà bày bảng PASS/exit code **khi lượt đó không có output công cụ nào** thì bị đính chính + ghi meta; (3) câu trả lời trung thực thì không bị đụng

## Vì sao

Thử full-mode trên bot OSA: worker chết vì xai hết tiền (`402 Payment Required`), `task_steps` ghi `note/error: Tác vụ thất bại: Hết hạn mức (402 -)`, nhưng Bot vẫn trả về bảng PASS với `mid=1234567890abcdef1234567890abcdef12345678`, `key_len=32`, `… (8 dòng cuối …)` — bằng chứng bịa. Đọc câu trả lời là tưởng đã chạy xong.

## Đã đổi (`osa/router.py`)

1. `failed_result_rule()` + `result_body(task)`: tin kết quả của tác vụ `failed` được nối thêm luật (dịch đủ vi/en/zh).
2. `TASK_FAILED_NOTE` (tiếng Anh, cho model) + `_last_failed` được ghi khi publish tác vụ lỗi.
3. Hậu kiểm trước khi lưu câu trả lời: nếu có `_last_failed` trong 30 phút, **lượt này không có tool output nào**, và câu trả lời khớp `claims_results()` (`| PASS |`, `PASS`, `FAIL`, `exit=<số>`, `✅`, `❌`) thì nối câu đính chính (stream + lưu) và ghi meta `unsupported_results = {task_id, error}`.
4. Cờ được reset mỗi lượt (`_unsupported_results = None`) để không dính sang lượt sau.
5. `osa/locales/en.json`, `vi.json`: hai khoá mới.

## Evidence

| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC-1 | PASS | `test_failed_result_carries_the_rule` (worker trả rỗng hai lần → task failed → tin kết quả chứa luật) |
| AC-2 | PASS | `test_reply_claiming_results_after_failure_is_corrected` ("\| 1 \| PASS \|… exit=0" → câu trả lời có "Đính chính" + meta `unsupported_results.task_id`) |
| AC-3 | PASS | `test_reply_without_claims_is_left_alone` (câu trả lời trung thực không bị thêm gì) |
| helper | PASS | 6 ca `claims_results`, 3 ca `result_body` |
| hồi quy | PASS | `test_audit_fixes + test_task_failed_no_results + test_stream_stall + test_observe` 114 passed; `python -m osa.i18n` 0 thiếu/0 thừa |

- Secrets/PII: không có key trong diff. Paid usage: 0 (test dùng fakellm).

## Còn mở

- Chưa chạy pytest toàn bộ — CI chạy.
- Chưa kiểm lại trên service thật sau restart (làm sau khi merge hoặc restart tay).
- Chưa chặn trường hợp Bot tự bịa **khi không có tác vụ nào lỗi** (C3 `verification.count_claims` đã bắt số liệu; bảng PASS không có số thì chưa bắt).
