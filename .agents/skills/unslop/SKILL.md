---
name: unslop
description: >-
  Bridge Hoplite cho unslop (bản gốc ở skills-pack/ai-native/unslop). Viết và
  soát tiếng Anh tự nhiên, không dấu vết AI: README.en, docs EN, chuỗi UI tiếng
  Anh, mô tả PR tiếng Anh, blog từ brief tiếng Việt kèm SEO và tóm tắt VI.
  Không dùng cho code hay dịch nguyên văn.
---

# unslop · bridge cho Hoplite

- `SKILL_DIR` = `skills-pack/ai-native/unslop/`. Chỉ đọc, không sửa (khóa SHA-256).
- Đọc **hết** `SKILL_DIR/SKILL.md`, rồi reference nó chỉ định.
- Quét bản nháp: `uv run python skills-pack/ai-native/unslop/scripts/scan_en.py <file>` (hoặc `-` cho stdin).
- Scanner chỉ gợi ý. Đọc lại bằng phán đoán; giữ số liệu, tên lệnh, đường dẫn, key i18n và vùng code nguyên văn.
- Prose tiếng Việt dùng bridge `unslop-vi`.
