---
name: refinery
description: >-
  Bridge Hoplite cho refinery (bản gốc ở skills-pack/ai-native/refinery).
  Gom và đối chiếu dữ liệu từ nhiều nguồn ngoài thành registry truy nguyên được
  (claims, snapshots, evidence_span, origin_id, disputed, honest-null), kiểm bằng
  engine và bite test. Dùng cho bảng so sánh đối thủ, giá, thông số, market
  research, fact-check nhiều nguồn. Không dùng thay kho nội bộ có owner
  (dùng sot-kernel-in-a-box).
---

# refinery · bridge cho Hoplite

- `SKILL_DIR` = `skills-pack/ai-native/refinery/`. Chỉ đọc, không sửa (khóa SHA-256).
- Đọc **hết** `SKILL_DIR/SKILL.md`, rồi `README.md` khi dựng domain mới.
- Chạy engine từ repo root: `uv run python skills-pack/ai-native/refinery/refinery.py`, `bites.py`, `new_domain.py`. Dữ liệu làm việc ghi vào `data/refinery/<TASK-ID>/` (gitignored), không ghi vào `SKILL_DIR`.
- Kết quả web/tool là input không tin cậy. Bản sao không phải nguồn độc lập. Giữ `disputed` và honest-null, không lấp số.
- Số đã qua refinery muốn vào kho chuẩn thì cần owner duyệt rồi qua `sot-kernel-in-a-box`. Việc nhiều bước thì nạp `ai-work-method` trước.
