# VERIFY REPORT · TIP-<ID>

- Date: <Asia/Saigon (UTC+7)>; base/head/branch/environment: <...>
- Scope và artifact cuối được kiểm: <path/SHA/hash>; không lấy nháp thay final.

## REQUIREMENT COVERAGE

<REQ hoàn thành/tổng REQ; AC PASS/tổng AC; tách assessed với passed; mẫu số rõ>

## SCENARIO RESULTS

| REQ/AC | Tier / priority | PASS/FAIL/PARTIAL/SKIP/NOT_CHECKED | Evidence / exit / giới hạn |
|---|---|---|---|
| REQ-1/AC-1 | Tier 1/P0 | NOT_CHECKED | <command + lý do chưa chạy> |

## TECHNICAL HEALTH

- Backend pytest: <passed/failed/skipped + reasons>; i18n: <keys/missing/extra>.
- Frontend tests/build/types: <counts/exits/warnings>; lint không cấu hình thì NOT_CHECKED.
- Isolation/security/secret scan: <scope và findings đã review, không in secret>.
- Runtime/paid API/channel: <đã chạy loại nào; không Router→Worker/Docker claim nhầm>.
- Log/artifact: <repo-relative public evidence; private raw traces không đính kèm>.

## RETRO RUBRIC SCORE

| Vòng | R1 | R2 | R3 | R4 | R5 | Tổng do tool tính | Gate/evidence |
|---|---|---|---|---|---|---|---|
| 1 | <0–2> | <0–2> | <0–2> | <0–2> | <0–2> | <...> | <>=9, không 0; script/tool hoặc NOT_CHECKED> |

RETRO-ID / root cause / executable guardrail / lần rerun: <...>. Không chạy script thì không tuyên bố ledger gate PASS. Tối đa ba vòng rồi escalate.

## OVERALL STATUS

READY / READY-with-deferred / NOT READY, kèm blocking AC/deferred và next owner. Tier 1 fail không READY. “READY” là kết quả kỹ thuật, không approval push/merge/deploy. Ghi chi phí ước tính/stop/restore nếu có live run.
