# Phiên 2026-11-11 · cursor · câu ứng dụng điện thoại

- Royan: chữ trên mục Ứng dụng điện thoại đang ghi iPhone. App dùng là mobile, không ghi riêng iPhone.
- Base `18a0306` (merge PR #52).
- Skill Flow: osa-dev → ai-work-method → vibecode-kit. Câu tiếng Việt đi qua unslop-vi.

## Đã làm

Đổi khóa và bản en/vi của câu quét QR trong Cài đặt → Ứng dụng điện thoại.

- Khóa: `在手机上装好 Open Super Agent App…` (bỏ `iPhone`).
- Tiếng Việt: "trên điện thoại".
- Tiếng Anh: "on your phone".
- Không đụng câu đẩy thông báo qua Apple, không đụng changelog lịch sử của app iPhone upstream, không ghi hostname tailnet.

## Evidence

| AC | Kết quả | Bằng chứng |
|---|---|---|
| Câu QR không còn chữ iPhone | PASS | `git grep` trên `web/` không còn `在 iPhone 上装好` và `trên iPhone` |
| en/vi đủ khóa, thiếu 0 | PASS | `python -m osa.i18n` exit 0. Frontend dùng 1222 câu, thiếu 0. Ba khóa backend thừa và `删除这个对话` là sẵn có, exit vẫn 0 |
| Test web | PASS | `npm test` 43/43 |

- Paid usage: 0. Không deploy, trang đang chạy vẫn hiện câu cũ cho tới khi cập nhật server.
