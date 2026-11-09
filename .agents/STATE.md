# Snapshot bàn giao · 07/11/2026

Mốc public đã xác minh lúc soạn OSA-014: `origin/i18n-vi = c16e6bb0e42de25ddd0ac12f58e179bbd23f1ed3` (merge PR #15). `merged_at` API `2026-11-07T13:47:09Z`, tức 20:47:09 Asia/Saigon. `merged_by` là VagabondKingsman. Đây là **snapshot**. Phiên mới fetch lại ref và PR đang mở. Giờ trong file là **Asia/Saigon (UTC+7)**. File đọc đầu cho bot mới: [HANDOFF](HANDOFF.md).

Bảng dưới đối chiếu GitHub API `merged_at` và `git rev-parse origin/i18n-vi` trong phiên OSA-014. Không dùng giờ commit làm giờ merge. `merged_by` của cả 15 PR là VagabondKingsman. Các mục "Bổ sung" phía dưới giữ nguyên lời lúc viết. Câu "Chưa merge" trong mục đó là trạng thái lúc viết mục. Bảng này mới hơn.

## Phiên bản và những gì đã merge

OSA v0.6.1 + VI/EN/ZH. Prompt gửi model là tiếng Anh, câu trả lời theo `i18n.lang()`. Chi phí lưu và hiện bằng USD. AI Native manifest version 2. Bảy package team-authored + mentor cài shared mặc định. Không khẳng định `main` cùng tip vì phiên này xác minh `i18n-vi`.

| PR | Merge lúc | SHA merge | Nội dung |
|---|---|---|---|
| [#1](https://github.com/VagabondKingsman/open-super-agent-remake/pull/1) | 00:38:33 | 129db18 | Port upstream v0.6.0, Vietnamese Chinese-as-key, giữ missing-Docker/routine hardening và docs/scripts. |
| [#2](https://github.com/VagabondKingsman/open-super-agent-remake/pull/2) | 00:52:43 | c6ec68b | Catalog locale thiếu/lỗi có fallback, HTML mặc định vi-VN, regression tests. |
| [#3](https://github.com/VagabondKingsman/open-super-agent-remake/pull/3) | 01:03:49 | afdea0e | Localize nhãn/goal task của routine theo ngôn ngữ UI. Không rewrite lịch sử chat cũ. |
| [#4](https://github.com/VagabondKingsman/open-super-agent-remake/pull/4) | 03:34:28 | 7c20454 | Skill pack/mentor, paging dài, verify_facts, inspect_repo/check_patch và live-eval v1–v3. |
| [#5](https://github.com/VagabondKingsman/open-super-agent-remake/pull/5) | 07:51:47 | 2a36b59 | Bundle bảy nguồn + helpers, SHA-256, LICENSE/NOTICE và default shared install/reconcile/opt-out. |
| [#6](https://github.com/VagabondKingsman/open-super-agent-remake/pull/6) | 08:26:01 | 3c08269 | Handoff `.agents/`, Skill Flow, STATE/BOARD/log. `merged_at` API `2026-11-07T01:26:01Z`. |
| [#7](https://github.com/VagabondKingsman/open-super-agent-remake/pull/7) | 12:23:22 | 5dc007b | CONTRIBUTING cho bot/remake (OSA-006). Head PR `b90e4d5`. `merged_at` API `2026-11-07T05:23:22Z`. |
| [#8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8) | 12:31:44 | 6e5d3ff | Port upstream `0897360`, `ec71362`, `3432671` (OSA-004). Head PR `5914b9d`. `merged_at` API `2026-11-07T05:31:44Z`. |
| [#9](https://github.com/VagabondKingsman/open-super-agent-remake/pull/9) | 12:37:13 | d7f2ee9 | Docs đánh dấu OSA-004 xong sau PR #8. `merged_at` API `2026-11-07T05:37:13Z`. |
| [#10](https://github.com/VagabondKingsman/open-super-agent-remake/pull/10) | 15:51:53 | 7b73abb | OSA-009 sửa audit B01–B07. Head `255246f`. `merged_at` API `2026-11-07T08:51:53Z`. |
| [#11](https://github.com/VagabondKingsman/open-super-agent-remake/pull/11) | 15:59:20 | d2938f4 | Docs OSA-009 xong, mở OSA-010. `merged_at` API `2026-11-07T08:59:20Z`. |
| [#12](https://github.com/VagabondKingsman/open-super-agent-remake/pull/12) | 18:25:08 | f471839 | OSA-010 một Heavy mỗi lượt, quorum draft, dừng khi hết hạn mức. Head `5c75acb`. `merged_at` API `2026-11-07T11:25:08Z`. |
| [#13](https://github.com/VagabondKingsman/open-super-agent-remake/pull/13) | 18:25:37 | fcc2d89 | OSA-011 prompt gửi model sang tiếng Anh. Head `f83e3cb`. `merged_at` API `2026-11-07T11:25:37Z`. |
| [#14](https://github.com/VagabondKingsman/open-super-agent-remake/pull/14) | 19:08:18 | 653f866 | OSA-012 trang offline tiếng Việt trước. Head `ee60893`. `merged_at` API `2026-11-07T12:08:18Z`. |
| [#15](https://github.com/VagabondKingsman/open-super-agent-remake/pull/15) | 20:47:09 | c16e6bb | OSA-013 chi phí và đơn giá sang USD. Head `8798089`. `merged_at` API `2026-11-07T13:47:09Z`. |

Nguồn bảng: GitHub PR API `merged_at` chuyển UTC+7, đối chiếu `git log` lúc OSA-014. PR #1 đến #5 có `merged_at` trong ngày 06/11 UTC, tức sáng 07/11 giờ Sài Gòn. Một số report cũ lệch timezone. Trình tự merge lấy API. Không sửa log cũ để giấu khác biệt.

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

## Bổ sung · OSA-009 Done · 15:54 Asia/Saigon

Thêm cuối file. Không sửa các mục phía trên. `origin/i18n-vi` xác minh lại bằng `git rev-parse` và `git fetch` là `7b73abbd0255b2df02a5d543c42007607870aedd`. Hai chỗ “Chưa merge” trong mục OSA-009 ở trên là trạng thái lúc viết mục đó.

[PR #10](https://github.com/VagabondKingsman/open-super-agent-remake/pull/10) đã merge vào `i18n-vi` tại `7b73abbd0255b2df02a5d543c42007607870aedd`. Head của PR là `255246f87ef3cc5a4ad4ad4f6c28b8ce9567a454`. Cha của merge commit là `d7f2ee91e4f527a2372a7ae9a0f3cbddb2a477b4` và head đó. `merged_at` API `2026-11-07T08:51:53Z`, tức 15:51:53 Asia/Saigon. Giờ commit ghi `2026-11-07T15:51:52+07:00`; không dùng giờ commit làm giờ merge. Author git của merge commit là VagabondKingsman. `merged_by` trên API là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI trên head `255246f`: backend, frontend, docker đều `completed` / `success`.

Box live trên Zro, VERIFY 15:48 Asia/Saigon, cùng head `255246f`:

- B01, B03, B05, B06 PASS.
- R1–R3 PASS trên contract đã sửa. R1 có controlled live và deterministic. R2 deterministic. R3 deterministic. Natural heavy không đủ ba tool call, nên guard cũ không chạy lại trong lượt đó. h0 không gọi tool. Goal của lượt đó FAIL.
- B04 PARTIAL. Chuỗi tool vẫn tiếng Việt. Model trộn tiếng Bồ Đào Nha và nhãn `方案`. VERIFY còn ghi long12 trả tiếng Anh và MCP đầu trả tiếng Ukraina. Không có validator ngôn ngữ đầu ra mới.
- B07 PARTIAL. Hủy giữa stream chữ và reasoning PASS: một dòng usage, `estimated=1`, output 53. Request đang chạy lúc SIGKILL có thể thiếu usage trong DB, không khôi phục được. Trường hợp hủy khi stream chỉ còn tool-call và chạy qua Zro thật là NOT_CHECKED. Bản R3 đã kiểm dùng stream tất định.
- Chưa phải GO cho chạy dài. long12 FAIL: 13 lần `verify_facts` cộng 1 tool lạ, tổng cuối 11, task #5 vẫn `done` sau 15 vòng model. Single task thiếu marker `PR10_SINGLE_DONE`. Các FAIL này thành OSA-010, owner chưa nhận.

Số liệu box lấy từ VERIFY đính kèm phiên docs, không chép artifact private lên git. Log phiên docs: [log](log/2026-11-07-grok-bot-osa-009-done.md). Phiên docs không gọi LLM trả phí và không sửa code runtime.

PR tài liệu của phiên này: [#11](https://github.com/VagabondKingsman/open-super-agent-remake/pull/11), branch `grok-bot/state-osa-009-done`, vào `i18n-vi`. Chưa merge.

## Bổ sung · OSA-010 đang làm · grok-bot · 07/11/2026

Append. Không sửa các mục phía trên. `origin/i18n-vi` lúc mở phiên là `d2938f4cb6a49555c933f4654f9c72c5ff2b5892` (merge PR #11). Câu “Chưa merge” của PR #11 ở đoạn trên là trạng thái lúc viết đoạn đó.

Branch `grok-bot/osa-010-heavy-fixes`. Tin Tin duyệt sửa bốn lỗi heavy từ live test Experiential (task #48–50, #61–63) và báo cáo A/B. Chưa merge. Không gọi LLM trả phí. Không đụng upstream kadaliao.

Nguyên nhân đã đối chiếu trên code ở base này:

- Router không nhớ Heavy đã giao trong cùng lượt, nên vài lần gọi tool `dispatch` tạo vài task.
- `run_heavy` bỏ exception của worker rồi vẫn gọi reviewer.
- `_run` ghi `done` khi heavy trả về chữ. Lỗi worker không thoát ra thành trạng thái task.
- Mọi worker heavy xuất phát cùng lúc. Lỗi 429 chỉ được viết thành câu, client còn retry sẵn. Không tách hết hạn mức khỏi rate limit.

Số test của phiên nằm ở [log OSA-010](log/2026-11-07-grok-bot-osa-010.md). Trên máy này `pytest` 223 passed, 3 skipped vì không có bubblewrap. 3 SKIP không phải PASS. Live provider sau bản sửa là NOT_CHECKED.

PR: [#12](https://github.com/VagabondKingsman/open-super-agent-remake/pull/12), branch `grok-bot/osa-010-heavy-fixes`, head `2671e11576654f8693d8abab249df62e1bddd202`, vào `i18n-vi`. Chưa merge.

## Bổ sung · OSA-011 đang làm · grok-bot · 07/11/2026

Append. Không sửa các mục phía trên. Branch làm việc `grok-bot/osa-011-en-prompts`, tách từ `grok-bot/osa-010-heavy-fixes` tại `5c75acb3147da40f44e00d8a86c2d72a175bed45`. PR: [#13](https://github.com/VagabondKingsman/open-super-agent-remake/pull/13), vào `i18n-vi`, xếp trên PR #12, merge sau #12. Commit code `b02c32d17eb88788b586c8c230a29f354f3faefb`. Chưa merge. Không gọi LLM trả phí. Không đụng upstream kadaliao.

Prompt gửi model (router, worker, reviewer, import trí nhớ, lọc routine, draft skill, mô tả tool) chuyển sang tiếng Anh. `i18n.model_hint()` luôn gắn chỉ thị trả lời theo `i18n.lang()` (mặc định vi) cho cả ba ngôn ngữ. `in_lang="zh"` không còn trong code prompt. Nhãn Heavy `方案` đổi thành `Draft`.

Số test của phiên nằm ở [log OSA-011](log/2026-11-07-grok-bot-osa-011.md). Trên máy này `pytest` 233 passed, 3 skipped vì không có bubblewrap. 3 SKIP không phải PASS. Live provider sau bản sửa là NOT_CHECKED.

## Bổ sung · OSA-012 đang làm · grok-bot · 07/11/2026

Append. Không sửa các mục phía trên. `origin/i18n-vi` lúc mở phiên là `fcc2d893a3070818bbe251e3b6917f7c7abb54c8` (merge PR #13). Câu “Chưa merge” của PR #13 ở đoạn trên là trạng thái lúc viết đoạn đó.

Đối chiếu API lúc mở OSA-012: [PR #12](https://github.com/VagabondKingsman/open-super-agent-remake/pull/12) đã merge tại `f471839260243a8ea8ddfdde4b34294b49b5db5a`, `merged_at` `2026-11-07T11:25:08Z` (18:25:08 Asia/Saigon), head `5c75acb3147da40f44e00d8a86c2d72a175bed45`. [PR #13](https://github.com/VagabondKingsman/open-super-agent-remake/pull/13) đã merge tại `fcc2d893a3070818bbe251e3b6917f7c7abb54c8`, `merged_at` `2026-11-07T11:25:37Z` (18:25:37 Asia/Saigon), head `f83e3cb486b82a036d54303c6cba437840f49f18`. `merged_by` cả hai là VagabondKingsman. Author git của hai merge commit là VagabondKingsman. Câu “Chưa merge” trong mục OSA-010 và OSA-011 phía trên là trạng thái lúc viết mục đó.

Branch `grok-bot/osa-012-sw-offline-vi`. [PR #14](https://github.com/VagabondKingsman/open-super-agent-remake/pull/14) vào `i18n-vi`. Head `59c2001cad4f9475c4c2078929c7d80374711e6b`. Trang offline của service worker hiện tiếng Việt trước, tiếng Anh sau. Ngôn ngữ đã lưu nằm trong Cache Storage `osa-lang` (khóa `/osa-lang`). Không có hoặc giá trị lạ thì tiếng Việt. Tiếng Trung chỉ khi ngôn ngữ UI là `zh`. `manifest.json` đổi `lang` sang `vi-VN` và đổi mô tả sang tiếng Việt. Chưa merge. Không gọi LLM trả phí. Không đụng upstream kadaliao.

Cookie không dùng được: Chrome không đưa header Cookie vào fetch của service worker. Đã đo trên Chrome headless trong phiên này. `navigator.language` không dùng, vì cài mới vẫn mặc định tiếng Việt.

Số test của phiên nằm ở [log OSA-012](log/2026-11-07-grok-bot-osa-012.md). Trên máy này `pytest` 233 passed, 3 skipped vì không có bubblewrap. 3 SKIP không phải PASS. Browser đã mở trang offline từ `sw.js` thật sau khi tắt server. Live provider là NOT_CHECKED. Docker Computer E2E trên máy này là NOT_CHECKED.

CI trên head `04d8832`, run `42370109157`: backend, frontend, docker đều success. 0 failed. Đối chiếu 18:55 Asia/Saigon. PR #14 vẫn chưa merge.

## Bổ sung · OSA-012 đã merge · OSA-013 đang làm · grok-bot · 07/11/2026

Append. Không sửa các mục phía trên. `origin/i18n-vi` lúc mở OSA-013 là `653f8666414139228a3a6810c8832e71faad3bb2` (merge PR #14). Câu “PR #14 vẫn chưa merge” ở đoạn trên là trạng thái lúc viết OSA-012.

[PR #14](https://github.com/VagabondKingsman/open-super-agent-remake/pull/14) đã merge vào `i18n-vi` tại `653f8666414139228a3a6810c8832e71faad3bb2`. Head của PR là `ee6089316a90c7d8fa371a4673eba40219b0c288`. `merged_at` API `2026-11-07T12:08:18Z`, tức 19:08:18 Asia/Saigon. Giờ commit ghi `2026-11-07 19:08:17 +0700`; không dùng giờ commit làm giờ merge. Author git của merge commit là VagabondKingsman.

Branch `grok-bot/osa-013-cost-usd`, tách từ `653f866`. [PR #15](https://github.com/VagabondKingsman/open-super-agent-remake/pull/15) vào `i18n-vi`. Head code `778446e7b2b2a0c65a4bb0d497c0d4630b174cbb`. Chi phí và đơn giá chuyển sang USD. models.dev không còn nhân 7.1. Bảng DeepSeek trong `config.yaml` đổi sang giá niêm yết USD (trang giá API, 07/11/2026). `llm_usage.cost` cũ đổi một lần, cờ `settings.cost_unit`. Tab giới hạn vẫn là token / bước / giây. Chưa merge. Không gọi LLM trả phí. Không đụng upstream kadaliao.

Số test của phiên nằm ở [log OSA-013](log/2026-11-07-grok-bot-osa-013.md).

## Bổ sung · OSA-013 đã merge · OSA-014 đang làm · grok-bot · 07/11/2026

Append. Không sửa các mục phía trên. `origin/i18n-vi` lúc mở OSA-014 là `c16e6bb0e42de25ddd0ac12f58e179bbd23f1ed3`. Câu "Chưa merge" của PR #15 ở đoạn trên là trạng thái lúc viết OSA-013.

[PR #15](https://github.com/VagabondKingsman/open-super-agent-remake/pull/15) đã merge vào `i18n-vi` tại `c16e6bb0e42de25ddd0ac12f58e179bbd23f1ed3`. Head của PR là `87980892e3a6141035516ee0b43d3d9136c1b3f5`. `merged_at` API `2026-11-07T13:47:09Z`, tức 20:47:09 Asia/Saigon. `merged_by` là VagabondKingsman. Lúc đối chiếu không có PR mở vào `i18n-vi`.

Deploy box của SHA này, Tin Tin báo, phiên docs không mở DB. Process giữ `/workspace/osa-run/osa.db`. Thư mục `/workspace/osa-run/data` không tồn tại. 103 dòng usage, tổng ¥0.18457 thành $0.02600. Cờ `cost_unit` có `currency` USD, `legacy_cny_per_usd` 7.1, `repriced_models` 0, `divided_rows` 64. File `config.experiential.yaml` trên box vẫn khai ¥. Chi tiết và cách backup fd nằm ở [OPS](OPS.md).

Branch `grok-bot/osa-014-handoff`. [PR #16](https://github.com/VagabondKingsman/open-super-agent-remake/pull/16) vào `i18n-vi`. Việc của branch là viết bàn giao trong `.agents/` để bot mới chỉ đọc thư mục đó là tiếp tục được. Chưa merge. Không gọi LLM trả phí. Không đụng upstream kadaliao. Log: [OSA-014](log/2026-11-07-grok-bot-osa-014.md).

## Bổ sung · live OSA-011 vào PR #16 · 07/11/2026

Append. Câu "Live provider sau bản sửa là NOT_CHECKED" trong mục OSA-011 phía trên là trạng thái lúc viết PR #13. Tin Tin đưa bằng chứng box vào PR #16.

Head lúc chạy: `f83e3cb486b82a036d54303c6cba437840f49f18`. Provider Experiential, model đuôi `:free`, cost ghi 0. Bốn lượt: vi 2,01 giây, en 2,01 giây, single task #75 done 29,19 giây, heavy task #79 done 124 giây. CJK 0 ở cả bốn. Đúng một heavy task, 3 góc nhìn và reviewer. Không có `方案`.

14 dòng usage, 116.236 token. Vượt mục tiêu khoảng 100.000 nên routine không chạy. Guard harness đếm sai cột token, phải sửa trước đợt sau. Websocket dừng vì regex 402 khớp offset 14025. Log server không có lỗi 402. `results.json` giữ heavy đang `running` tại 60,38 giây. Latency 124 giây lấy từ `summary.json` và báo cáo.

Bằng chứng: [LIVE-TEST](evidence/osa-011-live-test/LIVE-TEST.md), [summary](evidence/osa-011-live-test/summary.json), [results](evidence/osa-011-live-test/results.json), [live.py](evidence/osa-011-live-test/live.py), [finish.py](evidence/osa-011-live-test/finish.py). Không có thư mục `raw/`. Phiên này không gọi lại provider.

## Bổ sung · PR #16 đã merge · OSA-021 đang làm · hoplite · 09/11/2026

Append. Không sửa các mục phía trên. Câu "PR #16 chưa merge" ở trên là trạng thái lúc viết OSA-014.

[PR #16](https://github.com/VagabondKingsman/open-super-agent-remake/pull/16) đã merge vào `i18n-vi` tại `3b02a80f1b4b04e311c48f3283719f4798d7befd`. Head của PR là `c876608701a942b7a24d3d9857c0aed127c48493`. `merged_at` API `2026-11-07T14:14:45Z`, tức 21:14:45 Asia/Saigon. `merged_by` là VagabondKingsman.

OSA-021 port upstream `kadaliao/open-super-agent` v0.12.0 (`d432c74`) lên remake. Branch `hoplite/megara-e725a8f4`, [PR #17](https://github.com/VagabondKingsman/open-super-agent-remake/pull/17) vào `i18n-vi`, chưa merge. Cách làm: dựng nền v0.12.0 rồi port lại phần riêng của remake, giữ VI mặc định, prompt tiếng Anh, Heavy, chi phí USD, skill pack AI Native. `desktop/` và `mobile/` có trong cây, không có workflow build. Local: pytest 690 passed, 5 skipped. i18n backend 1175, frontend 1244, thiếu/thừa 0. Web 27/27, build OK. Docker build và smoke OK. Chi tiết và việc còn mở ở [log OSA-021](log/2026-11-09-hoplite-osa-021.md). Không gọi model trả phí trong phiên hoàn tất.

## Bổ sung · PR #17 đã merge · OSA-022 đang làm · hoplite · 09/11/2026

Append. Câu "PR #17 chưa merge" ở trên là trạng thái lúc viết OSA-021.

[PR #17](https://github.com/VagabondKingsman/open-super-agent-remake/pull/17) đã merge vào `i18n-vi` tại `d3a838ee1bcdcfac3962f84229fbd10f2e3728a8`, `merged_at` API `2026-11-09T07:25:33Z` (14:25:33 Asia/Saigon). Hoplite merge theo câu duyệt của Thi Vo. Bản trên `i18n-vi` giờ là OSA 0.12.0. Box vẫn chạy bản cũ cho tới khi deploy theo OPS.

OSA-022, branch `hoplite/osa-022-port-followups`, gồm: các việc còn mở sau port, OSA-015 (cảnh báo, không đổi DB), OSA-007 (sửa Quan sát ở 375px và hai bản dịch dính chữ), OSA-003 (entry JS 69 kB), OSA-008 (reconcile chịu crash), OSA-019 (template `vi:`, plugin theo ngôn ngữ UI, cờ `lang_flag`). Local: pytest 752 passed, 5 skipped. i18n thiếu/thừa 0. Web 27/27, build OK. Chi tiết ở [log OSA-022](log/2026-11-09-hoplite-osa-022.md). Không gọi model trả phí.
