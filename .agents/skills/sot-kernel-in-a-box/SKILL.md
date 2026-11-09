---
name: sot-kernel-in-a-box
description: >-
  Bridge Hoplite cho sot-kernel-in-a-box (bản gốc ở
  skills-pack/ai-native/sot-kernel-in-a-box). Dựng, kiểm toán, vận hành kho dữ
  liệu chuẩn nội bộ (Source of Truth) từ file có owner: adapter sang registry,
  SHA-256 phát hiện lệch nguồn, A3 Guard, 6 bite test, publish gate gắn digest.
  Dùng khi số liệu nội bộ phân tán dễ mâu thuẫn, cần audit số trước khi xuất
  báo cáo, hoặc đưa dữ liệu refinery đã duyệt vào kho chuẩn.
---

# sot-kernel-in-a-box · bridge cho Hoplite

- `SKILL_DIR` = `skills-pack/ai-native/sot-kernel-in-a-box/`. Chỉ đọc, không sửa (khóa SHA-256).
- Đọc **hết** `SKILL_DIR/SKILL.md`. Dựng dự án mới bằng cách chép `project_template/` ra `data/sot/<TASK-ID>/` (gitignored), không chạy trong `SKILL_DIR`. Công cụ ở `tools/`, ví dụ ở `examples/`.
- Mỗi file gốc phải có owner. Không tự biến claim thành `verified_primary`, không tự chọn số khi owner chưa duyệt. Hỏi người dùng.
- Publish gate phải gắn digest thật từ lần check vừa chạy. Việc nhiều bước thì nạp `ai-work-method` trước.
