# <type>: <tóm tắt>

## Mục tiêu / task / thay đổi

- BOARD ID, owner bot, branch `<bot>/<topic>`, base `i18n-vi`, base/head SHA.
- REQ/TIP/AC và lý do; source evidence đã mở, không suy đoán root cause như fact.
- File/behavior đổi, reusable components, out-of-scope và deviations.

## Verify

Liên kết VERIFY REPORT hoặc điền đủ coverage, scenarios, technical health, Retro R1–R5 và overall status theo `VERIFY-REPORT.md`.

- [ ] i18n checker, pytest, frontend test/build phù hợp phạm vi; ghi counts/exits/skips, không tick khi chưa chạy.
- [ ] VI default + EN/ZH + placeholders/migration giữ đúng.
- [ ] Không secrets/PII/session links/private traces/DB; diff --check + scan/review.
- [ ] Temp data/fake LLM, không real channel sends; paid run chỉ với approval/cap riêng và restore.
- [ ] STATE + BOARD + log phiên cập nhật; task claim không trùng owner.
- [ ] Thay đổi user-visible đã cân nhắc CHANGELOG; tuân thủ docs/architecture.md.
- [ ] App/template đổi: catalog/template validation và mức smoke đã chạy ghi rõ; không bắt buộc routine/channel thật khi chưa duyệt.

## Rủi ro / deferred / rollback

<Ghi Docker/bubblewrap/browser gaps, warning cũ, regression và safety/backup cần thiết. Rollback không force-push/không ghi đè dữ liệu.>

## Quyền phát hành

<Approval cho tạo PR/push này nếu có; không tự suy quyền merge. Merge: Tin Tin hoặc bot được duyệt rõ. Không PR upstream.>
