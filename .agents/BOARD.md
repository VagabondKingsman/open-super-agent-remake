# Bảng việc chung

Snapshot 07/11/2026, Asia/Saigon (UTC+7). GitHub PR + base mới là trạng thái phối hợp; file local chưa push không giữ chỗ ở tài khoản khác.

## Claim protocol

1. Pull/fetch i18n-vi, đọc bảng + PR đang mở. Chọn task chưa có owner, dùng ID cố định dưới đây.
2. Sau approval cho publish, mở claim PR nhỏ sửa đúng dòng: `ID / owner bot / branch <bot>/<topic> / scope / claimed_at Asia/Saigon / PR link khi có`. Hoặc ghi claim trong PR thực thi nếu việc nhỏ.
3. Chỉ coi claim đã nhận khi claim PR merge hoặc Tin Tin xác nhận owner rõ. PR còn mở là tín hiệu phối hợp, không distributed lock. Kiểm lại ngay trước BUILD; hai claim trùng thì dừng phần chồng và để Tin Tin/owner thống nhất, không giành bằng force-push.
4. Chưa được phép PR/push: chuẩn bị claim draft và báo chưa giữ chỗ, không tự công bố. Chi tiết có thể thực hiện độc lập theo scope người dùng giao, không sửa chồng.
5. Cuối phiên cập nhật progress/blocker/next step; nghỉ hoặc bỏ việc thì chuyển về backlog với lý do, giữ log. Không tự tước owner vì “quá hạn” khi chưa thống nhất.
6. PR code gắn task ID + TIP/VERIFY/log; merge xong chuyển Done và cập nhật STATE. Chưa merge phải ghi local/PR-ready, không Done public.

## Backlog

| ID | Việc | AC khởi điểm / điều kiện | Owner / branch |
|---|---|---|---|
| OSA-001 | Live Router→Worker skill chaining | Xác minh dispatch thật, Worker tự nạp source/reference, TIP/AC đủ, verifier dùng đúng; native WS→task trace, cleanup/restore. Cần Tin Tin duyệt model/caps trước paid run. | Chưa nhận |
| OSA-002 | Docker Computer E2E trên máy có Docker | App build + desktop/VNC/CDP, parallel windows, takeover re-observe, file upload/lifecycle; API 200 không đủ. Không reuse credential/session khác. | Chưa nhận |
| OSA-003 | Code-split bundle frontend | Baseline + đo trước/sau, lazy route/component phù hợp, build/tests + browser regression; giữ VI/EN/ZH. Chốt target với owner, không bịa ngưỡng đã duyệt. | Chưa nhận |
| OSA-004 | Kiểm release mới kadaliao | Read-only release/tag/diff sau v0.6.0, bảng delta/VI/security risks; chỉ port forward commits trên remake khi được giao. Không PR upstream. | Done · grok-bot / `grok-bot/port-upstream-v0.6.1` · xem mục Done |
| OSA-005 | Rà/hardening GitHub Actions | CI đã có backend/frontend/Docker. Kiểm check-runs, trigger push i18n-vi, reporting sandbox skips và skill hashes; đề xuất gap rồi chốt thay đổi, không “tạo CI lần đầu”. | Chưa nhận |
| OSA-007 | Rendered onboarding/responsive QA | Fresh isolated data, VI/EN/ZH persistence, empty states, navigation/keyboard, 375/768/1440, ảnh/evidence đã làm sạch. Không khai PASS bằng build. | Chưa nhận |
| OSA-008 | Reconcile crash/drift review | Fault injection temp data cho FS/SQLite boundary, preserved edits/deletions; đề xuất recovery không mất dữ liệu, không auto-force reinstall. | Chưa nhận |

## In progress

| ID | Owner / branch | Trạng thái / bước tiếp |
|---|---|---|
| OSA-009 | grok-bot / `grok-bot/osa-009-audit-fixes` | `OSA-009 / grok-bot / grok-bot/osa-009-audit-fixes / deep fix audit Zro B01–B07 / claimed_at 07/11/2026 15:00 Asia/Saigon / PR link pending`. Chưa merge. |

## Done · đã public

- PR #1: v0.6.0 + VI port; PR #2: locale fallback/VI HTML; PR #3: routine labels.
- PR #4: AI Native mentor/paging/verifiers + eval v1–v3; PR #5: full source bundle + safe shared defaults.
- OSA-H01: [PR #6](https://github.com/VagabondKingsman/open-super-agent-remake/pull/6) đã merge vào `i18n-vi` lúc 08:26:01 07/11/2026 Asia/Saigon, SHA `3c08269`. CloudAgent đã `git am` trên base 2a36b59, tree khớp manifest, checks local PASS.
- OSA-006: `OSA-006 / grok-bot / grok-bot/contributing-bots / CONTRIBUTING remake, không đụng code hay CI / claimed_at 07/11/2026 12:11 Asia/Saigon / [PR #7](https://github.com/VagabondKingsman/open-super-agent-remake/pull/7)`. Tin Tin đã giao task và duyệt plan. Đã merge vào `i18n-vi` tại `5dc007b` (head `b90e4d5`) lúc 12:23:22 07/11/2026 Asia/Saigon. Author git của merge commit là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI backend, frontend, docker SUCCESS.
- OSA-004: `OSA-004 / grok-bot / grok-bot/port-upstream-v0.6.1 / port 0897360+ec71362+3432671 / claimed_at 07/11/2026 12:23 Asia/Saigon / [PR #8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8)`. Đã merge vào `i18n-vi` tại `6e5d3ffe3e42362059d83117264c3414ed5e1603` (head `5914b9d`) lúc 12:31:44 07/11/2026 Asia/Saigon. Author git của merge commit là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI backend, docker, frontend SUCCESS. Retest trên box: pytest 193 passed, 0 skipped. i18n thiếu/thừa 0. Web 15/15. Build OK. `verify-sources` PASS. Smoke: Host/Origin lạ 403, localhost 200.
- Link/SHA/giờ merge ở STATE. “Eval GO” không phải nghiệm thu Worker/Docker E2E.
