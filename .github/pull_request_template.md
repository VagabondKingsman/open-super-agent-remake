## Task / mục tiêu

BOARD ID: <!-- ID --> · Owner bot: <!-- tên --> · Base: `i18n-vi`

<!-- Dùng mẫu đầy đủ ở .agents/templates/PR.md; không tự tick test chưa chạy. -->

## Đã đổi / lý do

## Verify và bằng chứng

<!-- Coverage, AC/tier results, commands/counts/exits/skips, R1–R5 và overall status. -->
<!-- Mẫu: .agents/templates/VERIFY-REPORT.md. Nêu Docker/Worker/browser deferred thật. -->

## Rủi ro / deferred / rollback

- [ ] Đúng remake-only; branch <bot>/<topic>, không force-push/upstream PR.
- [ ] VI mặc định, EN/ZH/placeholder; i18n + pytest + frontend tests/build phù hợp scope.
- [ ] Không secret/PII/DB/private traces/session links; đã review staged diff/scan.
- [ ] Temp data/fake LLM, không real channel sends; live paid run có approval/cap riêng nếu áp dụng.
- [ ] STATE + BOARD + log phiên cập nhật; no conflicting task owner.
- [ ] Đã kiểm docs/architecture.md; CHANGELOG và app/template validation nếu liên quan.

Hướng dẫn và templates: [.agents/README.md](../.agents/README.md), [PR](../.agents/templates/PR.md), [TIP](../.agents/templates/TIP.md), [VERIFY REPORT](../.agents/templates/VERIFY-REPORT.md), [handoff](../.agents/templates/HANDOFF.md).

Merge bởi Tin Tin hoặc bot được duyệt rõ. GO kỹ thuật không tự cấp quyền merge.
