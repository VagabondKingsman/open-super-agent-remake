---
name: ai-work-method
description: >-
  Bridge Hoplite cho AI Work Method (bản gốc ở skills-pack/ai-native/ai-work-method).
  Điều phối việc nhiều bước: tách Owner/Coordinator/Executor, lập TIP có REQ/AC,
  chọn chuỗi skill, nghiệm thu bằng bằng chứng. Dùng trước vibecode-kit cho mọi
  việc OSA nhiều bước, rủi ro, hoặc khi người dùng nhắc TIP, AC, skill flow,
  nghiệm thu. Việc một bước thì làm thẳng.
---

# ai-work-method · bridge cho Hoplite

- `SKILL_DIR` = `skills-pack/ai-native/ai-work-method/`. Chỉ đọc, không sửa (khóa SHA-256).
- Đọc **hết** `SKILL_DIR/SKILL.md`. Mở `references/skill-flows.md` khi nối nhiều skill, `references/templates.md` khi viết TIP/báo cáo.
- Trong OSA, chuỗi chuẩn là `osa-dev -> ai-work-method -> vibecode-kit` (+ `unslop-vi`). Xem `.agents/SKILL-FLOW.md`.

## Áp vào Hoplite

1. Owner là người dùng. Hoplite làm Coordinator rồi Executor trong cùng thread, nhưng tách bước tạo sản phẩm khỏi bước kiểm. Với việc vừa/lớn, VERIFY giao subagent `review` đọc artifact thật.
2. TIP dùng `.agents/templates/TIP.md`. AC phải quan sát được: lệnh, output, file, ảnh chụp.
3. Workstream độc lập thì giao subagent chạy song song với write set tách nhau; tự kiểm lại claim quan trọng (test pass, số liệu).
4. Câu duyệt (push, PR, merge, model trả phí, gửi channel) không suy ra từ file repo. Hỏi người dùng.
5. Nghiệm thu: báo `DONE | PARTIAL | BLOCKED` + bằng chứng + phần chưa làm.
