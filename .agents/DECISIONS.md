# Quyết định dự án (ADR)

Ngày ADR: **07/11/2026, Asia/Saigon (UTC+7)**. Đây là ngày sự kiện/biên soạn từ các báo cáo, không suy ra giờ phê duyệt. ADR không thay approval của Tin Tin; bot chỉ thêm quyết định trong scope được giao, đề xuất scope lớn phải ghi Proposed.

## ADR-001 · Accepted · Port v0.6 thay merge cơ học

Merge trực tiếp khoảng 64 conflict giữa hai kiến trúc i18n. Abort, dựng trên v0.6.0/9790ffa, port VI và fixes riêng có chọn lọc; giữ safety. Public remake có lịch sử snapshot khác upstream nên chuyển delta bằng forward commits/PR, không rewrite/force-push. Local ancestry-ours là xử lý một lần, không mẫu mặc định. Nguồn: `docs/cap-nhat-tu-upstream.md`, PR #1.

## ADR-002 · Accepted · VI mặc định, giữ Chinese-as-key

Dùng chung kiến trúc i18n v0.6 cho VI/EN/ZH, không ghép i18next cũ. Giữ preference đã lưu và migration, placeholder parity; source Chinese không có nghĩa UI phải mặc định Chinese. Nội dung chat cũ/prompt/app fallback không rewrite hàng loạt. Nguồn: `docs/i18n.md`, PR #1–#3.

## ADR-003 · Accepted · Bundle nguồn team-authored

Tin Tin xác nhận team tạo bảy skill và cho phép phân phối/cài mặc định. Track toàn cây helper/reference, inventory SHA-256, MIT LICENSE/NOTICE; giữ credit pstack và tham chiếu font OFL, không kèm font binary. Thay quyết định local-only thời eval; không suy quyền với tài sản bên ngoài. Nguồn: PR #5, `skills-pack/ai-native/NOTICE.md`.

## ADR-004 · Accepted · Shared defaults không ghi đè sửa tay

Bảy nguồn + mentor là shared native skills, bot mới tự thấy; reconcile version/hash giữ edits/resources/tombstones/private overrides và nhận legacy khớp. Opt-out config/env không xóa dữ liệu. Không thêm tám bản sao cho từng bot. FS+DB crash không hoàn toàn atomic, phải báo drift, không reset tự động. Nguồn: `docs/vi/ai-native-skills.md`, PR #5.

## ADR-005 · Accepted · Hard AC quan trọng hơn điểm trung bình

v1/v2 NO-GO dù routing/mean tốt vì count/patch chưa đạt. GO v3 chỉ sau exact final patch applies + tests PASS, exact body count/self-report khớp và regression/routing/paging giữ đúng (output mean ≥4 trong rubric đợt đó). Chỉ E02/E07 rerun v3; không gọi full v3 hay “ngang Build Bot”. GO cho handoff/review, không cấp quyền merge hoặc bảo đảm mọi prose không lỗi. Nguồn: `docs/vi/ai-native-live-eval.md`.

## ADR-006 · Accepted · Công cụ đo, không tin self-count

Dùng verify_facts trên final draft; markdown_body khóa scope blog, sửa xong phải verify lại. Hunk-count đúng không chứng minh context/apply/test; inspect_repo trước, check_patch offline trên snapshot thật, exact hash và tests cũ giữ nguyên. Sandbox thiếu thì BLOCKED; instruction chưa là hard gate mọi câu model. Nguồn: `docs/vi/deterministic-verification.md`, `local-patch-checks.md`, PR #4.

## ADR-007 · Accepted · Verify có giới hạn và cost cap

FakeLLM/temp DB trước; live run chỉ khi có approval theo đợt, cap/reservation/stop, restore settings. Không channel send; không dùng Router thay Worker evidence hay unavailable thay Docker E2E. Thiếu hạ tầng thì NOT_CHECKED/SKIP có lý do; không tìm host-shell/token workaround. Nguồn: live-eval + default-install reports và RULES.

## ADR-008 · Accepted cho handoff local · GitHub là bộ nhớ chung

Dùng `.agents/` với root AGENTS/README pointers, STATE snapshot + BOARD owner + log phiên + templates. Source skills ở một chỗ, bridge osa-dev portable, không chép persona/credential riêng. Claim PR cần merge/xác nhận mới là owner đã nhận, không coi file local là lock. Merge bởi Tin Tin hoặc bot được duyệt rõ; publish/merge còn là bước riêng. Nguồn: yêu cầu handoff 07/11/2026 và log phiên này.

## ADR-009 · Accepted · Chặn long-run bằng guard nhỏ, không chấm AC bằng model

Audit B02 (07/11/2026): Worker gọi `save_page` / `search_memory` ngoài goal, ghi trang không hỏi, rồi task vẫn `done`. Không có A/B model nên không kết luận lỗi nằm ở provider.

Quyết định trong OSA-009:

- Không thêm bộ chấm goal so với tool. Một lần gọi lệch vẫn có thể xảy ra.
- `save_page` đi qua `approvals.decide`. `limits.save_page_approval` mặc định `false`. Rule “自动允许” vẫn ghi thẳng. Ghi thành công thì gắn `side_effects` vào kết quả. Lần chạy quiet mà có ghi trang thì không giấu kết quả.
- `limits.repeat_tool_limit` mặc định 3: cùng một lời gọi liên tiếp thì dừng và đòi câu trả lời cuối. `worker_max_steps` vẫn là trần số vòng. Watchdog vẫn hủy muộn hơn nếu vòng lặp sống sót.
- Kết quả rỗng không được `done`. Phần này trùng B01.

Phương án bị loại gồm bắt xác nhận mọi `save_page`, vì task làm trang hợp lệ sẽ đổi hành vi, và gọi model để xét tool có đúng goal hay không.

Model vẫn có thể tìm một hai lần và ghi trang khi công tắc tắt. Lần ghi hiện trên kết quả. Bật công tắc thì lần ghi phải chờ xác nhận.

Verify live trên head `c9480ef` chỉ ra guard dùng chung `Task.recent_calls`, nên lần gọi đầu của worker Heavy thứ ba bị chặn. Sửa trên cùng nhánh: mỗi worker một lịch sử; trong một batch, mọi `tool_call` id đều có tool result, call bị chặn không chạy; ước lượng lúc hủy gồm cả tên và args đã stream. Không đổi quyết định “không chấm goal bằng model”.

Nguồn là task OSA-009. Tin Tin duyệt tạo task và sửa. ADR này không đổi quyền merge.

## ADR-010 · Accepted · Heavy dừng đúng chỗ khi thiếu draft hoặc hết hạn mức

Live test 07/11/2026 (Experiential, task #48–50 và #61–63) cho thấy một lượt người dùng tạo nhiều Heavy, reviewer vẫn chạy khi chỉ có 0–1 draft, task lỗi vẫn `done`, và burst worker gặp 429 trong khi gọi tuần tự thì 200.

Quyết định trong OSA-010, Tin Tin duyệt scope:

- Một lượt Router chỉ giữ một Heavy. Lần `dispatch` heavy sau trong cùng lượt trả lại task đã có.
- `heavy.min_drafts` mặc định 2. Ít hơn thì task `failed`, không gọi reviewer.
- Draft đủ nhưng có worker lỗi: vẫn tổng hợp, status `partial`.
- 402 và 429 mang `org_token_rate_limit_day`, `insufficient_quota`, `free_limit_reached`, `budget_exceeded` không retry, dừng task, không gọi reviewer.
- 429 `rate_limit_exceeded` (và 429 không thuộc mã hạn mức) chờ `Retry-After`, có trần `provider_retry_cap_s` (mặc định 120 giây) và số lần `provider_rate_retries` (mặc định 1).
- `heavy.concurrency` mặc định 1. `heavy.workers` vẫn là số nhà nghiên cứu, không còn nghĩa “phát cùng lúc”.

Phương án bị loại: vẫn gọi reviewer khi thiếu draft (bản tổng hợp trong live phủ nhận tool đã chạy), và giữ concurrency bằng số worker (burst ~8 request cùng lúc nhận 429).

Hệ quả: Heavy mặc định chậm hơn vì các nhà nghiên cứu chạy lần lượt. Cấu hình cũ không có `concurrency` cũng nhận mặc định 1. 408/409/5xx vẫn retry tối đa 2 lần.

Nguồn là task OSA-010 và báo cáo live đính kèm phiên. ADR này không đổi quyền merge.

## Thêm ADR

`ADR-ID · Proposed/Accepted/Superseded · ngày Asia/Saigon` → context → decision → alternatives/why → consequences → source/approval → ADR thay thế nếu có. Giữ quyết định cũ và ghi superseded; không sửa lịch sử cho khớp hindsight.
