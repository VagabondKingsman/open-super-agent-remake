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
| OSA-015 | P0. `memory.db` tuyệt đối bỏ qua `OSA_DATA_DIR` | DB của process nằm trong data dir, hoặc khởi động từ chối và nói rõ. Sửa `tests/test_data_dir.py::test_absolute_db_path_still_wins`. Backup fd đang mở trước khi đổi. Box chạy `c16e6bb` mở `/workspace/osa-run/osa.db`. Thư mục `/workspace/osa-run/data` không có. | Chưa nhận |
| OSA-020 | P1. Dọn config Experiential trên box sang USD | File operator, không commit. `pricing.currency` là `$`. Bảng tay là số USD hoặc bỏ. Restart không chia `llm_usage` lần hai vì cờ đã USD. File hiện còn ¥, `usd_rate` 7.1, bảng tay CNY. Code đang chia lúc đọc. | Chưa nhận |
| OSA-019 | P1. Phần ngôn ngữ OSA-011 còn lại | Persona tiếng Việt cho template. Mô tả tool MCP do server trả. Validator đầu ra sai ngôn ngữ. Giữ `[附件]`, `需要你做的事`, regex `无新内容`. Không dịch nội dung user. UI `zh` giữ nguồn Trung. | Chưa nhận |
| OSA-016 | P1. Live routine | Một lịch trên data được phép. Quiet không gửi channel. Có lệnh và kết quả. Hiện `NOT_CHECKED`. | Chưa nhận |
| OSA-001 | P2. Live Router→Worker skill chaining | Xác minh dispatch thật, Worker tự nạp source/reference, TIP/AC đủ, verifier dùng đúng. Trace WS tới task, cleanup/restore. Cần Tin Tin duyệt model và cap trước lượt trả phí. | Chưa nhận |
| OSA-002 | P2. Docker Computer E2E trên máy có Docker | App build, desktop/VNC/CDP, cửa sổ song song, takeover, upload. HTTP 200 không đủ. Không dùng credential của máy khác. | Chưa nhận |
| OSA-017 | P1. Chạy ổn ngoài box Grok Bot | Docker trên máy Tin Tin hoặc VPS. Hết phụ thuộc watchdog và mạng box cắt Tailscale. Chọn máy với Tin Tin trước. | Chưa nhận |
| OSA-018 | P2. Mẫu A/B Zro và DeepSeek còn lại | Bài, cap, điều kiện dừng được duyệt cho đúng đợt. Không tự chạy. | Chưa nhận |
| OSA-003 | P2. Code-split bundle frontend | Đo trước sau, lazy route phù hợp, build và test, giữ VI/EN/ZH. Cảnh báo chunk >500 kB còn, JS khoảng 1,15 MB. Chốt ngưỡng với Tin Tin. | Chưa nhận |
| OSA-004 | Kiểm release mới kadaliao | Read-only release/tag/diff sau v0.6.0. Chỉ port lên remake khi được giao. Không PR upstream. | Done · grok-bot / `grok-bot/port-upstream-v0.6.1` · xem mục Done |
| OSA-005 | P2. Rà GitHub Actions | CI đã có backend, frontend, Docker. Đề xuất lỗ hổng rồi mới sửa. Không coi là tạo CI lần đầu. | Chưa nhận |
| OSA-007 | P1. UI sau login và responsive | Data tách, VI/EN/ZH còn sau reload, empty state, 375/768/1440. Ảnh đã xóa dữ liệu riêng. Khoảng 390px sau login trên điện thoại của Tin Tin là `NOT_CHECKED`: bot không vào tailnet sau mật khẩu. Build xanh không phải PASS. | Chưa nhận |
| OSA-008 | P2. Reconcile crash giữa file và SQLite | Bơm lỗi trên data tạm. Giữ sửa tay và tombstone. Không tự cài lại. | Chưa nhận |

## In progress

- OSA-014: `OSA-014 / grok-bot / grok-bot/osa-014-handoff / bàn giao .agents để bot mới đọc một thư mục là tiếp tục được / claimed_at 07/11/2026 20:48 Asia/Saigon / [PR #16](https://github.com/VagabondKingsman/open-super-agent-remake/pull/16)`. Tách từ `i18n-vi` tại `c16e6bb`. Chưa merge. Không paid LLM. Không đụng upstream kadaliao.

## Done · đã public

- OSA-013: `OSA-013 / grok-bot / grok-bot/osa-013-cost-usd / chi phí và đơn giá chuyển sang USD / claimed_at 07/11/2026 19:09 Asia/Saigon / [PR #15](https://github.com/VagabondKingsman/open-super-agent-remake/pull/15)`. Đã merge vào `i18n-vi` tại `c16e6bb0e42de25ddd0ac12f58e179bbd23f1ed3` (head `87980892e3a6141035516ee0b43d3d9136c1b3f5`) lúc 20:47:09 07/11/2026 Asia/Saigon. `merged_at` API `2026-11-07T13:47:09Z`. `merged_by` là VagabondKingsman. Câu "Chưa merge" trong log OSA-013 là trạng thái lúc viết log đó. DB box đã chia một lần: 103 dòng, ¥0.18457 thành $0.02600, `divided_rows` 64, `repriced_models` 0. File config trên box vẫn để ¥. Việc dọn file là OSA-020. Docker Computer E2E và live provider của task này vẫn `NOT_CHECKED`.
- OSA-012: `OSA-012 / grok-bot / grok-bot/osa-012-sw-offline-vi / trang offline của service worker: tiếng Việt trước, tiếng Anh sau; Cache Storage osa-lang; manifest vi-VN / claimed_at 07/11/2026 18:45 Asia/Saigon / [PR #14](https://github.com/VagabondKingsman/open-super-agent-remake/pull/14)`. Đã merge vào `i18n-vi` tại `653f8666414139228a3a6810c8832e71faad3bb2` (head `ee6089316a90c7d8fa371a4673eba40219b0c288`) lúc 19:08:18 07/11/2026 Asia/Saigon. `merged_at` API `2026-11-07T12:08:18Z`. Author git của merge commit là VagabondKingsman. Câu "Chưa merge" trong log OSA-012 là trạng thái lúc viết log đó.
- OSA-011: `OSA-011 / grok-bot / grok-bot/osa-011-en-prompts / prompt gửi model sang tiếng Anh, chỉ thị ngôn ngữ trả lời theo i18n.lang(), bỏ in_lang zh cố định, nhãn Heavy Draft / claimed_at 07/11/2026 18:04 Asia/Saigon / [PR #13](https://github.com/VagabondKingsman/open-super-agent-remake/pull/13)`. Đã merge vào `i18n-vi` tại `fcc2d893a3070818bbe251e3b6917f7c7abb54c8` (head `f83e3cb486b82a036d54303c6cba437840f49f18`) lúc 18:25:37 07/11/2026 Asia/Saigon. `merged_at` API `2026-11-07T11:25:37Z`. `merged_by` trên API là VagabondKingsman. Author git của merge commit là VagabondKingsman.
- OSA-010: `OSA-010 / grok-bot (Kingfisher) / grok-bot/osa-010-heavy-fixes / một lượt tối đa một Heavy, quorum draft, status failed hoặc partial, dừng khi hết hạn mức / claimed_at 07/11/2026 17:12 Asia/Saigon / [PR #12](https://github.com/VagabondKingsman/open-super-agent-remake/pull/12)`. Đã merge vào `i18n-vi` tại `f471839260243a8ea8ddfdde4b34294b49b5db5a` (head `5c75acb3147da40f44e00d8a86c2d72a175bed45`) lúc 18:25:08 07/11/2026 Asia/Saigon. `merged_at` API `2026-11-07T11:25:08Z`. `merged_by` trên API là VagabondKingsman. Author git của merge commit là VagabondKingsman. Ngoài PR, chưa làm: hợp đồng marker/goal, trần số tool call theo task, so A/B model, đo ngôn ngữ.
- PR #1: v0.6.0 + VI port; PR #2: locale fallback/VI HTML; PR #3: routine labels.
- PR #4: AI Native mentor/paging/verifiers + eval v1–v3; PR #5: full source bundle + safe shared defaults.
- OSA-H01: [PR #6](https://github.com/VagabondKingsman/open-super-agent-remake/pull/6) đã merge vào `i18n-vi` lúc 08:26:01 07/11/2026 Asia/Saigon, SHA `3c08269`. CloudAgent đã `git am` trên base 2a36b59, tree khớp manifest, checks local PASS.
- OSA-006: `OSA-006 / grok-bot / grok-bot/contributing-bots / CONTRIBUTING remake, không đụng code hay CI / claimed_at 07/11/2026 12:11 Asia/Saigon / [PR #7](https://github.com/VagabondKingsman/open-super-agent-remake/pull/7)`. Tin Tin đã giao task và duyệt plan. Đã merge vào `i18n-vi` tại `5dc007b` (head `b90e4d5`) lúc 12:23:22 07/11/2026 Asia/Saigon. Author git của merge commit là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI backend, frontend, docker SUCCESS.
- OSA-004: `OSA-004 / grok-bot / grok-bot/port-upstream-v0.6.1 / port 0897360+ec71362+3432671 / claimed_at 07/11/2026 12:23 Asia/Saigon / [PR #8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8)`. Đã merge vào `i18n-vi` tại `6e5d3ffe3e42362059d83117264c3414ed5e1603` (head `5914b9d`) lúc 12:31:44 07/11/2026 Asia/Saigon. Author git của merge commit là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI backend, docker, frontend SUCCESS. Retest trên box: pytest 193 passed, 0 skipped. i18n thiếu/thừa 0. Web 15/15. Build OK. `verify-sources` PASS. Smoke: Host/Origin lạ 403, localhost 200.
- OSA-009: `OSA-009 / grok-bot / grok-bot/osa-009-audit-fixes / deep fix audit Zro B01–B07 / claimed_at 07/11/2026 15:00 Asia/Saigon / [PR #10](https://github.com/VagabondKingsman/open-super-agent-remake/pull/10)`. Đã merge vào `i18n-vi` tại `7b73abbd0255b2df02a5d543c42007607870aedd` (head `255246f87ef3cc5a4ad4ad4f6c28b8ce9567a454`) lúc 15:51:53 07/11/2026 Asia/Saigon. `merged_at` API `2026-11-07T08:51:53Z`. Author git của merge commit là VagabondKingsman. `merged_by` trên API là VagabondKingsman. Grok Bot merge với approval rõ của Tin Tin. CI backend, frontend, docker SUCCESS trên head đó. Box live trên Zro: B01, B03, B05, B06 PASS. R1–R3 PASS trên contract đã sửa (R1 controlled live và deterministic; R2 deterministic; R3 deterministic). B04 PARTIAL: model trộn ngôn ngữ (tiếng Bồ Đào Nha, `方案`). B07 PARTIAL: usage của request đang chạy lúc SIGKILL không khôi phục được. long12, natural heavy và marker single task vẫn FAIL, ghi ở OSA-010. Chạy dài vẫn mở.
- Link/SHA/giờ merge ở STATE. “Eval GO” không phải nghiệm thu Worker/Docker E2E.
