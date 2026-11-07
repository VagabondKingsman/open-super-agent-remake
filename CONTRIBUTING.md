# Đóng góp cho OSA remake

Hướng dẫn này dành cho người và bot làm việc trên [VagabondKingsman/open-super-agent-remake](https://github.com/VagabondKingsman/open-super-agent-remake). Bản tiếng Trung trước đây là CONTRIBUTING của upstream `kadaliao/open-super-agent`. Các bước upstream (tạo nhánh từ `main`, cài template rồi cho lịch chạy một lần) không dùng trên remake. Chúng được gọi tên ở [mục cuối](#huong-dan-upstream).

File này không cấp quyền push, merge, gửi tin channel, hay gọi LLM trả phí.

## Đọc trước khi sửa

Bắt đầu tại [.agents/README.md](.agents/README.md). Trước khi ghi file, đọc theo thứ tự sau:

1. [.agents/RULES.md](.agents/RULES.md) và [.agents/PERSONA.md](.agents/PERSONA.md)
2. [.agents/STATE.md](.agents/STATE.md), [.agents/BOARD.md](.agents/BOARD.md), và log mới nhất trong [.agents/log/](.agents/log/) (bỏ qua `_TEMPLATE.md`)
3. [.agents/SKILL-FLOW.md](.agents/SKILL-FLOW.md), [.agents/ARCHITECTURE.md](.agents/ARCHITECTURE.md), [.agents/DECISIONS.md](.agents/DECISIONS.md)

[AGENTS.md](AGENTS.md) chỉ là lối vào ngắn ở root. Skill Flow cho việc code và tài liệu: `osa-dev` → `ai-work-method` → `vibecode-kit`, thêm `unslop-vi` khi viết tiếng Việt và `unslop` khi viết tiếng Anh.

Mẫu: [TIP](.agents/templates/TIP.md), [VERIFY REPORT](.agents/templates/VERIFY-REPORT.md), [PR](.agents/templates/PR.md), [log](.agents/log/_TEMPLATE.md).

## Nhánh, PR và merge

- Chỉ push và mở PR tới `https://github.com/VagabondKingsman/open-super-agent-remake`.
- Nhánh tích hợp là `i18n-vi`. Tạo branch làm việc `<bot>/<topic>` từ `i18n-vi` đã cập nhật, ví dụ `grok-bot/contributing-bots`. Mọi PR target `i18n-vi`.
- `kadaliao/open-super-agent` chỉ để đọc và fetch. Không push, không mở PR, không comment thay mặt dự án ở upstream.
- Không force-push. Không `reset --hard`, không viết lại lịch sử đã công bố, không xóa nhánh hay đổi remote để chữa lỗi non-fast-forward.
- Không đẩy thẳng vào `main` và không tự đồng bộ `main`.
- Merge do Tin Tin, hoặc một bot có approval rõ cho đúng PR đó. Kiểm checks, diff và head SHA trước khi merge. GO kỹ thuật không phải quyền merge.

## Nhận task

Làm theo mục Claim protocol trong [.agents/BOARD.md](.agents/BOARD.md):

1. Pull hoặc fetch `i18n-vi`, đọc bảng và các PR đang mở. Chọn task chưa có owner. Dùng ID cố định trên BOARD.
2. Sau khi được duyệt publish, mở một PR claim nhỏ, sửa đúng dòng: `ID / owner bot / branch <bot>/<topic> / scope / claimed_at Asia/Saigon / PR link khi có`. Việc nhỏ ghi claim trong PR thực thi.
3. Claim chỉ tính là đã nhận khi PR claim đã merge, hoặc Tin Tin xác nhận owner rõ. PR đang mở là tín hiệu phối hợp, không phải khóa phân tán. Kiểm lại ngay trước BUILD. Hai claim trùng thì dừng phần chồng và để Tin Tin hoặc owner thống nhất. Không giành task bằng force-push.
4. Nếu chưa được phép PR hoặc push, soạn bản claim nháp và nói rõ chưa giữ chỗ. Không tự công bố.
5. Cuối phiên ghi tiến độ, blocker và bước tiếp. Nghỉ hoặc bỏ việc thì trả task về backlog, kèm lý do, và giữ log. Không tự lấy owner của người khác vì quá hạn khi chưa thống nhất.
6. PR gắn task ID, TIP, VERIFY và log. Sau khi merge, chuyển task sang Done và cập nhật STATE. Chưa merge thì ghi PR-ready. Không đánh Done public.

Mỗi PR cập nhật STATE, BOARD và thêm `.agents/log/YYYY-MM-DD-<bot>.md`. Giờ dùng Asia/Saigon (UTC+7).

## Test cô lập

Không có biến môi trường nào trỏ cả thư mục dữ liệu OSA. Đường dẫn SQLite là `memory.db` trong file config, ghép với root repo (`osa/memory.py`). Cách cô lập duy nhất là `OSA_CONFIG` trỏ tới một YAML có `memory.db` nằm trong thư mục tạm, và phải gán biến này trước khi import OSA. Import `osa.server`, `osa.memory` hoặc `osa.skillpacks` mở DB ngay lúc nạp module.

`tests/conftest.py` làm đúng việc đó. File này tạo thư mục tạm, ghi đè config, đặt `OSA_CONFIG`, gỡ một số biến môi trường, rồi mới import. Bản ghi đè là:

- `memory.db`: file trong thư mục tạm
- `computer.enabled`: `false`, `computer.backend`: `local`
- `triggers`: `[]`
- `mcp_servers`: `{}`
- `embedding.provider` và `embedding.model`: chuỗi rỗng
- gỡ `OSA_VAULT_KEY`, `INSTABOX_API_KEY`, `OSA_PASSWORD`, `OSA_WEBHOOK_TOKEN`, `DEEPSEEK_API_KEY`

Không có khóa `channels` trong `config.yaml`, và conftest không ghi `channels: {}`. Kết nối channel là hàng trong bảng SQLite `channels`. DB tạm mới không có hàng nào, nên không có channel để nối. Copy `data/osa.db` sẽ mang theo channel, routine và bot thật. Đừng làm vậy, và đừng sửa hay xóa bot hoặc routine thật để dọn test.

`config.yaml` mặc định có trigger webhook GitHub `enabled: true`. Lần đầu tiên process khởi động, `routines.import_legacy` chép các trigger đó vào DB. Config tạm phải đặt `triggers: []`, nếu không DB tạm vẫn nhận routine webhook đó. Đừng kích hoạt nó.

`OSA_COMPUTER_DATA` chỉ đổi thư mục Computer dùng chung (`osa/computer/local.py`). Nó không đổi DB.

`scripts/osa-start.sh` không phải môi trường test. Script luôn `cd` về root repo, tạo `logs/` và `data/`, source `.env` nếu file đó có, rồi chạy uvicorn không gắn config tạm. DB mặc định là `data/osa.db`. Đừng dùng script này để xem thử server có lên không.

Server không có chế độ FakeLLM. `providers.client` luôn tạo client OpenAI thật. `FakeLLM` chỉ có trong `tests/fakellm.py` và fixture `llm` của pytest. Đừng gọi model trả phí để kiểm tra một PR.

Khởi động server (`lifespan` trong `osa/server.py`) chạy `prices.loop()`. Vòng đó tải `https://models.dev/api.json` (hoặc `pricing.source` nếu có) khi file `model-prices.json` cạnh DB thiếu hoặc cũ hơn một ngày, rồi ghi file đó. Đây là catalog công khai, không phải lượt LLM trả phí, nhưng vẫn là request ra mạng. Pytest không cần bật server. Đừng bật server để kiểm tra tài liệu.

Không có route `/health`. `GET /` đi vào fallback SPA `/{path:path}` và trả `index.html` (hoặc trang tĩnh cũ nếu chưa build). `GET /health` cũng rơi vào fallback đó, không phải endpoint sức khỏe. `GET /api/status` có thật và trả trạng thái MCP cùng danh sách routine.

Không đặt `OSA_PASSWORD` thì `auth.enabled()` là false: UI không yêu cầu đăng nhập. `osa/server.py` in cảnh báo lúc startup. Chỉ chấp nhận điều này khi cổng nằm trên `127.0.0.1`. `scripts/osa-start.sh` bind `127.0.0.1:8765`. Đừng publish cổng đó, và đừng mở VNC, CDP hay tunnel.

[docs/development.md](docs/development.md) vẫn là ghi chú upstream tiếng Trung. Mục sao chép `data/osa.db` rồi tắt channel trong bản copy không phải quy trình remake. Test tự động dùng DB tạm và model giả như trên.

## Lệnh kiểm tra

Chạy từ root repo. Python từ 3.11, `uv`, Node theo lockfile Vite (`^20.19.0 || >=22.12.0`). Không commit `osa/static/dist/`.

```bash
uv sync --locked
uv run python -m osa.i18n
uv run pytest -q -ra
uv run python -m osa.skillpacks verify-sources
(cd web && npm ci && npm test && npm run build)
git diff --check
```

`uv run python -m osa.i18n` không mở DB. Nó báo khóa EN/VI thiếu hoặc thừa, placeholder lệch, và câu tiếng Trung trên frontend chưa bọc `t()`.

`pytest` dùng temp DB và FakeLLM qua conftest. Ghi số passed, failed và skipped. Thiếu bubblewrap thì ba test trong `tests/test_local_checks.py` SKIP. SKIP không phải PASS. Không bỏ assertion cũ để suite xanh.

`verify-sources` đối chiếu SHA-256 của `skills-pack/ai-native/`. Lệnh này import `osa.memory`, nên khi chạy tay hãy đặt `OSA_CONFIG` tạm trước. Không gọi `defaults` hoặc `install` vào DB thật chỉ để kiểm tra tài liệu.

Đổi runtime, UI, i18n, hoặc một file ở root ngoài `.agents/` thì chạy i18n, pytest và frontend tests. Build khi đụng UI hoặc trước handoff phát hành. Ghi command, exit code và số test. Vite có thể cảnh báo chunk JS lớn hơn 500 kB. Cảnh báo đó không phải build fail. Trên base `3c08269` chunk này khoảng 1,15 MB. Số đo của từng phiên nằm trong log, không phải ngưỡng cứng.

`uv run python -m osa.catalog` kiểm manifest ứng dụng và không mở SQLite. `uv run python -m osa.templates` kiểm YAML template, không cài template và không chạy routine. Import module vẫn mở DB, nên đặt `OSA_CONFIG` tạm trước. Không cài template lên DB thật và không cho lịch chạy.

Thiếu Docker thì Computer E2E là `NOT_CHECKED`. API trả `docker_missing` là kết quả đúng, không sửa app để giả có Docker. Không gửi tin channel thật, không bắn webhook ra ngoài, không tạo lịch có tác động ngoài.

## Cách viết và những thay đổi không nhận

- Giữ tiếng Việt mặc định. English và 中文 vẫn chạy. Khóa i18n là câu tiếng Trung. Bản dịch ở `osa/locales/en.json`, `osa/locales/vi.json`, `web/src/locales/en.json` và `web/src/locales/vi.json`. Giữ placeholder. Không đưa i18next cũ trở lại. Xem [docs/i18n.md](docs/i18n.md).
- Python ưu tiên thư viện chuẩn, hàm ngắn. Comment nói lý do.
- Frontend dùng React function component. State ở `web/src/store.ts`. Style ở `styles.css`.
- Commit theo [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
- Một PR một việc. Đổi giao diện thì kèm ảnh đã làm sạch. Đổi hành vi Bot thì kèm hội thoại từ FakeLLM hoặc test, không phải kênh thật.
- Thay đổi người dùng thấy trên sản phẩm thì cân nhắc `CHANGELOG.md`. Sửa hướng dẫn cộng tác thì không bắt buộc một dòng changelog.
- Không nhận bản vá vòng captcha hoặc kiểm tra người-máy. Bước đó để người dùng tiếp quản. [docs/apps.md](docs/apps.md) và [docs/roadmap.md](docs/roadmap.md) trỏ về quy tắc này.
- Không ghi secret vào code hoặc config được track. Không commit `.env`, DB, backup, profile trình duyệt, trace riêng, hay link session.

## Hướng dẫn upstream, không dùng trên remake

<a id="huong-dan-upstream"></a>

Các việc sau nằm trong CONTRIBUTING upstream. Trên remake, làm cột bên phải.

| Việc upstream yêu cầu | Trên remake |
|---|---|
| Tạo nhánh từ `main`, PR vào `main` | Tạo `<bot>/<topic>` từ `i18n-vi`, PR vào `i18n-vi`. Không đẩy `main`. |
| Thêm template bằng cách cài trên máy rồi cho lịch chạy một lần | `uv run python -m osa.templates` trên DB tạm. Không bật routine hay channel thật khi chưa có approval riêng. |
| UI chỉ tiếng Trung và tiếng Anh, chỉ kiểm `en.json` | Giữ tiếng Việt mặc định và `vi.json`, cùng `en.json`. Khóa vẫn là tiếng Trung. |
| Sao chép `data/osa.db` để thử tay, như [docs/development.md](docs/development.md) | Dùng `OSA_CONFIG` và DB tạm. Không copy DB thật. |

Port commit upstream theo [docs/cap-nhat-tu-upstream.md](docs/cap-nhat-tu-upstream.md). Không mở PR lên `kadaliao/open-super-agent`.

## Trước khi mở PR

Dùng [.github/pull_request_template.md](.github/pull_request_template.md) và [.agents/templates/PR.md](.agents/templates/PR.md). Ghi TIP, từng AC, lệnh đã chạy, và phần chưa chạy (`NOT_CHECKED`). `git diff --check` phải sạch. Quét diff tìm secret và PII, rồi đọc lại các mẫu trùng, trước khi commit.

CI nằm ở [.github/workflows/ci.yml](.github/workflows/ci.yml): compile và import, catalog, templates, i18n, pytest, frontend test và build, cộng job Docker image. Push trong workflow hiện chỉ ghi nhánh `main`. PR không giới hạn nhánh. Chưa đọc check-run thì không kết luận CI remote xanh. Job Docker smoke không thay Computer E2E.
