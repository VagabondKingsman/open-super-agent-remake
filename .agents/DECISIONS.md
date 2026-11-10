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

## ADR-011 · Accepted · Prompt gửi model dùng tiếng Anh, câu trả lời theo ngôn ngữ giao diện

Live sau OSA-009: UI là tiếng Việt, user nhắn tiếng Anh, router trả tiếng Trung ("已重新派发…"). Heavy còn để nhãn `方案` trong prompt reviewer, và câu trả lời tiếng Việt lẫn chữ đó. Prompt hệ thống và mô tả tool gốc viết bằng tiếng Trung, nên model bám tiếng Trung. `model_hint()` để trống khi lang là zh, và bản en của hint vẫn là câu tiếng Trung. `routines.describe(..., in_lang="zh")` cố định lịch trong prompt router.

Quyết định trong OSA-011, Tin Tin giao scope:

- Prompt, mô tả tool, và câu lệnh chèn vào context gửi model viết bằng tiếng Anh. Giữ placeholder, hợp đồng JSON, và marker mà code đọc.
- `i18n.ANSWER_LANG` là một đoạn tiếng Anh cho vi, en, zh. `model_hint()` luôn nối đoạn của `i18n.lang()` (mặc định vi) vào cuối prompt router, worker, reviewer, import trí nhớ, lọc sự kiện, và draft skill.
- Nhãn draft Heavy là `=== Draft N ===`. Prompt reviewer cấm chép marker đó vào câu trả lời.
- `in_lang="zh"` không còn trong code gọi prompt. Lịch trong prompt dùng ngôn ngữ giao diện hiện tại.
- Marker hệ thống gửi model đổi sang tiếng Anh (`system notice`, `system-attached current state`, `system image`, `[bot: name]`). `defang` vẫn gỡ marker Trung cũ và marker Anh mới. Quiet marker chỉ thị model là `[nothing new]`; regex vẫn nhận `无新内容` / `没有新内容`.
- Dòng user thấy (thẻ, log tool, lỗi) vẫn là khóa i18n tiếng Trung. Kết quả tool trước đây viết cứng tiếng Trung và hiện trong task log chuyển sang `i18n.t`.

Không làm trong ADR này: dịch persona của template có sẵn (vi và en đã phủ `en:` lúc cài; zh giữ nguồn Trung), mô tả tool do MCP server trả về, nội dung user viết (instruction, memory, skill), và validator chặn output sai ngôn ngữ. Chỉ thị không sửa chữ model đã viết.

Nguồn là task OSA-011. ADR này không đổi quyền merge.

## ADR-012 · Accepted · Chi phí lưu và hiện bằng USD

Trang chi phí đang hiện `¥`. models.dev ghi USD / triệu token; code nhân `pricing.usd_rate` (mặc định 7.1) rồi lưu vào `llm_usage.cost`. Bảng `pricing.models` cho `deepseek-flash` và `deepseek-v4-pro` là giá CNY chép từ trang giá, không nhân rate. Tab Giới hạn & ngân sách là trần token, số bước và số giây, không phải một số tiền.

Quyết định trong OSA-013, Tin Tin giao scope:

- Đơn vị tính và đơn vị hiện là USD. Field API `currency` giữ tên, giá trị luôn `$`. `prices.rate` giữ trong payload, giá trị luôn `1`, không còn là tỷ giá.
- Giá models.dev dùng nguyên số USD. Không nhân, không hiện CNY.
- Bảng mặc định đổi sang giá niêm yết USD trên https://api-docs.deepseek.com/quick_start/pricing/ , đối chiếu 07/11/2026. Giờ cao điểm trong config giữ nguyên (giờ Bắc Kinh, khớp UTC trên trang giá).
- Config cũ còn `currency` là ¥, CNY, RMB hoặc 元: số trong `pricing.models` chia cho `legacy_cny_per_usd`, không có thì `usd_rate`, không có thì 7.1, rồi tính như USD.
- DB: `settings.cost_unit`. Chưa có cờ thì dòng thuộc model trong `pricing.models` tính lại từ cột token theo giá USD hiện tại (kể cả giờ cao điểm). Dòng khác chia cho cùng hệ số. Sau đó ghi cờ. Lần mở sau không chia nữa. `legacy_cny_per_usd: 1` nghĩa là số cũ đã là USD.
- Trần trong tab giới hạn không đổi đơn vị. Không có trần tiền CNY để quy đổi.

Phương án bị loại: giữ hai đơn vị trên UI, và nhân tiếp models.dev với 7.1. Cũng không lấy giá models.dev hôm nay để viết lại mọi dòng cũ, vì giá catalog đổi thì lịch sử không còn là số đã ghi.

Hệ quả: dòng models.dev chia 7.1 ra đúng USD đã nhân lúc ghi. Dòng `deepseek-flash` / `deepseek-v4-pro` được tính lại theo bảng USD mới nếu lần khởi động đầu đã dùng config USD. Nếu lần đó config vẫn là CNY, hai model này thành giá CNY cũ / 7.1, thấp hơn giá niêm yết khoảng 6% vì bảng CNY cũ đã làm tròn (tỷ lệ khoảng 6,67). Muốn đúng giá niêm yết thì sửa config sang USD trước lần khởi động đầu.

Nguồn là task OSA-013. ADR này không đổi quyền merge.

## ADR-013 · Accepted · Bàn giao nằm trong .agents, số box không kèm secret

Tin Tin muốn bot mới chỉ đọc `.agents/` là tiếp tục được như Kingfisher. Chat cũ không đi theo repo.

Quyết định trong OSA-014:

- [HANDOFF](HANDOFF.md) là file đọc đầu. [OPS](OPS.md) ghi cách chạy box. [PROTOCOL](PROTOCOL.md) ghi cách làm việc với Tin Tin, gồm câu `Duyệt merge`.
- Đường dẫn `/workspace/osa-run/...` là đường dẫn đã thấy trên box chạy `c16e6bb`. Máy khác xem fd của process. Backup đúng file DB đang mở.
- Không ghi key, mật khẩu, email, cookie, hay hostname tailnet.
- Bot mới chọn prefix, hỏi Tin Tin, giữ cách nói trong PERSONA.

Phương án bị loại: chép nguyên transcript phiên vào git, và viết giá trị env vào OPS.

Hệ quả: bot không có thư mục này thì không có ngữ cảnh vận hành. File không cấp quyền merge, model trả phí, hay mở Funnel.

Nguồn là task OSA-014, 07/11/2026. ADR này không đổi quyền merge.

## ADR-014 · Accepted · Làm local trước, đẩy bằng patch

Ngày 10/11/2026, Asia/Saigon. Tin Tin yêu cầu sửa và test trên box cho tới khi ổn định rồi mới mở PR. Box không `git push` được, và cloud agent không nhận bundle nhị phân.

Quyết định:

- Sửa trong một worktree riêng trên box, tách từ `origin/i18n-vi`. Checkout đang chạy server không bị đổi nhánh, stash hay reset.
- Test như CI trên worktree. Commit nhỏ, author `Tin Tin <tintin@users.noreply.github.com>`.
- `git format-patch origin/i18n-vi..HEAD` ra file text. Cloud agent `git am` lên branch mới, push, mở PR vào `i18n-vi`. CI xanh và Tin Tin đồng ý thì merge bằng merge commit.
- `config.yaml` của box (`computer.idle_pause_s: 2592000`) không bao giờ vào patch.

Phương án bị loại: sửa trực tiếp trên checkout đang chạy (dễ commit nhầm `config.yaml`, dễ làm server đọc code dở), gửi bundle nhị phân (bị từ chối).

Hệ quả: PR #36 tới #39 đi theo cách này. Mỗi patch phải áp sạch trên `i18n-vi` mới nhất. Nếu base đã đổi, xuất lại patch trên base mới.

Cũng trong phiên deep audit 10/11, STATE.md chuyển thành snapshot ngắn. Lịch sử append cũ nằm nguyên văn ở `archive/STATE-2026-11-07-den-2026-11-10.md`. Phiên sau sửa STATE theo snapshot, ghi diễn biến vào `log/`.

Nguồn là yêu cầu của Tin Tin ngày 10/11/2026. ADR này không đổi quyền merge.

## Thêm ADR

`ADR-ID · Proposed/Accepted/Superseded · ngày Asia/Saigon` → context → decision → alternatives/why → consequences → source/approval → ADR thay thế nếu có. Giữ quyết định cũ và ghi superseded; không sửa lịch sử cho khớp hindsight.
