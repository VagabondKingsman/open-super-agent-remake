---
name: unslop-vi
description: >-
  Bridge Hoplite cho unslop-vi (bản gốc ở skills-pack/ai-native/unslop-vi).
  Viết và soát prose tiếng Việt cho README, docs, mô tả PR, log .agents của OSA:
  bỏ sáo ngữ, văn dịch máy, danh hóa thừa, câu chatbot. Không dùng cho dịch
  thuần hay sửa một lỗi chính tả.
---

# unslop-vi · bridge cho Hoplite

- `SKILL_DIR` = `skills-pack/ai-native/unslop-vi/`. Chỉ đọc, không sửa (khóa SHA-256).
- Đọc **hết** `SKILL_DIR/SKILL.md`, rồi reference nó chỉ định.
- Quét bản nháp: `uv run python skills-pack/ai-native/unslop-vi/scripts/scan_vi.py <file>` (hoặc `-` cho stdin; `--compare TRUOC SAU` để so hai bản).
- Scanner chỉ gợi ý. Đọc lại bằng phán đoán; giữ số liệu, tên lệnh, đường dẫn, thuật ngữ kỹ thuật và vùng code nguyên văn.
- Prose tiếng Anh dùng `skills-pack/ai-native/unslop/SKILL.md` theo cùng cách.
