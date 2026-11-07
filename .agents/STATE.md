# Snapshot bàn giao · 07/11/2026

Mốc public đã xác minh: `origin/i18n-vi = 6e5d3ffe3e42362059d83117264c3414ed5e1603` (merge PR #8, 07/11/2026 12:31:44 Asia/Saigon). Mốc trước đó là `5dc007b` (merge PR #7, 12:23:22) và `3c08269` (merge PR #6, 08:26:01). Đây là **snapshot**, không phải latest vĩnh viễn. Phiên mới phải fetch/đọc ref và PR đang mở. Giờ trong file là **Asia/Saigon (UTC+7)**; ngày 07/11/2026 áp dụng cho bảng PR.

## Phiên bản và những gì đã merge

OSA v0.6.0 + VI/EN/ZH; AI Native manifest version 2. Bảy package team-authored + mentor cài shared mặc định. Không khẳng định branch main hiện cùng tip vì phiên này chỉ xác minh i18n-vi.

| PR | Merge lúc | SHA merge | Nội dung |
|---|---|---|---|
| [#1](https://github.com/VagabondKingsman/open-super-agent-remake/pull/1) | 00:38:33 | 129db18 | Port upstream v0.6.0, Vietnamese Chinese-as-key, giữ missing-Docker/routine hardening và docs/scripts. |
| [#2](https://github.com/VagabondKingsman/open-super-agent-remake/pull/2) | 00:52:43 | c6ec68b | Catalog locale thiếu/lỗi có fallback, HTML mặc định vi-VN, regression tests. |
| [#3](https://github.com/VagabondKingsman/open-super-agent-remake/pull/3) | 01:03:49 | afdea0e | Localize nhãn/goal task của routine theo ngôn ngữ UI; không rewrite lịch sử chat cũ. |
| [#4](https://github.com/VagabondKingsman/open-super-agent-remake/pull/4) | 03:34:28 | 7c20454 | Skill pack/mentor, paging dài, verify_facts, inspect_repo/check_patch và live-eval v1–v3. |
| [#5](https://github.com/VagabondKingsman/open-super-agent-remake/pull/5) | 07:51:47 | 2a36b59 | Bundle bảy nguồn + helpers, SHA-256, LICENSE/NOTICE và default shared install/reconcile/opt-out. |
| [#6](https://github.com/VagabondKingsman/open-super-agent-remake/pull/6) | 08:26:01 | 3c08269 | Handoff `.agents/`, Skill Flow, STATE/BOARD/log. `merged_at` API `2026-11-07T01:26:01Z`, đổi sang UTC+7. |
| [#7](https://github.com/VagabondKingsman/open-super-agent-remake/pull/7) | 12:23:22 | 5dc007b | CONTRIBUTING cho bot/remake (OSA-006). Head PR `b90e4d5`. `merged_at` API `2026-11-07T05:23:22Z`. Author git của merge commit là VagabondKingsman. Phiên ghi nhận Grok Bot merge với approval rõ của Tin Tin. CI backend, frontend, docker SUCCESS. |
| [#8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8) | 12:31:44 | 6e5d3ff | Port upstream `0897360`, `ec71362`, `3432671` (OSA-004). Head PR `5914b9d`. `merged_at` API `2026-11-07T05:31:44Z`. Author git của merge commit là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI backend, docker, frontend SUCCESS. |

Nguồn bảng: GitHub PR API `merged_at` chuyển UTC+7, đối chiếu git log. Không dùng commit author time làm merge time. Một số report lịch sử có timezone/giờ tiêu đề không nhất quán; ngày ADR dùng 07/11, trình tự merge lấy API, không sửa nguồn để giấu khác biệt.

## Bằng chứng nền đã có, không phải test lại trong mọi phiên

- Deep verify v0.6 trước pack: 101 pytest, 11 frontend; 15/17 AC PASS, 2 PARTIAL (Docker E2E, rendered browser walkthrough); status READY-with-deferred. Không cộng supplemental subset thành unique tests.
- Default-install report sau PR #4: 172 pytest, 15 frontend, build PASS; i18n backend 500/frontend 883 EN/VI keys, 0 thiếu/thừa, 0 Chinese UI chưa wrap. 129 source hashes PASS; 385.609 bytes nguồn. Fresh temp startup 0→8 shared skills, restart không duplicate, bot mới thấy cùng ids; real local restart không thêm LLM usage.
- Kết quả **phiên handoff này** nằm ở [log phiên](log/2026-11-07-build-bot.md); không lấy report cũ làm kết quả chạy mới. Các private raw reports không cần cho onboarding; tóm tắt công khai nằm ở đây và `docs/vi/`.

## Live skill eval: kết luận đúng phạm vi

| Đợt | Model / runs / calls | Kết quả | USD ước tính |
|---|---|---|---|
| v1 | grok-4.6; 16 runs / 68 calls | latest-mixed 216/240, routing 8/8; NO-GO vì tự báo sai Rubric/blog, artifact chưa đủ gate. | 0,700516 |
| v2 | grok-4.7; 10 runs / 60 calls (8 full + E02/E04 rerun) | latest-mixed 222/240; arithmetic tốt hơn nhưng patch chưa apply vào fixture nguyên trạng, scope blog 186/206 mơ hồ; NO-GO. | 1,138054 |
| v3 | grok-4.7; chỉ E02/E07, 2 runs / 19 calls | E02 exact patch check/apply/tests PASS (10 tests); E07 final 172 từ markdown_body. Hai AC mục tiêu PASS, GO cho handoff/PR review. | 0,359648 |

Tổng ba đợt **2,198218 USD** ước tính theo pricing metadata, không phải hóa đơn xAI. Latest-mixed thay hai bài v3 vào v2 là 228/240, không phải full eight-task v3. Không A/B model cô lập, không chứng minh ngang Build Bot. Chấm executor, mẫu nhỏ; v3 prose vẫn có giả định chưa có nguồn, cần biên tập trước publish.

E08 v2 đọc đủ resource 9.051 ký tự, offsets 0/5500 tới EOF, suffix khớp; đây là skill-resource paging, không phải mọi PDF/document stack. Tất cả live completions các đợt là **Router**, chưa Worker live. Normal role settings được khôi phục grok-4.6 sau eval theo báo cáo; bot mới không được giả định host khác dùng cùng model. Không paid call trong default-install/handoff.

Nguồn chi tiết: `docs/vi/ai-native-live-eval.md`, `ai-native-default-install.md`, `ai-native-verification.md`, `local-patch-checks.md`, `deterministic-verification.md` (đều dưới `docs/vi/`).

## Local-only và giới hạn

- Nhánh local cũ được giữ ở `safety/i18n-vi-before-shared-handoff-20261107`, tip `abe6207`. Trước sync tree bằng public 2a36b59 (diff rỗng), không copy lại commit cũ chỉ vì SHA khác. Local i18n-vi đã ở public tip, handoff làm trên `build-bot/shared-handoff`.
- Công bố trên remake: [PR #6](https://github.com/VagabondKingsman/open-super-agent-remake/pull/6) đã merge vào `i18n-vi` lúc 08:26:01 Asia/Saigon, merge commit `3c08269da64dc26941e064267221c7af28af1dca`. Branch `build-bot/shared-handoff`, base `2a36b59ca9d6236cd60935d71a2da8fcb690d8d1`. Commit patch `a682ad9a4426aa3aa1ffd1824d0b304789b19225`, tree `0904f3de3c8ac455478b03d746fd352fe583c7f8` khớp manifest. Không force-push và không đụng upstream kadaliao.
- CloudAgent, 07/11/2026 08:25 Asia/Saigon (UTC+7): `osa.i18n` PASS (EN/VI backend 500, frontend 883, thiếu/thừa 0, Chinese UI chưa wrap 0); `pytest -q` 172 passed, 0 skipped với bubblewrap 0.9.0 (3 SKIP ở `tests/test_local_checks.py` nếu không có bwrap); frontend `npm test` 15 passed, 0 skipped; `npm run build` PASS, JS 1.153,85 kB / gzip 374,59 kB, warning >500 kB còn; `verify-sources` 129 PASS. Không commit package-lock. CI remote của PR #6 là bằng chứng chính.
- DB/config/vault/browser sessions/operator fixture registry/backup/full eval traces chỉ nằm trên máy vận hành; không đưa lên GitHub. Tài khoản/máy mới phải tự thiết lập và được cấp quyền, không kế thừa credential của Build Bot.
- **Worker live** / Router→Worker skill chain chưa nghiệm thu với paid model; FakeLLM wiring không thay bằng chứng đó.
- Docker/Computer: Build Bot box thiếu Docker; chỉ graceful unavailable đã kiểm. App image build và desktop/VNC/CDP/parallel/takeover/upload E2E trên box đó NOT_CHECKED. CI file có Docker job nhưng chưa đọc remote check-runs trong phiên này.
- Bubblewrap: có sandbox tests đã PASS trong v3; host/kernel khác có thể SKIP. Phải báo skip count/reason, không mở host-shell fallback.
- Frontend: warning chunk JS khoảng 1,15 MB (>500 kB), chưa code-split. Không gọi warning là build failure; rendered onboarding/responsive/browser QA trong đợt deep verify cũ chưa hoàn tất.
- Tunnel: brief bàn giao nêu tunnel bị chặn trên Build Bot box; chưa tìm thấy bằng chứng tái kiểm công khai trong các report đã đọc. Ghi nhận môi trường, không kết luận hạn chế mọi máy, không cam kết remote URL hay công bố session link.
- Chat/task cũ tiếng Trung không tự được dịch/rewrite. App/template VI còn fallback EN; prompt nội bộ vẫn phần lớn source upstream kèm answer-language hint. Checker sạch không đồng nghĩa mọi nội dung là VI.
- Hash integrity không phải chữ ký nguồn hoặc chứng nhận helper an toàn. Default reconcile không atomic xuyên FS+SQLite khi crash; xem drift thủ công. Instruction verifier chưa là hard gate mọi câu trả lời model.
- `UpdateSkill` không có trong catalog phiên này; mới có tài liệu import, không có claim cài skill vào Grok Bot khác. Không suy capability của tài khoản khác.

## Bước tiếp theo

OSA-006 đã Done. [PR #7](https://github.com/VagabondKingsman/open-super-agent-remake/pull/7) merge vào `i18n-vi` tại `5dc007b`, head `b90e4d5`, 12:23:22 Asia/Saigon. Kết quả lệnh của phiên đó nằm ở [log OSA-006](log/2026-11-07-grok-bot.md). Log đó ghi 169 passed và 3 skipped vì máy đó thiếu `bwrap`. 169 + 3 = 172 test đã collect trên base `3c08269`. SKIP không phải PASS. Không lấy số đó làm kết quả của PR #8.

Việc khác trên BOARD vẫn chờ owner: Worker live cần approval budget, Docker/browser QA cần máy phù hợp. Không chạy paid API, tunnel hay channel thật chỉ vì mục đó nằm trong backlog.

## Bổ sung · port v0.6.1 · grok-bot · 07/11/2026

Append, không sửa snapshot phía trên. 12:23 Asia/Saigon (UTC+7). Branch `grok-bot/port-upstream-v0.6.1` từ `3c08269`. Port thủ công `0897360`, `ec71362`, `3432671` trong commit `8fd4327b4581a5adc3b5e026dd7e22bfdf718fa7`. Version làm việc 0.6.1. Không gồm desktop/Tauri/`v0.7.0-preview`. Upstream chỉ fetch, push URL `DISABLED`. Chi tiết và bằng chứng trong [log phiên](log/2026-11-07-grok-bot-port.md). PR: [#8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8). Chưa merge. Sau PR #7, nhánh này merge `origin/i18n-vi` (`5dc007b`) bằng merge commit, không rebase.

## Bổ sung · OSA-004 Done · 12:31 Asia/Saigon

[PR #8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8) đã merge vào `i18n-vi` tại `6e5d3ffe3e42362059d83117264c3414ed5e1603`. Head của PR là `5914b9d8e2ac1108539c01c6388ae5f19f446d79`. `merged_at` `2026-11-07T05:31:44Z` (12:31:44 Asia/Saigon). Author git của merge commit là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI backend, docker, frontend SUCCESS trên head đó. Đoạn “Chưa merge” ở mục port phía trên là trạng thái lúc viết, không xóa.

Retest trên box, ghi cùng lúc merge: `pytest` 193 passed, 0 skipped. `osa.i18n` thiếu/thừa 0. Web 15/15. Build OK. `verify-sources` PASS. Smoke runtime: Host/Origin lạ trả 403, localhost trả 200. Commit SHA upstream đã port cuối cùng là `3432671`. `docs/cap-nhat-tu-upstream.md` đã ghi SHA này, không sửa thêm trong phiên đánh Done.

## Bổ sung · OSA-009 đang làm · grok-bot · 07/11/2026

Append. Base phiên này là `origin/i18n-vi` = `d7f2ee91e4f527a2372a7ae9a0f3cbddb2a477b4` (merge PR #9). Branch `grok-bot/osa-009-audit-fixes`. Commit sửa code `93bcc00887c401452319573bd2b9d7fe2f36d6a4`. PR: [#10](https://github.com/VagabondKingsman/open-super-agent-remake/pull/10) vào `i18n-vi`. Tin Tin duyệt tạo task và sửa B01–B07 từ audit runtime. Chưa merge. Số test của phiên nằm ở [log OSA-009](log/2026-11-07-grok-bot-osa-009.md). 193 passed của box OSA-004 là số của máy có bubblewrap trên base cũ, không phải số của PR này. Live provider rerun là NOT_CHECKED, owner chạy sau trên máy của họ.

Verify độc lập trên head `c9480ef` kết luận HOLD. R1: heavy worker dùng chung lịch sử lặp. R2: batch bị cắt thiếu tool result. R3: hủy khi chỉ có tool-call delta thì không ghi usage. Đã sửa trên cùng branch, chưa merge. Câu model lẫn tiếng Bồ Đào Nha và `方案` được ghi là hành vi model, không viết lại output. Số gate của vòng sửa nằm ở log OSA-009.
