# Phiên 2026-11-11 · cursor · menu bot

- Royan: trong chi tiết bot có nút sao chép ID. Chuột phải hoặc nhấn giữ một bot ở thanh bên, ngoài Ghim, thêm sao chép ID, đánh dấu chưa đọc, ẩn, xóa, và mở trang sửa chi tiết.
- Base `18a0306`.
- Skill Flow: osa-dev → ai-work-method → vibecode-kit.

## Đã làm

- ID là số nguyên tạo cùng bot (`bots._next_id`), không tái sử dụng. Chi tiết bot hiện số đó và nút sao chép. Trang http dùng `document.execCommand('copy')` khi Clipboard API không có.
- `bots.hidden` và `chats.unread_mark`. Ẩn thì bot rời danh sách chính, nằm dưới mục Bot đã ẩn. Mở hội thoại thì xóa cờ chưa đọc.
- Menu: Ghim, đánh dấu chưa đọc, sao chép ID, ẩn hoặc hiện, sửa chi tiết, xóa. Xóa bot chính trả lỗi của server. Nhấn giữ 480 ms mở cùng menu với chuột phải.
- Sau review: chuột phải không nuốt click kế tiếp. Mục Bot đã ẩn hiện dấu chờ xác nhận và số chưa đọc, từng dòng cũng có huy hiệu. Danh sách ẩn cuộn trong 32vh.

## Evidence

| AC | Kết quả | Bằng chứng |
|---|---|---|
| Ẩn bot, giữ cờ khi đổi tên, đánh dấu chưa đọc | PASS | `pytest tests/test_bot_row_actions.py tests/test_bots_direct_chats.py`: 8 passed |
| en/vi thiếu 0 | PASS | `python -m osa.i18n` exit 0. Frontend 1231 câu, thiếu 0 |
| Typecheck và test web | PASS | `tsc --noEmit` exit 0. `npm test` 43/43. Sau review, `tsc --noEmit` lại exit 0 |
| Toàn bộ pytest | PASS | 1158 passed, 3 skipped, 103 giây |

- Paid usage: 0. Chưa deploy, nên trang đang chạy chưa có menu mới.
