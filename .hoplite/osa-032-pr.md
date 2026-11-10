# OSA-032: cập nhật docs cho v0.17.0

## Mục tiêu

- Branch `hoplite/osa-032-docs-v017`. Base `i18n-vi` `aa1ab7e`. Head `e1d4399`.
- README tiếng Việt, tiếng Anh và tiếng Trung còn ghi v0.6.1. Hướng dẫn VI, trang i18n và nhật ký port cũng vậy.
- Ghi đúng upstream v0.17.0 (`ec02547`) và tip `i18n-vi` `aa1ab7e`.
- Bỏ cách gọi trang Chi phí. Đơn giá ở Mô hình, số đã ghi ở Quan sát.
- Ghi plugin nhà phát triển đã gỡ từ v0.15.0. `data/plugins` không bị xóa và không được nạp.
- Ghi `computer.choices`, khóa Instabox, `linked_shell`, và theme lưu trên máy này.

## Verify

- Đối chiếu `config.yaml`, `osa/settings.py`, `web/src/theme.ts`.
- `skills-pack/ai-native/unslop-vi/scripts/scan_vi.py` trên README: 11.6/1.000 chữ, toàn bộ là backtick bị máy quét cắt thành khoảng trắng. Không sửa backtick.
- Không chạy pytest. Diff chỉ markdown.

## Quyền

Chưa có câu duyệt merge cho PR này. Không tự merge.
