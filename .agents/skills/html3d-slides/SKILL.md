---
name: html3d-slides
description: >-
  Bridge Hoplite cho html3d-slides (bản gốc ở skills-pack/ai-native/html3d-slides).
  Thiết kế, dựng hoặc nâng cấp slide trình chiếu HTML tương tác có 3D
  (Three.js/WebGL/WebGPU): brief, storyboard, ba lớp DOM + 3D + Ambient chung
  state, người nói điều khiển nhịp, đo UI bằng measure-ui.js, đóng gói HTML chạy
  độc lập. Không dùng khi cần file PowerPoint (.pptx).
---

# html3d-slides · bridge cho Hoplite

- `SKILL_DIR` = `skills-pack/ai-native/html3d-slides/`. Chỉ đọc, không sửa (khóa SHA-256).
- Đọc **hết** `SKILL_DIR/SKILL.md`. Mở `references/` theo bước bản gốc chỉ định. Lấy khung từ `assets/`, chạy kiểm UI bằng `scripts/` (kể cả `measure-ui.js`).
- Deck dựng trong `data/slides/<TASK-ID>/` (gitignored) hoặc thư mục người dùng chỉ định, không ghi vào `SKILL_DIR`.
- Kiểm trên trình duyệt thật qua Preview của Hoplite: ảnh chụp từng slide, GPU fallback. Build xanh không thay ảnh chụp.
- Slide có số liệu cần kiểm chứng thì nạp `ai-work-method`, số đi qua `refinery` hoặc `sot-kernel-in-a-box`. Chữ trên slide tiếng Việt thì soát bằng `unslop-vi`.
