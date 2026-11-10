# Bộ eval offline cho agent (P0+ #5) · 10/11/2026

Giờ theo Asia/Saigon (UTC+7).

- Yêu cầu (t86u): làm P0+ #5, bộ eval CI 20–30 task, PR vào `i18n-vi`. Trace/replay (#3) là việc kế tiếp.
- Base: `origin/i18n-vi` = `2bb18f4`. Worktree `/workspace/osar-eval`, nhánh `feat/eval-suite`. Không đụng `/workspace/open-super-agent` và bot đang chạy (pid 523005).
- Skill Flow: osa-dev, ai-work-method, vibecode-kit, unslop-vi cho tài liệu.

## Làm gì

| Phần | Chỗ |
|---|---|
| Engine chạy kịch bản: dựng Bot, group, tool app giả, vault, Computer giả, routine, repo fixture; điều khiển (duyệt, từ chối, hủy, nói thêm); chấm; chặn socket ra ngoài 127.0.0.1 | `tests/evals/engine.py` |
| 27 kịch bản YAML, 6 kịch bản safety, 1 xfail | `tests/evals/scenarios/` |
| Test pytest marker `eval`, hai bite test cho engine (kỳ vọng sai phải FAIL, mạng thật bị chặn) | `tests/test_evals.py` |
| `Stall`: stream ra một chunk rồi treo | `tests/fakellm.py` |
| Runner: JSON, markdown, so baseline, `--update-baseline` | `scripts/run_evals.py` |
| Cổng so baseline | `scripts/eval_gate.py`, `tests/test_eval_gate.py` |
| Baseline | `tests/evals/baseline.json` |
| CI: bước eval sau Tests, artifact `eval-scorecard` | `.github/workflows/ci.yml` |
| Tài liệu | `docs/vi/eval.md`, `CONTRIBUTING.md` |

Kịch bản dùng đường thật của OSAR: `check_patch` trong `bwrap`, thẻ của `approvals`, `routines.tick`, `POST /hooks/<key>`, `watchdog`, `guard_stream`. Model là `FakeLLM` qua `AsyncOpenAI` thật.

## Bản của SuperGrok Craft

`/workspace/osra-cassette-eval.patch` (commit `4783db6`). Đã đọc như code không tin cậy: chỉ thư viện chuẩn, không mạng, không subprocess, chỉ ghi file khi có `--json`. File patch khớp commit.

- Lấy `scripts/eval_gate.py` và `tests/test_eval_gate.py`, sửa:
  - kịch bản baseline PASS mà nay FAIL thì chặn (bản gốc chỉ liệt kê; một kịch bản hỏng và một kịch bản được sửa cùng lúc thì lọt);
  - thêm `expected_fail` cho lỗ đã biết: safety xfail có trong baseline không chặn, nhưng gắn xfail cho kịch bản đang PASS thì chặn;
  - steps/token/cost/latency chỉ cảnh báo, ngưỡng 20%, thêm cảnh báo theo từng kịch bản. Bản gốc chặn khi tăng 30%, sẽ chặn PR chỉ vì prompt dài hơn.
- Không lấy `osa/cassette.py`, `tests/test_cassette.py`, `docs/design/cassette-eval.md`: thuộc #3 trace/replay, bộ eval không cần.

## Review PR #44 (SuperGrok Craft)

Thêm một commit:

- CI so với baseline của nhánh đích: `git fetch` nhánh đích, `run_evals.py --base-ref`. Nhánh đích chưa có baseline thì dùng baseline của PR kèm thông báo bootstrap; push không có nhánh đích thì dùng baseline đã commit; không có ref thì exit 2. Kiểm `expected_fail` lén gắn cũng so với baseline nhánh đích. Test: `tests/test_run_evals.py` trên repo git tạm.
- Số bước tăng quá 30% (trung bình và từng kịch bản) lại FAIL; 20–30% cảnh báo; token/cost/latency chỉ cảnh báo ở 20%.
- Bite: thêm hai lượt gọi tool vào `e08` (kịch bản vẫn PASS, 2 → 4 bước) thì cổng FAIL `e08_mcp_read_tool: steps +100% (2 → 4)`, exit 1.

## Cổng kiểm

- `OSA_REQUIRE_SANDBOX=1 xvfb-run -a uv run pytest -q -rs`: 891 passed, 1 skipped (`test_real_desktop`, cần macOS), 1 xfailed (`e27`). Trước đó 853 passed, 1 skipped.
- `scripts/run_evals.py`: 26/27 PASS, 1 xfail, 0 skip. Phần eval chạy khoảng 4 giây. Ba lượt liền nhau cho cùng outcome, số bước, số lần gọi model và token.
- Bite: đổi kỳ vọng `e08` thành chuỗi không có thì runner exit 1, cổng báo `scenarios that passed in baseline now fail: e08_mcp_read_tool`.
- `python -m osa.i18n`: en/vi thiếu 0, thừa 0. Không thêm câu hiển thị mới trong `osa/`.
- `compileall osa` OK. Không sửa `web/`.

## Tìm thấy khi viết

- `e27` xác nhận lỗ P0-2 bằng test: bot khác, trong lượt do bot đánh thức, gọi `resolve_approval` và tool chạy.
- `router.TASKS` dùng id tin nhắn làm khóa, id bị dùng lại sau khi xóa Bot (BOARD `OPEN-TASK-ID`).
- `routines.tick` duyệt mọi routine trong DB; engine giới hạn về routine của kịch bản để routine của test khác không chạy chen.

## Điểm móc cho trace/replay (#3)

- `providers.create_chat`: mọi lượt gọi model đi qua đây, có đủ `messages`, `tools`, `model`.
- `memory.record_usage`, `record_error`, `record_partial`: một hàng `llm_calls` mỗi lượt, có Bot, chat, task qua `memory.WHO`.
- `tasklog.Log.start` và `finish`: bước tool có `detail` (tham số) và `body` (kết quả).
- `registry.fire("tool_done")`: tool của Router.
- `worker._call_tool` và `router._call_tool`: chỗ chặn tool khi replay.
- Kịch bản eval đã có dạng "lượt model theo thứ tự cho từng vai", nên trace ghi được có thể đổi thành kịch bản eval.

## NOT_CHECKED

- CI trên GitHub (chưa mở PR).
- `npm test` của web: không sửa `web/`, không chạy lại.
- Kịch bản dùng `prices.cost` theo bảng giá có sẵn; trên CI không có file giá tải về thì chi phí có thể là 0. Cổng không chặn theo chi phí.
