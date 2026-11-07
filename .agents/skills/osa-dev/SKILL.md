---
name: osa-dev
description: >-
  Phát triển / sửa bug / thêm tính năng cho open-super-agent remake (OSA) của
  Tin Tin. Dùng khi làm việc với repo
  VagabondKingsman/open-super-agent-remake: fix bug, i18n, Computer, channels,
  upstream merge, docs VI, hoặc khi user nói OSA / open-super-agent / remake.
  Skill Flow mặc định: ai-work-method + vibecode-kit (+ unslop-vi cho prose VI).
---
# osa-dev · Open Super Agent remake

Skill Flow mặc định: `osa-dev` → `ai-work-method` → `vibecode-kit` (thêm `unslop-vi` khi viết README/docs VI).

## Ngữ cảnh cố định

- Checkout: repo root của máy hiện tại; base tích hợp `i18n-vi`, branch làm việc `<bot>/<topic>`.
- Remake GitHub: `https://github.com/VagabondKingsman/open-super-agent-remake` (base `i18n-vi`; kiểm ref hiện tại, không đoán `main` cùng tip).
- Upstream: `kadaliao/open-super-agent`; **không** push/PR lên upstream; chỉ công bố vào remake theo `.agents/RULES.md`.
- Docs VI: `docs/huong-dan-vi.md`, `docs/cap-nhat-tu-upstream.md`.
- AI Native packages: `skills-pack/ai-native/` trong repo. Handoff chung: `.agents/README.md`.

## Bước

1. Load `ai-work-method` rồi `vibecode-kit` bằng Skill; ghi `Skill Flow: osa-dev -> ai-work-method -> vibecode-kit`.
2. SCAN checkout hiện tại trong phạm vi công cụ/quyền cho phép (và docs/roadmap nếu liên quan). Đọc TIP/AC ngắn.
3. BUILD / sửa code repo: CloudAgent trên remake theo `code-changes` (không force-push; không PR lên kadaliao). Local chỉ đọc/verify/smoke (`scripts/osa-start.sh`, tests).
4. VERIFY: chạy test/smoke quan sát được; Computer cần Docker; nếu `docker_missing` thì ghi rõ, không giả PASS.
5. Prose VI (README, docs, chat user-facing): load `unslop-vi`.
6. User chỉ định skill/flow khác → ưu tiên flow đó, vẫn giữ ràng buộc remake-only + CloudAgent.
7. Báo cáo DONE/PARTIAL/BLOCKED + bằng chứng (commit SHA, link file, kết quả test).

## Ghi chú portability

Port từ bridge osa-dev đang dùng của Build Bot, giữ phương pháp và bỏ đường dẫn riêng/mirror ngoài repo. Tài liệu không cấp quyền clone/publish/merge hay paid API; xem `.agents/RULES.md` và policy công cụ của tài khoản.
