---
name: vibecode-kit
description: >-
  Bridge Hoplite cho Vibecode Kit (bản gốc ở skills-pack/ai-native/vibecode-kit).
  Quy trình AI-First SCAN → RRI → VISION → BLUEPRINT → TASK GRAPH → BUILD ⇄
  RETRO RUBRIC → VERIFY → REFINE, có TIP/AC, Retro Rubric R1–R5, Debug 9 bước,
  QA 3 tầng. Dùng khi người dùng gọi "vibecodekit", "vibe code kit", "làm theo
  methodology/quy trình", hoặc khi update, fix, refactor, test, audit code OSA
  (open-super-agent remake). Luôn chạy sau osa-dev và ai-work-method.
---

# vibecode-kit · bridge cho Hoplite

Bridge này không chép phương pháp. Nguồn duy nhất là bộ đã khóa SHA-256 trong repo:

- `SKILL_DIR` = `skills-pack/ai-native/vibecode-kit/` (tính từ repo root).
- Không sửa gì trong `skills-pack/`. `uv run python -m osa.skillpacks verify-sources` phải giữ PASS.
- Sổ Retro và file làm việc ghi vào `data/vibecode/<TASK-ID>/` (gitignored), không ghi vào `SKILL_DIR`.

## Bước 0 · Nạp đúng chuỗi

1. In dòng `Skill Flow: osa-dev -> ai-work-method -> vibecode-kit` (thêm `-> unslop-vi` nếu có prose VI).
2. Đọc `.agents/skills/osa-dev/SKILL.md`, rồi bridge `.agents/skills/ai-work-method/SKILL.md`.
3. Đọc **hết** `SKILL_DIR/SKILL.md`. Reference chỉ mở khi tới bước cần (bảng ở mục 5 của bản gốc, hoặc `SKILL_DIR/REFERENCES_INDEX.md`).
4. Đọc onboarding repo nếu phiên chưa đọc: `.agents/HANDOFF.md`, `RULES.md`, `STATE.md`, `BOARD.md`, log mới nhất. `git fetch origin i18n-vi` và so SHA trước khi nhận việc.

## Chọn quy mô

| Quy mô | Ví dụ OSA | Chuỗi bước |
|---|---|---|
| Nhỏ, 1 TIP | sửa một bug, thêm key i18n, đổi một check | SCAN nhanh → TIP → BUILD ⇄ RETRO → VERIFY |
| Vừa, 2–5 TIP | gate xác nhận cho `computer_shell`, sửa OSA-015 data dir, hardening vòng nền | đủ 8 bước, RETRO-ID truyền sang TIP sau |
| Lớn, 5+ TIP | port release upstream, code-split frontend, đổi kiến trúc | đủ 8 bước + QA 3 tầng + sổ RETRO xuyên dự án |

## Ánh xạ từng pha sang công cụ Hoplite

| Pha | Làm gì | Reference |
|---|---|---|
| SCAN | Read/Grep/Glob song song; với việc rộng, giao subagent `explore` rồi chỉ giữ kết luận. Ghi `REUSABLE_COMPONENTS`. | `references/scan-report-format.md` |
| RRI | Tự trả lời điều SCAN đã rõ. Chỉ hỏi khoảng trống đổi kết quả, gom một lần bằng `ask_user_question`. | `references/rri-methodology.md`, `rri-question-bank.md` |
| VISION / BLUEPRINT | Chỉ cho việc vừa/lớn. Nêu module/file chạm tới, schema, REQ-ID. | `references/vision-guide.md`, `templates.md` |
| TASK GRAPH / TIP | Viết TIP theo `.agents/templates/TIP.md`: REQ, AC quan sát được, lệnh test, guardrails. | `references/tip-and-report-formats.md` |
| BUILD | Lọc YAGNI 3 câu trước mỗi file/hàm mới. Sửa trực tiếp trong workspace; test dùng temp DB + `tests/fakellm.py`. | bản gốc mục 3.6 |
| RETRO | Sau mỗi lần chạy test, chấm R1–R5 bằng script (dưới). FAIL hoặc < 9/10 thì tự đệ quy, tối đa 3 vòng, rồi escalate. | `references/retro-rubric-protocol.md` |
| DEBUG | Lỗi khó, nguyên nhân chưa rõ: theo 9 bước, không sửa mò. | `references/debug-protocol.md` |
| VERIFY | Chạy lệnh thật, đọc output từng lệnh. Việc vừa/lớn: giao subagent `review` kiểm độc lập để tách BUILD khỏi VERIFY. | `references/qa-protocol.md`, `.agents/templates/VERIFY-REPORT.md` |
| REFINE | Xử lý tồn đọng trong scope. Tính năng mới ngoài scope thì quay lại VISION. | `references/templates.md` |

### Lệnh Retro Rubric

```bash
S=skills-pack/ai-native/vibecode-kit/scripts/retro_rubric.py
uv run python $S init data/vibecode/<TASK-ID>
uv run python $S evaluate data/vibecode/<TASK-ID> --tip TIP-001 --r1 2 --r2 2 --r3 1 --r4 2 --r5 2 --notes "<bằng chứng>"
uv run python $S learn data/vibecode/<TASK-ID> --tip TIP-001 --symptom "<triệu chứng>" --cause "<nguyên nhân gốc>" --guardrail "<quy tắc chặn>" --test-cmd "<lệnh test hồi quy>"
uv run python $S verify-guardrails data/vibecode/<TASK-ID>
uv run python $S report data/vibecode/<TASK-ID>
```

Điểm phải dựa trên output đã chạy, không tự cho điểm khi chưa có bằng chứng.

### Bộ kiểm VERIFY của OSA

Chọn theo phạm vi, ghi command + exit + số test:

```bash
uv run python -m compileall -q osa && uv run python -c "import osa.server"
uv run python -m osa.catalog && uv run python -m osa.templates && uv run python -m osa.i18n
uv run pytest -q
uv run python -m osa.skillpacks verify-sources
(cd web && npm test && npm run build)   # khi đụng UI, i18n hoặc trước bàn giao
```

- Đổi UI: kiểm trên OSA đang chạy ở Preview (`data/live/`, `.hoplite/settings.json`), chụp ảnh bằng `agent-browser`.
- Live LLM chỉ dùng model và cap người dùng đã duyệt. Docker Computer E2E chưa chạy thật thì ghi `NOT_CHECKED`. Bubblewrap SKIP không phải PASS.
- VERIFY REPORT đủ 5 mục: REQUIREMENT COVERAGE, SCENARIO RESULTS, TECHNICAL HEALTH, RETRO RUBRIC SCORE, OVERALL STATUS.

## Ràng buộc Hoplite (thay cho GROK-BOT-COMPAT.md)

- Không có CloudAgent: Hoplite sửa code trực tiếp trong workspace, trên branch của thread.
- Push, mở/cập nhật PR, merge, gửi channel, chạy model trả phí: chỉ khi người dùng duyệt đúng hành động đó. PR chỉ vào `i18n-vi` của `VagabondKingsman/open-super-agent-remake`. Không force-push.
- Mỗi PR cập nhật `.agents/STATE.md`, `.agents/BOARD.md` và thêm `.agents/log/YYYY-MM-DD-hoplite.md` (giờ Asia/Saigon).
- Escalation L3 (scope, kiến trúc lõi, bảo mật, chi phí) thì dừng và hỏi người dùng.

## Báo cáo cuối

`DONE | PARTIAL | BLOCKED`, kèm VERIFY REPORT, bảng Retro (điểm, số vòng, RETRO-ID), file đã đổi, phần chưa kiểm. Prose tiếng Việt cho README/docs/PR: nạp `unslop-vi`.
