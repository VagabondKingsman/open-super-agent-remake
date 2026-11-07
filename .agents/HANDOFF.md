# Bàn giao OSA · file đọc đầu cho bot mới

Đọc file này trước. Nó thay bộ nhớ chat của Kingfisher. Tài liệu không cấp quyền merge, chạy model trả phí, gửi channel, hay mở OSA ra ngoài tailnet.

Repo: `VagabondKingsman/open-super-agent-remake`. Base: `i18n-vi`. Upstream `kadaliao/open-super-agent` chỉ đọc. Giờ trong các file là **Asia/Saigon (UTC+7)**.

## Đọc theo thứ tự

1. File này.
2. [README](README.md), [RULES](RULES.md), [PERSONA](PERSONA.md), [PROTOCOL](PROTOCOL.md).
3. [STATE](STATE.md), [BOARD](BOARD.md), log mới nhất trong [log/](log/). Bỏ qua `_TEMPLATE.md`. STATE là snapshot. Fetch lại ref trước khi nhận việc.
4. [SKILL-FLOW](SKILL-FLOW.md). Cài bảy skill trong `skills-pack/ai-native/` và bridge [osa-dev](skills/osa-dev/SKILL.md). Đọc skill trước khi làm, không gọi tên rồi coi như đã nạp.
5. [ARCHITECTURE](ARCHITECTURE.md), [OPS](OPS.md) nếu sắp chạy box, [DECISIONS](DECISIONS.md).
6. [templates/](templates/) khi lập TIP, viết PR, hoặc bàn giao một task. `templates/HANDOFF.md` là mẫu một task. File này là bàn giao cả dự án.

[PROMPT](PROMPT.md) là đoạn Tin Tin dán vào bot mới. Sau khi đã đọc danh sách trên thì không cần đọc lại như quy trình.

## Head hiện tại

Đối chiếu trong phiên OSA-014, 07/11/2026:

`origin/i18n-vi = c16e6bb0e42de25ddd0ac12f58e179bbd23f1ed3`

Đó là merge [PR #15](https://github.com/VagabondKingsman/open-super-agent-remake/pull/15). `merged_at` API `2026-11-07T13:47:09Z` (20:47:09 Asia/Saigon). `merged_by` là VagabondKingsman. Head của PR là `87980892e3a6141035516ee0b43d3d9136c1b3f5`. Không có PR mở vào `i18n-vi` lúc đối chiếu.

Phiên sau chạy `git fetch` và `git rev-parse origin/i18n-vi`. SHA mới hơn thì đọc log mới. Đừng coi `c16e6bb` là latest mãi. `main` không được khẳng định cùng tip.

File này vào repo bằng [PR #16](https://github.com/VagabondKingsman/open-super-agent-remake/pull/16), branch `grok-bot/osa-014-handoff`. Lúc viết thì PR chưa merge. Nếu `origin/i18n-vi` vẫn là `c16e6bb`, bàn giao này chưa nằm trên base.

## Đã merge

Giờ là `merged_at` đổi sang Asia/Saigon. `merged_by` của cả 15 PR trên API là VagabondKingsman. Chi tiết và các câu "Chưa merge" cũ nằm trong STATE. Những câu đó là trạng thái lúc viết mục, bảng này mới hơn.

| PR | Giờ merge | SHA | Việc |
|---|---|---|---|
| [#1](https://github.com/VagabondKingsman/open-super-agent-remake/pull/1) | 00:38:33 | `129db18` | Port upstream v0.6.0, VI, Chinese-as-key. |
| [#2](https://github.com/VagabondKingsman/open-super-agent-remake/pull/2) | 00:52:43 | `c6ec68b` | Fallback locale, HTML mặc định vi-VN. |
| [#3](https://github.com/VagabondKingsman/open-super-agent-remake/pull/3) | 01:03:49 | `afdea0e` | Nhãn routine theo ngôn ngữ UI. |
| [#4](https://github.com/VagabondKingsman/open-super-agent-remake/pull/4) | 03:34:28 | `7c20454` | Skill pack, paging, verify_facts, inspect_repo, live-eval v1–v3. |
| [#5](https://github.com/VagabondKingsman/open-super-agent-remake/pull/5) | 07:51:47 | `2a36b59` | Bundle bảy nguồn, SHA-256, cài shared mặc định. |
| [#6](https://github.com/VagabondKingsman/open-super-agent-remake/pull/6) | 08:26:01 | `3c08269` | Handoff `.agents/` đầu tiên. |
| [#7](https://github.com/VagabondKingsman/open-super-agent-remake/pull/7) | 12:23:22 | `5dc007b` | OSA-006 CONTRIBUTING cho bot. |
| [#8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8) | 12:31:44 | `6e5d3ff` | OSA-004 port v0.6.1 (`0897360`, `ec71362`, `3432671`), `OSA_DATA_DIR`. |
| [#9](https://github.com/VagabondKingsman/open-super-agent-remake/pull/9) | 12:37:13 | `d7f2ee9` | Docs đánh dấu OSA-004 xong. |
| [#10](https://github.com/VagabondKingsman/open-super-agent-remake/pull/10) | 15:51:53 | `7b73abb` | OSA-009 sửa audit B01–B07. |
| [#11](https://github.com/VagabondKingsman/open-super-agent-remake/pull/11) | 15:59:20 | `d2938f4` | Docs OSA-009 xong, mở OSA-010. |
| [#12](https://github.com/VagabondKingsman/open-super-agent-remake/pull/12) | 18:25:08 | `f471839` | OSA-010 một Heavy mỗi lượt, quorum draft, dừng khi hết hạn mức. |
| [#13](https://github.com/VagabondKingsman/open-super-agent-remake/pull/13) | 18:25:37 | `fcc2d89` | OSA-011 prompt gửi model sang tiếng Anh, trả lời theo `i18n.lang()`. |
| [#14](https://github.com/VagabondKingsman/open-super-agent-remake/pull/14) | 19:08:18 | `653f866` | OSA-012 trang offline vi trước, en sau. |
| [#15](https://github.com/VagabondKingsman/open-super-agent-remake/pull/15) | 20:47:09 | `c16e6bb` | OSA-013 chi phí lưu và hiện bằng USD. |

PR #1 đến #5 rơi vào đêm 06/11 UTC, tức sáng 07/11 giờ Sài Gòn. Bản OSA đang chạy là v0.6.1. Không gồm desktop/Tauri/`v0.7.0-preview`.

Việc đã vào code, rút từ log và từ code ở `c16e6bb`:

- VI mặc định, EN/ZH, Chinese-as-key. Chat cũ không tự dịch.
- Bảy skill AI Native cộng `ai-native-mentor` cài shared lúc startup. Opt-out bằng `skills.ai_native_defaults: false` hoặc `OSA_AI_NATIVE_DEFAULTS=false`.
- Heavy: một lượt một task, `min_drafts` 2, `concurrency` 1. 402 và 429 hết hạn mức thì dừng, không gọi reviewer. 429 rate limit thì chờ `Retry-After`.
- Prompt hệ thống và mô tả tool của OSA là tiếng Anh. `model_hint()` luôn gắn chỉ thị trả lời theo ngôn ngữ UI, mặc định vi. Nhãn draft là `=== Draft N ===`.
- Marker code còn đọc: `[附件]`, khóa `需要你做的事`, và regex quiet vẫn nhận `无新内容` / `没有新内容` cạnh `[nothing new]`. Đừng xóa các chuỗi này khi "dọn tiếng Trung".
- Template có khối `en:` thì UI khác `zh` dùng bản tiếng Anh. UI `zh` giữ nguồn Trung. Không có khối `vi:`.
- Trang offline của service worker nằm trong `web/public/sw.js`, ngôn ngữ lấy từ Cache Storage `osa-lang`, thiếu thì tiếng Việt.
- Chi phí là USD. `settings.cost_unit` chặn lần chia thứ hai. Tab giới hạn vẫn là token, bước, giây.
- `OSA_DATA_DIR` chuyển DB, apps, workspace, log của `scripts/osa-start.sh` khi `memory.db` là đường tương đối. Đường tuyệt đối thì không. Xem OSA-015.

Live OSA-011 đã có trong repo: [bằng chứng](evidence/osa-011-live-test/LIVE-TEST.md), head lúc chạy `f83e3cb`, Experiential, mọi model đuôi `:free`, cost ghi 0. Bốn lượt chat (vi, en, single, heavy) đều CJK 0. Báo cáo để trạng thái PARTIAL. 14 dòng usage, 116.236 token (`cache_hit` + `cache_miss` + `output`), vượt mục tiêu khoảng 100.000 nên không chạy routine. Guard harness cộng cột `input` thay vì `cache_hit` + `cache_miss`, phải sửa trước đợt sau. Harness dừng websocket vì regex 402 khớp offset 14025. Log server không có 402. `results.json` còn heavy `running` ở 60,38 giây. `summary.json` ghi heavy PASS 124 giây. Thư mục `raw/` không đưa vào git. Câu `NOT_CHECKED` trong log OSA-011 là lời lúc mở PR #13.

## Còn lại

Ưu tiên và AC đầy đủ hơn ở [BOARD](BOARD.md). Bảng này là thứ tự nên hỏi Tin Tin. Chưa có câu giao thì chưa làm.

| ID | Ưu tiên | Việc | AC gợi ý | Chưa kiểm |
|---|---|---|---|---|
| OSA-015 | P0 | DB không đi theo `OSA_DATA_DIR` khi `memory.db` là đường tuyệt đối | DB của process nằm trong data dir, hoặc process từ chối khởi động và nói rõ. Sửa `test_absolute_db_path_still_wins`. Backup file DB đang mở trước khi đổi. | Box đã thấy file mở lệch. Chưa sửa code. |
| OSA-020 | P1 | Dọn `config.experiential.yaml` trên box sang USD | `pricing.currency` là `$`. Bảng tay là số USD hoặc bỏ hẳn. Khởi động lại không chia `llm_usage` lần hai. Không commit file config. | File trên box vẫn để ¥. Code đọc và chia đúng. |
| OSA-019 | P1 | Phần ngôn ngữ OSA-011 để lại | Persona tiếng Việt cho template. Mô tả tool MCP do server trả về. Validator đầu ra sai ngôn ngữ. Giữ marker code đang parse. Không dịch nội dung user. | Chưa có validator. |
| OSA-016 | P1 | Chạy thử routine trên data được phép | Một lịch, filter quiet, không gửi channel thật, có log lệnh. | `NOT_CHECKED` |
| OSA-007 | P1 | UI sau đăng nhập, khoảng 390px, và các mốc 768/1440 | Ảnh đã xóa dữ liệu riêng. Ba ngôn ngữ còn đúng sau reload. | Bot không mở được tailnet sau login. Tin Tin thử trên điện thoại. |
| OSA-017 | P1 | Chạy OSA bằng Docker trên máy Tin Tin hoặc VPS | Hết phụ thuộc watchdog và mạng box. Computer E2E nằm ở OSA-002, không gộp vào task này. | Chưa chọn máy. |
| OSA-001 | P2 | Router giao việc thật cho Worker, Worker tự nạp skill | Trace đủ, cleanup. Cần duyệt model và cap trước lượt trả phí. | Worker live chưa nghiệm thu. |
| OSA-002 | P2 | Computer E2E trên máy có Docker | Build app, VNC/CDP, cửa sổ song song, takeover, upload. HTTP 200 không tính. | Box thường thiếu Docker. |
| OSA-018 | P2 | Mẫu A/B Zro và DeepSeek còn lại | Đủ bài đã chốt, cap, điều kiện dừng. | Cần duyệt từng đợt. |
| OSA-003 | P2 | Tách bundle frontend | Đo trước sau. Cảnh báo chunk >500 kB còn từ các bản build cũ (JS khoảng 1,15 MB). Chốt ngưỡng với Tin Tin. | Chưa đụng. |
| OSA-005 | P2 | Rà GitHub Actions | CI đã có backend, frontend, Docker. Đề xuất lỗ hổng rồi mới sửa. | Chưa nhận. |
| OSA-008 | P2 | Reconcile khi crash giữa file và SQLite | Bơm lỗi trên data tạm. Không tự cài lại đè sửa tay. | Chưa nhận. |

Deploy `c16e6bb` trên box, Tin Tin báo, phiên docs không mở DB:

- Process giữ `/workspace/osa-run/osa.db`. Thư mục `/workspace/osa-run/data` không tồn tại. Đây là bằng chứng sống của OSA-015. Đường dẫn này là của box đó. Máy khác phải xem fd, đừng chép đường dẫn.
- Migration OSA-013 trên DB đó: 103 dòng usage, tổng ¥0.18457 thành $0.02600. Cờ `settings.cost_unit`: `currency` USD, `legacy_cny_per_usd` 7.1, `repriced_models` 0, `divided_rows` 64. Code còn ghi khóa `rows`. Bản báo không có khóa đó. 103 trừ 64 bằng 39 dòng `cost = 0` không vào vòng chia, suy từ code, không đếm lại trên DB.
- `repriced_models` 0 khớp model Experiential không nằm trong bảng tay `deepseek-flash` / `deepseek-v4-pro`: các dòng khác 0 bị chia 7.1, không bị tính lại theo giá niêm yết.
- File operator `config.experiential.yaml` vẫn khai `currency` ¥, `usd_rate` 7.1, và bảng tay CNY. `manual_table_is_cny()` chia bảng đó lúc đọc. Việc dọn file là OSA-020.

`legacy_cny_per_usd: 1` chỉ khi số cũ đã là USD. DB box này đã chia một lần. Lần sau cờ USD giữ nguyên số.

## Bước đầu phiên sau

1. Ack với Tin Tin. Nói đã đọc HANDOFF, head đang thấy, và việc định hỏi. Bot khác Kingfisher thì hỏi prefix. Giữ cách nói trong PERSONA.
2. `git status --short`. Cây sạch thì `git switch i18n-vi` và `git pull --ff-only origin i18n-vi`, rồi `git rev-parse HEAD`. Cây bẩn hoặc pull không tua được thì dừng, fetch và đọc, không reset.
3. Đọc STATE, BOARD, log mới hơn file này nếu có. Chọn một ID chưa có owner. Claim theo BOARD. Chưa được phép push thì nói chưa giữ chỗ.
4. Cài skill theo SKILL-FLOW. Thiếu `UpdateSkill` thì ghi `NOT_INSTALLED`. Không đi tìm token để thay.
5. Phiên onboarding dừng trước push, PR, merge, model trả phí, channel thật, và restart data thật. Tin Tin chốt task và quyền.
6. Sửa repo trên cloud agent, branch `<bot>/<topic>`, PR vào `i18n-vi`. Box chỉ chạy và kiểm. Merge khi Tin Tin viết "Duyệt merge", ghim head SHA, method merge. Chi tiết ở PROTOCOL và OPS.
