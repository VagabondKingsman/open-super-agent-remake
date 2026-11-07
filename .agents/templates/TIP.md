# TIP-<ID> · <mục tiêu>

- Owner / Coordinator / Builder / branch / base SHA: <...>
- Skill Flow: osa-dev → ai-work-method → vibecode-kit (+ prose/data skill khi cần)
- Scope và out-of-scope: <...>
- Input/nguồn/ref: <file/PR/claim/evidence đã mở; thiếu gì ghi chưa biết>
- Output: <artifact/path/behavior>
- Constraints/approval: <repo-only, no-send/no-paid mặc định; cap nếu được duyệt>
- REUSABLE_COMPONENTS: <đã đối chiếu code/thư viện nào trước tạo mới>

| REQ | AC quan sát được | Test/command/artifact | Priority |
|---|---|---|---|
| REQ-1 | AC-1: Given ... When ... Then ... | <kết quả kỳ vọng, count scope> | P0 |

## Plan / guardrails

- SCAN → BUILD → VERIFY theo phụ thuộc, giới hạn tối đa ba vòng Retro.
- ACTIVE RETRO GUARDRAILS: <RETRO-ID / regression command>
- Isolation/data/runtime: <temp DB trước import, fake LLM, Docker/sandbox needs>
- Failure/stop/escalation: <không test pass, thiếu usage, cap, đổi scope>
- DEVIATIONS / SUGGESTIONS: <chi tiết tự quyết trong scope hoặc đề xuất cần owner>
