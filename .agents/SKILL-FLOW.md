# Skill Flow chuẩn

## Luồng cho OSA

`osa-dev → ai-work-method → vibecode-kit` + `unslop-vi` cho prose VI hoặc `unslop` cho EN.

- `osa-dev`: giữ ngữ cảnh remake, guardrails, workflow CloudAgent/local verify.
- `ai-work-method`: phân rã REQ, TIP/AC, chọn skill và nghiệm thu bằng chứng. Một bot có thể làm Coordinator rồi Executor nhưng phải tách BUILD khỏi VERIFY.
- `vibecode-kit`: `SCAN → RRI → VISION → BLUEPRINT → TASK GRAPH → BUILD ⇄ VERIFY/RETRO → REFINE`. Bug nhỏ rút thành SCAN → TIP → BUILD/Retro → VERIFY; không bỏ AC và bằng chứng.
- Hỏi RRI chỉ cho khoảng trống ảnh hưởng quyết định; không ép tám pha dài cho một thay đổi nhỏ. Dùng lại code có sẵn trước khi tạo abstraction.

## Khi dùng bảy AI Native skills

| Skill | Trigger và gate |
|---|---|
| ai-work-method | Việc nhiều bước/rủi ro/cần phối hợp. TIP nêu mục tiêu, input, output, REQ/AC, constraints, giả định. |
| vibecode-kit | Mọi code/bug/test/refactor/audit. SCAN, TIP, test, QA 3 tầng theo rủi ro và Retro R1–R5. |
| refinery | Bảng/claim nhiều nguồn ngoài. Snapshot + evidence_span + origin_id, engine/bites; bản sao không là nguồn độc lập. Giữ disputed/honest-null. |
| sot-kernel-in-a-box | Nguồn nội bộ có owner. source_canonical → adapter → registry, SHA-256/A3, 6 bites và publish gate gắn digest. Không tự chọn số khi owner chưa duyệt. |
| html3d-slides | Slide HTML/3D, không phải PPTX. Brief/storyboard, DOM + 3D + Ambient chung state, người nói điều khiển; measure-ui.js, render và GPU fallback. |
| unslop | Viết/sửa/soát EN tự nhiên; từ brief VI có thể kèm SEO + tóm tắt VI. Giữ nguồn và số; scanner chỉ gợi ý. |
| unslop-vi | README/docs/PR/prose VI. Bỏ sáo ngữ/văn dịch máy, giữ thuật ngữ và vùng bảo vệ; scan rồi đọc lại bằng phán đoán. |

Research → sản phẩm: refinery → owner duyệt → SOT gate → vibecode-kit hoặc html3d-slides → prose skill. Không dùng refinery thay owner nội bộ. Việc một bước như sửa chính tả thì làm trực tiếp, không ép cả chuỗi.

## Deep Check là gì

Không phải lời nhắc chung “hãy kiểm tra kỹ”. Đây là VERIFY của vibecode-kit + QA Protocol + Retro Rubric; đọc hai reference trong `skills-pack/ai-native/vibecode-kit/references/` trước khi chạy:

- `qa-protocol.md`: CONTEXT → GENERATE → EXECUTE → REPORT → FIX → VERIFY.
- `retro-rubric-protocol.md`: R1 Spec/Contract, R2 Runtime/Test, R3 Edge/Resilience, R4 Blast-radius/Hygiene/YAGNI, R5 Anti-repeat; mỗi chiều 0–2, tổng ≥9/10 và không chiều 0. Tối đa ba vòng tự sửa rồi escalate/debug, không lặp vô hạn.
- Tier 1 bắt buộc: từng AC, coverage P0, startup/core flow, link/assets. Tier 2: edge/error/empty/network/concurrency, UI 375/768/1440 nếu có. Tier 3: performance/security/accessibility theo phạm vi; rủi ro auth/secret thì test bảo mật liên quan là AC bắt buộc, không bỏ chỉ vì ở Tier 3.
- Mỗi tier ghi PASS/FAIL/PARTIAL/SKIP/NOT_CHECKED + lý do. Không tính coverage “đã xem xét” thành coverage “đạt”. Tier 1 chưa đạt thì không READY. Thiếu runtime phải báo deferred, không cộng điểm ảo.
- Test fail → root cause → `RETRO-ID` → regression bite → nạp guardrail vào TIP sau → rerun. Tổng điểm dùng script/công cụ, không tự cộng nhẩm rồi khẳng định PASS.

VERIFY REPORT có năm mục: REQUIREMENT COVERAGE, SCENARIO RESULTS, TECHNICAL HEALTH, RETRO RUBRIC SCORE, OVERALL STATUS. Dùng [mẫu](templates/VERIFY-REPORT.md). Điểm chỉ diễn giải phạm vi đã chạy, không phải giấy phép phát hành.

## TIP/AC tối thiểu

Dùng [TIP](templates/TIP.md): REQ → AC → artifact → test/evidence. Ví dụ AC không viết “i18n tốt”, mà viết “VI mặc định, EN/ZH lưu sau reload; checker 0 thiếu/thừa; placeholder parity; command và kết quả kèm theo”. Chốt scope/count mode trước khi test, không đổi AC sau để hợp thức hóa output.

## Cài skill vào chính Grok Bot cộng sự

Đây là **cài vào tài khoản bot đang build**, khác tám skill tự cài vào DB OSA. Clone source hay chạy OSA không tự cài skill cho Grok Bot.

1. Từ repo đã xác minh, chạy `uv run python -m osa.skillpacks verify-sources` (không cần paid API). Inventory hiện chứa 129 file nguồn. Giữ LICENSE/NOTICE, không sửa hash để ép PASS.
2. Lấy bảy nguồn `skills-pack/ai-native/<name>/SKILL.md` theo bảng trên; đây là bản gốc, không phải adapter sinh trong data OSA. Lấy thêm bridge [`skills/osa-dev/SKILL.md`](skills/osa-dev/SKILL.md).
3. Khám phá schema `UpdateSkill` trong tool catalog tài khoản đó. Khi có, dùng action `write`, name/description từ YAML frontmatter và body là toàn bộ recipe Markdown. Giữ các metadata khác nếu platform hỗ trợ; không tự xóa frontmatter keys. Skill đã có thì đối chiếu, dùng id đúng, không ghi đè sửa riêng không được duyệt. Không nhầm tool OSA `save_skill` với Grok Bot `UpdateSkill`.
4. Giữ **cả cây resources** (scripts/references/demo/evals) và relative paths. Nếu UpdateSkill chỉ nhận body, riêng lệnh đó chưa đưa helpers vào kho skill: ghi rõ resource mapping tới checkout `skills-pack/ai-native/<name>/`. Chỉ đọc reference/chạy helper từ repo đã review; `SKILL_DIR` phải trỏ cây thật. Nếu platform không truy cập được helpers, đánh dấu `PARTIAL`, không nhận đã cài đủ.
5. Nếu `UpdateSkill` không có, ghi `NOT_INSTALLED` và báo đúng capability thiếu. Không bịa id hoặc giả “copy file là cài”. Tài khoản Kingfisher có tool này. Phiên cloud viết OSA-014 không phải tài khoản đó. Bot mới xem catalog của chính mình. Không đi tìm token để thay.
6. Nạp `osa-dev`, `ai-work-method`, `vibecode-kit` bằng Skill (hoặc thao tác đọc tương đương do platform cung cấp). Kiểm đọc được reference QA/Retro và file cuối của resource dài. Báo bảng `skill / source ref / installed id hoặc NOT_INSTALLED / resources / load-check`; cài recipe không chứng minh helpers đã chạy.

Bridge trong folder này được port từ skill osa-dev của Build Bot, bỏ đường dẫn riêng, dùng source trong repo và không đoán main cùng tip. Không chứa persona riêng.

## Cài skill vào Hoplite

Hoplite không có `UpdateSkill`. Nó tự đọc mọi `.agents/skills/<name>/SKILL.md` trong checkout và liệt kê thành repository skill. Mỗi file ở đó là bridge mỏng trỏ về `skills-pack/ai-native/<name>/`, không chép phương pháp. Bản gốc khóa SHA-256, không sửa.

| Bridge | Nguồn | Helper đã chạy thử (OSA-024) |
|---|---|---|
| `osa-dev` | bridge riêng của remake | không có helper |
| `ai-work-method` | `ai-work-method/` | không có helper |
| `vibecode-kit` | `vibecode-kit/` | `retro_rubric.py selftest` PASS |
| `unslop-vi` | `unslop-vi/` | `scan_vi.py -` bắt được V2 |
| `unslop` | `unslop/` | `scan_en.py -` bắt được B1 |
| `refinery` | `refinery/` | `bites.py` (domain `training-demo`) TẤT CẢ RĂNG CẮN ✓ |
| `sot-kernel-in-a-box` | `sot-kernel-in-a-box/` | `sot_check.py` PASS, `sot_bites.py` 6/6 trên bản chép `examples/demo_org` |
| `html3d-slides` | `html3d-slides/` | `node --check scripts/measure-ui.js` OK. Chưa đo trên trình duyệt. |
| `ai-native-mentor` | `ai-native-mentor/` | không có helper |

Phiên Hoplite mới kiểm nhanh: danh sách repository skill có đủ chín tên trên, `uv run python -m osa.skillpacks verify-sources` PASS. Helper chạy bằng `.venv/bin/python` của repo (có PyYAML). Script ghi dữ liệu (refinery, sot) chạy trên bản chép ở thư mục tạm hoặc `data/<skill>/<TASK-ID>/`, không chạy trong `skills-pack/`.

## Skill trong runtime OSA

OSA startup mặc định có bảy skill + `ai-native-mentor` dưới dạng shared DB records. `load_skill` trả `method_source`; theo `next_offset` tới null/COMPLETE, không dừng tại CONTINUE_REQUIRED. `read_skill_resource` liệt kê/đọc, không chạy helper. Worker phải nạp lại skill: tool results riêng của Router không tự đi cùng dispatch. Dispatch goal phải chứa TIP/AC, Skill Flow, input/output và constraints.

`verify_facts` kiểm exact final draft, count/sum/quotes. Blog gửi cả phần blog có headings, dùng `markdown_body`; loại YAML frontmatter, headings và code, không gửi SEO/tóm tắt. Sau sửa phải verify lại. Check số không chứng minh factual correctness/runtime.

`inspect_repo` → `check_patch` chỉ cho fixture operator đã đăng ký, không phải host shell cho repo OSA. Chỉ giao exact patch hash khi git apply --check, apply và sandbox pytest đều PASS. Thiếu sandbox trả BLOCKED; không chạy không cô lập.
