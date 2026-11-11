# Bàn giao OSA · file đọc đầu cho bot mới

Đọc file này trước. Nó thay bộ nhớ chat của Kingfisher. Tài liệu không cấp quyền merge, chạy model trả phí, gửi channel, hay mở OSA ra ngoài tailnet.

Repo: `VagabondKingsman/open-super-agent-remake`. Base: `i18n-vi`. Upstream `kadaliao/open-super-agent` chỉ đọc. Giờ trong các file là **Asia/Saigon (UTC+7)**.

## Đọc theo thứ tự

1. File này.
2. [README](README.md), [RULES](RULES.md), [PERSONA](PERSONA.md), [PROTOCOL](PROTOCOL.md).
3. [STATE](STATE.md), [BOARD](BOARD.md), log mới nhất trong [log/](log/). Bỏ qua `_TEMPLATE.md`. STATE là snapshot. Fetch lại ref trước khi nhận việc.
4. [SKILL-FLOW](SKILL-FLOW.md). Cài bảy skill trong `skills-pack/ai-native/` và bridge [osa-dev](skills/osa-dev/SKILL.md). Đọc skill trước khi làm, không gọi tên rồi coi như đã nạp.
5. [ARCHITECTURE](ARCHITECTURE.md), [OPS](OPS.md) nếu sắp chạy box, [DECISIONS](DECISIONS.md). Cài máy mới thì đọc [docs/vi/cai-dat-may-moi.md](../docs/vi/cai-dat-may-moi.md).
6. [templates/](templates/) khi lập TIP, viết PR, hoặc bàn giao một task. `templates/HANDOFF.md` là mẫu một task. File này là bàn giao cả dự án.

[PROMPT](PROMPT.md) là đoạn Tin Tin dán vào bot mới. Sau khi đã đọc danh sách trên thì không cần đọc lại như quy trình.

## Head hiện tại

Đối chiếu 10/11/2026 22:20 Asia/Saigon: `origin/i18n-vi = 5a1e0e7`, merge [PR #41](https://github.com/VagabondKingsman/open-super-agent-remake/pull/41). Version `0.17.0`. CI trên PR #41 xanh cả ba job (backend, frontend, docker). Số test và trạng thái box ở [STATE](STATE.md). Phiên sau chạy `git fetch` và `git rev-parse origin/i18n-vi`. SHA mới hơn thì đọc log mới hơn.

`main` là default branch trên GitHub nhưng đứng ở `a30e3cc` (AUDIT-F11, Tin Tin quyết), tổ tiên cũ của `i18n-vi`, không có `.agents/` hay `tests/`. Clone bằng `git clone -b i18n-vi`. Cloud agent hay checkout `main` theo mặc định, phải chuyển sang `i18n-vi` trước khi làm.

Cài trên máy mới, cho người hay bot: [docs/vi/cai-dat-may-moi.md](../docs/vi/cai-dat-may-moi.md). Lệnh vận hành box ở [OPS](OPS.md).

## Cách làm việc từ 10/11/2026

Tin Tin chốt làm local trước rồi mới PR:

1. Sửa và test trên box, trong một worktree riêng: `git -C <checkout> worktree add <thư mục mới> -b <bot>/<topic> origin/i18n-vi`. Không sửa trực tiếp checkout đang chạy server.
2. Chạy đủ gate như CI (mục "Chạy test giống CI" trong hướng dẫn cài). Ghi số vào log.
3. Commit nhỏ, author `Tin Tin <tintin@users.noreply.github.com>`, rồi `git format-patch origin/i18n-vi..HEAD`. Box không `git push` được.
4. Cloud agent trên repo remake checkout `i18n-vi`, `git am` các patch, push branch, mở PR vào `i18n-vi`.
5. CI xanh và Tin Tin đồng ý thì merge (merge commit). Không force-push.
6. Deploy lên box chỉ khi Tin Tin giao: backup DB, đổi code theo [OPS](OPS.md#deploy-và-restart), restart bằng script, kiểm `/manifest.json`, đăng nhập, Computer.

Không bao giờ commit `config.yaml` của box vận hành. File đó có `computer.idle_pause_s: 2592000` chưa commit để giữ VM Instabox thức. Ở checkout đang chạy server: không stash, không `checkout -- .`. Chỉ đổi code ở đó theo đúng các bước trong OPS, giữ lại dòng `idle_pause_s`.

Skill Flow cho việc OSA: `osa-dev` → `ai-work-method` → `vibecode-kit` (debug 9 bước, QA 3 tầng). Văn bản tiếng Việt qua `unslop-vi`. Chi tiết ở [SKILL-FLOW](SKILL-FLOW.md).

## Đã merge

Giờ là `merged_at` đổi sang Asia/Saigon. `merged_by` trên API là VagabondKingsman, trừ PR #17 do Hoplite (`app/usehoplite`) merge theo câu duyệt của Thi Vo. Chi tiết và các câu "Chưa merge" cũ nằm trong STATE. Những câu đó là trạng thái lúc viết mục, bảng này mới hơn.

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
| [#16](https://github.com/VagabondKingsman/open-super-agent-remake/pull/16) | 21:14:45 | `3b02a80` | OSA-014 bàn giao `.agents/` cho bot mới. |
| [#17](https://github.com/VagabondKingsman/open-super-agent-remake/pull/17) | 14:25:33 09/11 | `d3a838e` | OSA-021 port upstream v0.12.0 (`d432c74`) lên remake. |
| [#18](https://github.com/VagabondKingsman/open-super-agent-remake/pull/18) | 18:16:57 09/11 | `b628fe4` | OSA-022: việc còn mở sau port, OSA-015, 007, 003, 008, 019. |
| [#19](https://github.com/VagabondKingsman/open-super-agent-remake/pull/19) | 19:29:21 09/11 | `1b0de69` | OSA-023 đồng bộ `.agents/` sau PR #18. |
| [#20](https://github.com/VagabondKingsman/open-super-agent-remake/pull/20) | 20:25:07 09/11 | `6c02c1b` | OSA-024 bridge Hoplite cho đủ bộ AI Native. |
| [#22](https://github.com/VagabondKingsman/open-super-agent-remake/pull/22) | 20:39:03 09/11 | `b9b1c2a` | OSA-019 `lang_flag` hiện trên trang Quan sát. |
| [#21](https://github.com/VagabondKingsman/open-super-agent-remake/pull/21) | 22:19:01 09/11 | `42475fd` | OSA-005 cứng hóa GitHub Actions, workflow build image computer. |
| [#23](https://github.com/VagabondKingsman/open-super-agent-remake/pull/23) | 22:19:16 09/11 | `bbf0ed5` | OSA-025 ba lỗi bảo mật High. |
| [#24](https://github.com/VagabondKingsman/open-super-agent-remake/pull/24) | 22:22:52 09/11 | `b3e5b65` | OSA-028 bảo mật Medium và L1. |
| [#25](https://github.com/VagabondKingsman/open-super-agent-remake/pull/25) | 22:26:20 09/11 | `254673c` | OSA-029 độ tin cậy: vòng nền, WebSocket backoff, TZ. |
| [#26](https://github.com/VagabondKingsman/open-super-agent-remake/pull/26) | 23:22:08 09/11 | `1466670` | OSA-030 đồng bộ `.agents/` sau #21, #23, #24, #25. |
| [#27](https://github.com/VagabondKingsman/open-super-agent-remake/pull/27) | 12:59:36 10/11 | `4512138` | OSA-031 port upstream v0.13.0–v0.17.0. Head `d97ad3c`. |
| [#28](https://github.com/VagabondKingsman/open-super-agent-remake/pull/28) | 13:09:02 10/11 | `aa1ab7e` | OSA-031 ghi `.agents/` sau khi #27 merge. Head `c9efd89`. |
| [#29](https://github.com/VagabondKingsman/open-super-agent-remake/pull/29) | 13:39:04 10/11 | `d9ae1d8` | OSA-032 README và docs người dùng cho v0.17.0. Head `e1d4399`. |
| [#30](https://github.com/VagabondKingsman/open-super-agent-remake/pull/30) | 13:52:29 10/11 | `c7c5321` | OSA-033 bàn giao `.agents/`. Giờ commit merge. |
| [#31](https://github.com/VagabondKingsman/open-super-agent-remake/pull/31) | 15:01:58 10/11 | `f8d48f3` | OSA-034 vỏ Android. Giờ commit merge. |
| [#32](https://github.com/VagabondKingsman/open-super-agent-remake/pull/32) | 15:40:21 10/11 | `26752c9` | OSA-035 Android crash. |
| [#33](https://github.com/VagabondKingsman/open-super-agent-remake/pull/33) | 15:49:27 10/11 | `4e146df` | OSA-036 nút Đổi server. |
| [#34](https://github.com/VagabondKingsman/open-super-agent-remake/pull/34) | 16:18:45 10/11 | `ac85f73` | OSA-037 trang nổi Android. |
| [#35](https://github.com/VagabondKingsman/open-super-agent-remake/pull/35) | 16:23:51 10/11 | `90d820c` | E2E-B1-B6: effort fallback, chặn dispatch bịa, reviewer, tự handoff, ảnh cả màn hình. Head `e5d9f5a`. Giờ commit merge. |
| [#36](https://github.com/VagabondKingsman/open-super-agent-remake/pull/36) | 17:08:40 10/11 | `7a0e674` | TIP-04b cửa sổ task tự phóng, handoff `.agents/`, README VI. Head `875a71d`. |
| [#37](https://github.com/VagabondKingsman/open-super-agent-remake/pull/37) | 20:15:33 10/11 | `0500666` | Stream treo hoặc rớt thì gọi lại cùng lượt (Nova #253). Head `1f5408a`. |
| [#38](https://github.com/VagabondKingsman/open-super-agent-remake/pull/38) | 20:30:03 10/11 | `e55d00a` | CI cài `bubblewrap`, 3 test sandbox chạy thật. Head `0cc7217`. |
| [#39](https://github.com/VagabondKingsman/open-super-agent-remake/pull/39) | 20:42:26 10/11 | `8c108c9` | CI chạy `test_real_chrome` dưới `xvfb`. Head `0aa79de`. |
| [#40](https://github.com/VagabondKingsman/open-super-agent-remake/pull/40) | 21:16:04 10/11 | `91b6cfb` | Deep audit cài máy mới, `docs/vi/cai-dat-may-moi.md`, `.agents/`. Head `f7307a1`. Giờ commit merge. |
| [#41](https://github.com/VagabondKingsman/open-super-agent-remake/pull/41) | 22:12:10 10/11 | `5a1e0e7` | Sửa AUDIT-F1–F13. Head `9bce42d`. Giờ commit merge. |

PR #1 đến #5 rơi vào đêm 06/11 UTC, tức sáng 07/11 giờ Sài Gòn. Từ PR #17, code trên `i18n-vi` là v0.12.0, có `desktop/` và `mobile/` trong cây nhưng không có workflow build. Box vẫn chạy bản cũ cho tới khi deploy theo OPS.

Việc đã vào code, rút từ log và từ code ở `c16e6bb`. Thay đổi từ PR #17 trở đi ghi ở cuối danh sách:

- VI mặc định, EN/ZH, Chinese-as-key. Chat cũ không tự dịch.
- Bảy skill AI Native cộng `ai-native-mentor` cài shared lúc startup. Opt-out bằng `skills.ai_native_defaults: false` hoặc `OSA_AI_NATIVE_DEFAULTS=false`.
- Heavy: một lượt một task, `min_drafts` 2, `concurrency` 1. 402 và 429 hết hạn mức thì dừng, không gọi reviewer. 429 rate limit thì chờ `Retry-After`.
- Prompt hệ thống và mô tả tool của OSA là tiếng Anh. `model_hint()` luôn gắn chỉ thị trả lời theo ngôn ngữ UI, mặc định vi. Nhãn draft là `=== Draft N ===`.
- Marker code còn đọc: `[附件]`, khóa `需要你做的事`, và regex quiet vẫn nhận `无新内容` / `没有新内容` cạnh `[nothing new]`. Đừng xóa các chuỗi này khi "dọn tiếng Trung".
- Template chọn khối theo thứ tự vi → en → zh từ PR #18. UI `zh` giữ nguồn Trung.
- Trang offline của service worker nằm trong `web/public/sw.js`, ngôn ngữ lấy từ Cache Storage `osa-lang`, thiếu thì tiếng Việt.
- Chi phí là USD. `settings.cost_unit` chặn lần chia thứ hai. Tab giới hạn vẫn là token, bước, giây.
- `OSA_DATA_DIR` chuyển DB, apps, workspace, log của `scripts/osa-start.sh` khi `memory.db` là đường tương đối. Đường tuyệt đối thì không. Từ PR #18, trường hợp này in cảnh báo lúc khởi động và hiện ở Cài đặt → Sao lưu (OSA-015, Tin Tin chọn cảnh báo, không đổi đường DB).
- PR #18: lời gọi model trực tiếp (filter routine, import memory, teach, plugin `llm.complete`) đi qua `providers.create_chat`, 402 và 429 hết hạn mức không retry. Frontend lazy-load, entry JS 69 kB. Reconcile skill pack chịu crash giữa chừng. `osa/langcheck.py` gắn cờ `lang_flag` khi trả lời phần lớn là chữ Hán mà UI là vi hoặc en, không chặn.
- PR #23–#25, áp dụng khi deploy:
  - Đăng nhập: mọi lần kiểm mật khẩu xếp một hàng chung.
  - Task nền trên computer Docker/Instabox phải được duyệt trước `computer_shell` và `computer_write_file`.
  - Container computer tạo mới có `no-new-privileges`, giới hạn pids, bỏ `NET_RAW`/`MKNOD`. Container `osa-computer` cũ phải `docker rm -f` để tạo lại.
  - `compose.yaml` không gắn `docker.sock`. Muốn dùng computer local thì thêm `compose.computer.yaml` (`COMPOSE_FILE` trong `.env`).
  - Nghe ngoài loopback mà không có `OSA_PASSWORD` thì từ chối khởi động (`OSA_ALLOW_NO_PASSWORD=1` để bỏ qua).
  - Webhook cũ `/hooks/<tên>` cần `OSA_WEBHOOK_TOKEN` khi đã có mật khẩu.
  - `fetch_url` ghim IP đã kiểm, tối đa 2 MB. Push chặn IP nội bộ.
  - TZ Docker mặc định là `Asia/Ho_Chi_Minh`.
- PR #37 và #41, stream model:
  - Chunk đầu chờ tối đa `limits.stream_first_chunk_s` (170 giây). Sau chunk đầu, hai chunk cách nhau quá `limits.stream_idle_s` (120 giây) thì đóng stream. Cả hai phải nhỏ hơn 3 phút của Watchdog.
  - Stream treo, rớt kết nối, 5xx, "at capacity" thì gọi lại cùng lượt `limits.stream_retries` lần (mặc định 1), chờ 2–5 giây trước mỗi lần. Hết quota và request sai không gọi lại. Router chỉ gọi lại khi UI chưa nhận chữ nào, và gửi `reset` để UI xóa phần thinking đã hiện.
  - Usage của lượt hỏng vẫn được ghi (ước tính khi không có usage, `estimated=1`).
  - Ba khóa trên có dòng comment trong `limits:` của `config.yaml`.
- PR #41, khác: cửa sổ task phóng tới màn hình thật và không tràn ra ngoài; Chrome trên Linux không màn hình báo lỗi ngay với gợi ý `xvfb-run -a`; `scripts/osa-start.sh` nhận `OSA_PORT` và chờ `/manifest.json`; file backup quyền 0600; CLI backup và cảnh báo `OSA_PASSWORD` có vi/en; `docs/docker.md` tiếng Việt.

Live OSA-011 đã có trong repo: [bằng chứng](evidence/osa-011-live-test/LIVE-TEST.md), head lúc chạy `f83e3cb`, Experiential, mọi model đuôi `:free`, cost ghi 0. Bốn lượt chat (vi, en, single, heavy) đều CJK 0. Báo cáo để trạng thái PARTIAL. 14 dòng usage, 116.236 token (`cache_hit` + `cache_miss` + `output`), vượt mục tiêu khoảng 100.000 nên không chạy routine. Guard harness cộng cột `input` thay vì `cache_hit` + `cache_miss`, phải sửa trước đợt sau. Harness dừng websocket vì regex 402 khớp offset 14025. Log server không có 402. `results.json` còn heavy `running` ở 60,38 giây. `summary.json` ghi heavy PASS 124 giây. Thư mục `raw/` không đưa vào git. Câu `NOT_CHECKED` trong log OSA-011 là lời lúc mở PR #13.

## Còn lại

OSA-040 (chưa merge, branch `cursor/android-connect-crash-efeb`): app Android văng lúc nối server. Nguyên nhân thấy trên demo Linux là `add_capability` panic vì chưa có manifest app, khóa ACL bị độc, process chết. Hàng đợi wry 8 chỗ vẫn không được gọi `navigate`. Điện thoại thật chưa chạy bản này.

Code trên `i18n-vi` là v0.17.0. So với upstream `ec02547` không thiếu file trong `osa/`, `web/`, `tests/`, `desktop/`, `mobile/`. Khác biệt còn lại là của remake: tiếng Việt mặc định, prompt tiếng Anh, chi phí USD, AI Native, và các sửa bảo mật đã merge tới PR #25. Không có plugin. Không có trang Chi phí. `desktop/` và `mobile/` có trong cây, remake không build. Workflow đóng gói app Mac của upstream không có.

Chưa kiểm trên máy thật: Docker Computer E2E, app Mac, điện thoại sau login. Đó là OSA-002 và OSA-007, chưa phải code thiếu.

Deep audit 10/11 ([log](log/2026-11-10-deep-audit-install.md)) tìm AUDIT-F1 tới F12. Live test lúc sửa tìm thêm F13. Tất cả đã sửa trong PR #41 ([log](log/2026-11-10-audit-fixes.md)), trừ F11 là việc của Tin Tin trên GitHub. Mục còn mở sau PR #41 là các dòng `OPEN-*` trên [BOARD](BOARD.md): đường gọi lại stream chưa xảy ra live, thông báo "0 giây", `docs/docker.md` sẽ xung đột khi merge upstream, các mục `NOT_CHECKED`, và script giữ VM thiếu `Idempotency-Key`.

Ưu tiên và AC đầy đủ hơn ở [BOARD](BOARD.md). Bảng này là thứ tự nên hỏi Tin Tin. Chưa có câu giao thì chưa làm.

| ID | Ưu tiên | Việc | AC gợi ý | Chưa kiểm |
|---|---|---|---|---|
| OSA-015 | Xong | DB không đi theo `OSA_DATA_DIR` khi `memory.db` là đường tuyệt đối | Tin Tin chọn cảnh báo, không đổi đường DB. Đã vào PR #18. | Chưa thấy dòng cảnh báo trên box thật. |
| OSA-020 | P1 | Dọn `config.experiential.yaml` trên box sang USD | `pricing.currency` là `$`. Bảng tay là số USD hoặc bỏ hẳn. Khởi động lại không chia `llm_usage` lần hai. Không commit file config. | File trên box vẫn để ¥. Code đọc và chia đúng. |
| OSA-019 | P1 | Phần ngôn ngữ còn lại | Người bản ngữ đọc lại khối `vi:` của template. `lang_flag` đã hiện trên Quan sát (PR #22). | Bản `vi:` chưa có người đọc. |
| OSA-016 | P1 | Chạy thử routine trên data được phép | Một lịch, filter quiet, không gửi channel thật, có log lệnh. | `NOT_CHECKED` |
| OSA-007 | P1 | UI khoảng 390px sau đăng nhập trên điện thoại thật | Ma trận vi/en/zh × 375/768/1440 trên preview sandbox đã PASS ở PR #18. | Bot không mở được tailnet sau login. Tin Tin thử trên điện thoại. |
| OSA-017 | P1 | Chạy OSA bằng Docker trên máy Tin Tin hoặc VPS | Hết phụ thuộc watchdog và mạng box. Computer E2E nằm ở OSA-002, không gộp vào task này. | Chưa chọn máy. |
| OSA-001 | P2 | Router giao việc thật cho Worker, Worker tự nạp skill | Trace đủ, cleanup. Cần duyệt model và cap trước lượt trả phí. | Worker live chưa nghiệm thu. |
| OSA-002 | P2 | Computer E2E trên máy có Docker | Build app, VNC/CDP, cửa sổ song song, takeover, upload. HTTP 200 không tính. | Box thường thiếu Docker. |
| OSA-018 | P2 | Mẫu A/B Zro và DeepSeek còn lại | Đủ bài đã chốt, cap, điều kiện dừng. | Cần duyệt từng đợt. |
| OSA-003 | Xong | Tách bundle frontend | Entry JS 1.364 kB → 69 kB, hết cảnh báo chunk. Đã vào PR #18. | Không. |
| OSA-005 | Xong | Rà GitHub Actions | Đã cứng hóa ở PR #21. | Không. |
| OSA-008 | Xong | Reconcile khi crash giữa file và SQLite | 19 ca bơm lỗi. Đã vào PR #18. | Không. |

Deploy `c16e6bb` trên box, Tin Tin báo, phiên docs không mở DB:

- Process giữ `/workspace/osa-run/osa.db`. Thư mục `/workspace/osa-run/data` không tồn tại. Đây là bằng chứng sống của OSA-015. Đường dẫn này là của box đó. Máy khác phải xem fd, đừng chép đường dẫn.
- Migration OSA-013 trên DB đó: 103 dòng usage, tổng ¥0.18457 thành $0.02600. Cờ `settings.cost_unit`: `currency` USD, `legacy_cny_per_usd` 7.1, `repriced_models` 0, `divided_rows` 64. Code còn ghi khóa `rows`. Bản báo không có khóa đó. 103 trừ 64 bằng 39 dòng `cost = 0` không vào vòng chia, suy từ code, không đếm lại trên DB.
- `repriced_models` 0 khớp model Experiential không nằm trong bảng tay `deepseek-flash` / `deepseek-v4-pro`: các dòng khác 0 bị chia 7.1, không bị tính lại theo giá niêm yết.
- File operator `config.experiential.yaml` vẫn khai `currency` ¥, `usd_rate` 7.1, và bảng tay CNY. `manual_table_is_cny()` chia bảng đó lúc đọc. Việc dọn file là OSA-020.

`legacy_cny_per_usd: 1` chỉ khi số cũ đã là USD. DB box này đã chia một lần. Lần sau cờ USD giữ nguyên số.

Audit 09/11, phần còn lại chưa giao (nhóm C): L2 vault key từ passphrase dùng scrypt (cần migrate), L3 thu hồi session, L5 lọc IP nội bộ cho app MCP HTTP/SSE, R2 bật WAL cho SQLite. Ngoài ra `sources/_util.get` và `unfurl` vẫn kiểm IP rồi mới kết nối, có thể chuyển sang `tools.pin()`.

## Computer Instabox trên box vận hành

- `computer.backend: auto` chọn Instabox khi có khóa Instabox: nhập trên panel (mã hóa vào vault) hoặc `INSTABOX_API_KEY` trong môi trường. Không có khóa thì dùng Docker. Trong app desktop thì dùng host.
- Màn hình VM đọc bằng `xdpyinfo`. Cỡ màn hình đổi theo người xem VNC: sáng 10/11 là 1920 × 1080, tối 10/11 là 661 × 1619. Cửa sổ task phóng tới `computer.width` × `computer.height` (1280 × 800), nhưng không quá màn hình thật (PR #41).
- `GET /shot` trả 409 trên Instabox vì panel dùng live view. Đây không phải lỗi mới.
- VM tự tạm dừng sau `computer.idle_pause_s` giây không dùng. Box vận hành đặt số lớn trong `config.yaml` local và chạy script giữ VM thức. Đừng commit giá trị đó. Script và đường dẫn là của box đó, máy khác tự cấu hình.
- Script đó gia hạn lease hoạt động của Instabox (TTL 600 giây) theo chu kỳ. Đừng tắt nó và đừng để VM ở trạng thái pause. Instabox vẫn áp trần `maxRunMinutes` (480 phút lúc kiểm 10/11) cho mỗi lượt chạy. Hết trần thì VM dừng dù lease còn. Script định tự suspend rồi resume trước mốc đó để tránh cooldown, nhưng tối 10/11 cả hai lệnh trả 400 vì thiếu header `Idempotency-Key`, nên VM vào cooldown 5 phút (OPEN-KEEPALIVE). Sau cooldown, `POST /api/bots/<id>/computer/start` của OSA đánh thức lại (đã kiểm 22:19 10/11: trả 200, `running`).
- Gói miễn phí chỉ có một máy. Đừng thử Instabox từ một bản cài thứ hai bằng cùng khóa khi box vận hành đang dùng.
- Không ghi khóa, mật khẩu đăng nhập OSA, link VNC hay link remote của VM vào repo hoặc log.

## Bước đầu phiên sau

1. Ack với Tin Tin. Nói đã đọc HANDOFF, head đang thấy, và việc định hỏi. Bot khác Kingfisher thì hỏi prefix. Giữ cách nói trong PERSONA.
2. `git status --short`. Cây sạch thì `git switch i18n-vi` và `git pull --ff-only origin i18n-vi`, rồi `git rev-parse HEAD`. Cây bẩn hoặc pull không tua được thì dừng, fetch và đọc, không reset. Trên box vận hành, checkout đang chạy server luôn bẩn vì `config.yaml`: chỉ `git fetch` ở đó, làm việc trong worktree.
3. Đọc STATE, BOARD, log mới hơn file này nếu có. Chọn một ID chưa có owner. Claim theo BOARD. Chưa được phép push thì nói chưa giữ chỗ.
4. Cài skill theo SKILL-FLOW. Thiếu `UpdateSkill` thì ghi `NOT_INSTALLED`. Không đi tìm token để thay.
5. Phiên onboarding dừng trước push, PR, merge, model trả phí, channel thật, và restart data thật. Tin Tin chốt task và quyền.
6. Sửa theo mục "Cách làm việc từ 10/11/2026" ở trên. Tóm tắt là worktree trên box, test như CI, `format-patch`, cloud agent `git am` rồi mở PR vào `i18n-vi`. Merge khi Tin Tin đồng ý cho đúng PR, ghim head SHA, method merge. Chi tiết ở PROTOCOL và OPS.
