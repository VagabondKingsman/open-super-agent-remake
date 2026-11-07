> Cập nhật 07/11/2026 (Asia/Saigon): xác nhận quyền của chủ việc cho phép bundle đầy đủ và cài mặc định. Nội dung bên dưới là bằng chứng đợt cài ban đầu; hướng dẫn hiện hành ở ai-native-skills.md.

# VERIFY: AI Native pack cho OSA

Thời điểm: 07/11/2026 01:33 (Asia/Saigon). Phạm vi: cài local, không push, không gọi LLM trả phí, không gửi channel thật.

## Requirement coverage

6/6 yêu cầu triển khai đã hoàn thành. Chưa nghiệm thu chất lượng chọn skill của mô hình thật hoặc thực thi helpers qua Computer thiếu Docker.

| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC-1: đúng cơ chế OSA | PASS | Native skills.from_file/save; SQLite `data/osa.db`, bảng skills; không có enabled flag |
| AC-2: 7 package + mentor đủ nguồn | PASS (local-only) | 129 file nguồn SHA-256 khớp; helpers/assets/references giữ nguyên; zip riêng |
| AC-3: lớp truyền dạy | PASS | Mentor VI + worked-examples (4 bài) + acceptance-drills; TIP/AC, routing, handoff và giới hạn |
| AC-4: runtime discovery | PASS | Restart; GET /api/bots/1..4/skills đều có đủ 8 shared skills; Router/Worker có load/read |
| AC-5: kiểm định | PASS với deferred | 124 pytest, 15 frontend tests, build/i18n, fake-agent integration và helper smoke |
| AC-6: docs/quyền/local commit | PASS | Docs cài/update; license audit; 7 payload không vào git, chỉ commit installer/mentor/docs/tests |

## Scenario results và QA 3 tầng

- Tier 1: native discovery, idempotent install, slash/export, Router -> Worker load/read với FakeLLM, API thật và khởi động lại đều PASS.
- Tier 2: shared/private override, skill visibility, offset sai, dữ liệu dài/control characters, source thiếu/sai tên, dung lượng skill store, bot không tồn tại và zip trong thư mục chính đều PASS.
- Tier 3 (phần liên quan): chặn absolute path/traversal/symlink/binary và giới hạn resource/tool output PASS. Không mở host shell mới, không đọc credential. UI/GPU/render performance không thuộc thay đổi này; NOT_CHECKED.

Bộ regression mới có 14 test; tổng toàn repo 124 pytest. Test dùng payload giả lập do repo tạo, không đòi bản nguồn bên thứ ba để CI chạy.

## Technical health

- `uv run pytest -q`: 124 passed.
- `uv run python -m osa.i18n`: backend 500, frontend 883 chuỗi cho mỗi ngôn ngữ en/vi; thiếu 0, thừa 0, chuỗi Chinese UI chưa bọc t(): 0.
- `cd web && npm test`: 15 passed; `npm run build`: PASS. Vite vẫn cảnh báo bundle trên 500 kB, không phải lỗi build mới.
- Host helper smoke trong `.venv/bin/python`: 17/17 lệnh exit 0 sau khi sửa lệnh kiểm tra tự đoán sai. Có argparse help, Retro selftest, refinery demo/bites, SOT adapter/hygiene/baseline/check/gate/bites, scan prose và node syntax check.
- Refinery training-demo: positive control + 6 bites áp dụng PASS; 9 domain gates không cấu hình là N/A, không tính thành PASS.
- SOT demo: 6/6 bite tests bắt đúng lỗi. Mọi thao tác demo chạy trên bản sao, không sửa dữ liệu người dùng.
- `measure-ui.js`: chỉ node syntax PASS; chưa đo trên DOM/render thật.
- Prose scan VI đã chạy và đọc lại: V12 chủ yếu là false positive do scanner bỏ inline code rồi thấy khoảng trắng trước dấu câu; tên Deep Check/frontmatter là vùng bảo vệ. Đã bỏ từ cường điệu còn lại trong docs; không sửa script gốc để làm xanh máy quét.
- Live DB: số bản ghi `llm_usage` không tăng trong cài đặt/verify. Không phát task live.

## Retro Rubric

Điểm do executor tự đánh giá theo artifact, không phải mô hình khác chấm độc lập. Engine `retro_rubric.py` kiểm cổng:

- Vòng 1: 6/10 (R2=0): integration test gọi Router.user không có thật; helper smoke dùng sai tên subcommand. Chưa phải lỗi sản phẩm đã ship.
- RETRO-01: đọc entrypoint/CLI thật, dùng server.safe_handle và FakeLLM; regression guard chạy 14 test pack PASS.
- Vòng 2: R1=2, R2=2, R3=2, R4=1, R5=2, tổng 9/10; engine PASS. R4 giữ 1 vì có thêm adapter runtime phải bảo trì.

## Overall status

READY-with-deferred cho local installation/plumbing, không tuyên bố OSA đã có chất lượng suy luận ngang Build Bot.

Deferred:

1. Live-agent routing/chất lượng phối hợp chưa test vì không dùng LLM trả phí.
2. Computer thiếu Docker (`docker_missing`); skill không tự cấp host shell. Host helper PASS không đồng nghĩa Computer PASS; cần chuyển package/dependencies sang môi trường Computer khi có Docker.
3. Cả 7 package chưa có grant phân phối lại trong bản cung cấp: cài local, không đưa payload vào repo công khai. Clone repo trống chưa có 7 package.
4. Chưa chạy QA HTML/GPU thực tế; request hiện tại chỉ cài skill.

Evidence local: `/workspace/osa-ui-shots/ai-native/` gồm TIP, install/API JSON, skill-list.json, pytest/i18n/frontend logs, helper-smoke.json và RETRO-REPORT.md. DB backup riêng nằm ở cùng thư mục, không được chia sẻ hay commit. Zip: `/workspace/osa-ui-shots/ai-native-osa-pack.zip` (private local-only).
