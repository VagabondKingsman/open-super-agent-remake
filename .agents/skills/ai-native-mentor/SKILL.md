---
name: ai-native-mentor
description: >-
  Bridge Hoplite cho ai-native-mentor (bản gốc ở
  skills-pack/ai-native/ai-native-mentor). Hướng dẫn chọn và nối các skill AI
  Native (ai-work-method, vibecode-kit, refinery, sot-kernel-in-a-box,
  html3d-slides, unslop, unslop-vi) khi việc trộn research, dữ liệu, code hoặc
  slide, cần TIP/AC hoặc Deep Check. Không ép quy trình cho việc nhỏ.
---

# ai-native-mentor · bridge cho Hoplite

- `SKILL_DIR` = `skills-pack/ai-native/ai-native-mentor/`. Chỉ đọc, không sửa (khóa SHA-256).
- Đọc **hết** `SKILL_DIR/SKILL.md` và `references/` khi cần chọn chuỗi skill.
- Với repo OSA, chuỗi chuẩn vẫn là `osa-dev -> ai-work-method -> vibecode-kit` (+ `unslop-vi`). Xem `.agents/SKILL-FLOW.md`. Mentor chỉ giúp chọn thêm `refinery`, `sot-kernel-in-a-box`, `html3d-slides`, `unslop` khi việc cần.
- Mỗi skill được chọn thì nạp bridge của nó trong `.agents/skills/`, không gọi tên rồi coi như đã nạp.
