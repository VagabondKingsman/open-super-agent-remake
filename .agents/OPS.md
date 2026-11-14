# Vận hành OSA trên box Grok Bot

Cách cài, chạy và kiểm bản đã merge. Cài trên máy mới thì đọc [docs/vi/cai-dat-may-moi.md](../docs/vi/cai-dat-may-moi.md) trước. File này ghi phần riêng của box vận hành. Không ghi giá trị key, mật khẩu, cookie, email, mã máy Instabox hay hostname tailnet vào git hoặc chat. Chỉ ghi tên biến.

## Box vận hành hiện tại (10/11/2026)

| Mục | Giá trị |
|---|---|
| Checkout chạy server | `/workspace/open-super-agent`, nhánh local `deploy/audit-f1-f12` (`b8ca2c0`), cây trùng `5a1e0e7` (PR #41). Chưa ở `i18n-vi` |
| Process | `uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765`, pid 523005 lúc 22:20 10/11, PID trong `logs/osa.pid`, cổng trong `logs/osa.port` |
| Khởi động, dừng | `bash scripts/osa-start.sh`, `bash scripts/osa-stop.sh` trong checkout đó |
| DB | `data/osa.db` trong checkout. Kiểm bằng `ls -l /proc/<pid>/fd \| grep '\.db'` trước khi backup |
| Secret | nạp từ `.env` của checkout và kho secret của bot. Không in giá trị |
| Computer | Instabox, máy `docker-osar-test` (`backend: auto`, `INSTABOX_API_KEY` trong vault của OSA) |
| `task_timeout_s` | 7200 từ `settings.overrides` trong DB. `config.yaml` ghi 600, override thắng |
| Giữ VM thức | `computer.idle_pause_s: 2592000` trong `config.yaml`, chưa commit. `/workspace/instabox-keepalive/lease-keepalive.py` (pid 335522, log `lease.log`) gia hạn activity lease mỗi 3 phút. Trần `maxRunMinutes` 480 phút vẫn áp. Suspend/resume của script đang lỗi thiếu `Idempotency-Key` (BOARD OPEN-KEEPALIVE). Không tắt script, không để VM pause, không commit `config.yaml` |

Restart server chỉ khi Tin Tin yêu cầu, và backup DB trước. Việc sửa code làm trong worktree riêng, không làm trên checkout này (xem [HANDOFF](HANDOFF.md#cách-làm-việc-từ-10112026)).

## Kiểm như CI trên box

Chạy trong worktree, không trong checkout đang chạy server:

```bash
uv sync --locked
uv run python -m compileall -q osa
uv run python -c "import osa.server"
uv run python -m osa.catalog
uv run python -m osa.templates
uv run python -m osa.i18n
uv run python -m osa.skillpacks verify-sources
env -u DISPLAY CI=1 OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs
(cd web && npm ci && npm test && npx tsc --noEmit && npm run build)
git diff --check
```

Trên code của PR #41 (`5a1e0e7`): 853 passed, 1 skipped (`test_real_desktop`, chỉ macOS). Web `npm test` 36/36. `osa.i18n` thiếu 0. Box có `bwrap` 0.12.0, `xvfb-run`, Google Chrome, Node 24, uv 0.13.7. Box không có Docker, nên Docker build và compose là `NOT_CHECKED`. Đọc check-run CI cho phần đó.

Muốn chạy thử một bản cài mới song song mà không đụng server thật thì clone vào thư mục tạm, đặt `OSA_DATA_DIR` riêng, chạy uvicorn foreground ở cổng khác (ví dụ 8799), gỡ `INSTABOX_API_KEY` và các key provider khỏi môi trường của lệnh đó, tắt process khi xong.

## Khóa cấu hình mới (PR #37, #41)

Có mặc định trong code, có dòng comment trong `limits:` của `config.yaml`. Bỏ `#` để đổi:

| Khóa | Mặc định | Việc |
|---|---|---|
| `limits.stream_first_chunk_s` | 170 | chờ chunk đầu tối đa bao nhiêu giây. Nhỏ hơn 180 giây của Watchdog |
| `limits.stream_idle_s` | 120 | sau chunk đầu, hai chunk cách nhau quá số này thì đóng stream |
| `limits.stream_retries` | 1 | số lần gọi lại cùng lượt, chờ 2–5 giây trước mỗi lần |

Biến môi trường của script: `OSA_PORT` (mặc định 8765), `OSA_START_TIMEOUT` (giây chờ `/manifest.json`, mặc định 60), `OSA_STOP_TIMEOUT` (giây chờ process thoát, mặc định 20). Server luôn nghe `127.0.0.1`.

## Deploy và restart

Chỉ làm khi Tin Tin giao. Code đã merge vào `i18n-vi` hoặc là patch đã test trong worktree.

1. Backup DB bằng sqlite backup API (an toàn khi server đang chạy, có WAL), kiểm `integrity_check`, quyền 0600:

```bash
TS=$(date +%Y%m%d-%H%M%S)
.venv/bin/python - "$TS" <<'PY'
import sqlite3, sys
src = sqlite3.connect("file:data/osa.db?mode=ro", uri=True)
dst = sqlite3.connect(f"/workspace/osa-backups/osa.db.<tên>.{sys.argv[1]}")
src.backup(dst); print(dst.execute("pragma integrity_check").fetchone()[0])
PY
chmod 600 /workspace/osa-backups/osa.db.*.$TS
```

2. Giữ bản sửa `config.yaml`: `cp -p config.yaml /workspace/osa-backups/config.yaml.local.$TS && git diff config.yaml > /workspace/osa-backups/config.yaml.local.$TS.diff`.
3. Đổi code (mục dưới), `uv sync --locked`, `(cd web && npm run build)`. `osa/static/dist/` nằm ngoài git nên phải build lại.
4. `bash scripts/osa-stop.sh` (chờ process thoát, báo `stopped <pid> (port :8765)`), rồi `bash scripts/osa-start.sh` (chỉ báo `started` khi `/manifest.json` trả lời, lỗi thì in log và thoát 1).
5. Kiểm: `/manifest.json` 200, đăng nhập bằng mật khẩu (không in), `GET /api/bots/1/computer` là `instabox` `running`, `ps -p 335522` còn chạy, `grep idle_pause_s config.yaml` vẫn là 2592000, `git status --short` chỉ có `config.yaml`.

### Đưa checkout vận hành về i18n-vi

Checkout đang ở nhánh local `deploy/audit-f1-f12`, cây trùng `5a1e0e7`. Khi cần theo `i18n-vi`:

```bash
cd /workspace/open-super-agent
git fetch origin i18n-vi
git diff config.yaml > /workspace/osa-backups/config.yaml.local.$TS.diff   # bước 2 ở trên
git checkout -- config.yaml
git checkout -B i18n-vi origin/i18n-vi
git apply /workspace/osa-backups/config.yaml.local.$TS.diff
git status --short    # chỉ còn " M config.yaml"
```

Nhánh local `i18n-vi` đã có (lúc 22:20 10/11 ở `d9ae1d8`, sau origin 54 commit) và không worktree nào đang giữ nó, nên `-B` đặt lại nó về `origin/i18n-vi` là an toàn.

Nếu `git apply` báo xung đột (upstream sửa đúng dòng `idle_pause_s`) thì sửa tay dòng đó về 2592000. Code đổi thì restart theo bước 3–5. Chỉ đổi nhánh mà cây không đổi (như bây giờ) thì không cần restart.

## CI

`.github/workflows/ci.yml` chạy khi push vào `main` hoặc `i18n-vi` và trên mọi PR:

- backend: `uv sync --locked`, compile, import, catalog, templates, i18n, verify-sources, cài `bubblewrap` + `xvfb`, mở user namespace (`sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`), `OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs`.
- frontend: Node 22, `npm ci`, `npm test`, `npm run build` (đã gồm `tsc --noEmit`).
- docker: `docker compose config --quiet` cho cả hai file compose, build image app, smoke bằng `docker run` trên `127.0.0.1:8765`.

`.github/workflows/computer-image.yml` build image Computer khi `osa/computer/image/` đổi.

## Lịch sử: box chạy `c16e6bb` (07/11/2026)

Các mục dưới đây mô tả box chạy `c16e6bb` với provider Experiential và thư mục `/workspace/osa-run/`. Giữ lại để tra cứu migration chi phí và cách watchdog Tailscale từng chạy. Box hiện tại không dùng thư mục đó.

### Build web trước

Server ưu tiên `osa/static/dist/`. Thư mục này gitignore. Pull source không cập nhật bundle.

```bash
cd <worktree>/web && npm run build
```

Thiếu `dist/index.html` thì `osa/server.py` trả `osa/static/index.html`, trang tiếng Trung cũ. `/sw.js` lúc đó cũng có thể là trang đó với mã 200. Body phải có `OFFLINE_COPY`. Mã 200 một mình chưa đủ.

### Chạy

Script trong repo là `scripts/osa-start.sh`. Nó ghi PID và log dưới `OSA_DATA_DIR/logs` khi biến đó có, không thì `data/` và `logs/` trong checkout. Bind `127.0.0.1:8765`.

Box đang chạy `c16e6bb` không dùng script đó cho process chính. Process là `uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765`, log nối vào file log của thư mục runtime, watchdog kéo lại khi `/sw.js` hỏng. Lệnh khởi động từng gỡ các biến không thuộc provider đang dùng, để process không kế thừa key lạ:

`DEEPSEEK_API_KEY`, `OSA_VAULT_KEY`, `OSA_WEBHOOK_TOKEN`, `INSTABOX_API_KEY`.

Các biến cần có sẵn trong môi trường, lấy từ kho secret của bot, không viết giá trị vào lệnh:

| Tên | Việc |
|---|---|
| `OSA_CONFIG` | File YAML operator. Box đang trỏ `config.experiential.yaml` trong thư mục runtime. |
| `OSA_DATA_DIR` | Định chuyển DB và dữ liệu ra khỏi repo khi `memory.db` là đường tương đối. |
| `OSA_PASSWORD` | Bật trang đăng nhập. Bắt buộc trước khi có URL nào ngoài localhost. |
| `EXPERIENTIAL_API_KEY` | Key provider Experiential. |
| `ZRO_API_KEY` | Key provider Zro, bản rollback. |
| `OSA_ALLOWED_HOSTS` | Host thêm khi chưa có mật khẩu. Có mật khẩu thì mục này không nới Host. |
| `OSA_WEBHOOK_TOKEN` | Chỉ khi nhận webhook. Box đang chạy thì gỡ biến này. |
| `OSA_VAULT_KEY` | Khóa vault. Không in. |
| `OSA_AI_NATIVE_DEFAULTS` | `false` thì không reconcile skill mặc định. Không xóa skill đã cài. |
| `INSTABOX_API_KEY` | Bật Computer Instabox. Box đang chạy thì gỡ. |
| `OSA_BACKUP_PASSPHRASE` | Mật khẩu backup của app. Không in. |
| `OSA_DOTENV` | `0` = không đọc `.env`; một đường dẫn = đọc tệp đó. Mặc định đọc `.env` trong repo để lệnh chạy tay không rơi vào `data/` của repo. |
| `OSA_PROMPT_DUMP_KEEP` | Dump prompt giữ bao nhiêu tệp mới nhất (mặc định 500, `0` = không giới hạn). |
| `OSA_PROMPT_DUMP_MAX_MB` | Bỏ qua request lớn hơn ngưỡng này (mặc định 4 MB). |
| `OSA_BACKUP_DIR` | Chỗ `scripts/net-fast.sh` ghi bản sao lưu, mặc định `/home/boxes/osa-backups`. |

**Sao lưu để ngoài thư mục dữ liệu.** Bản sao lưu nằm trong `osa-data/` là tự bao chính nó: mỗi lần nén cả thư mục lại to thêm. Từ OSA-041 dùng `osa-backups/` cạnh `osa-data/`; tệp `.tar.gz` hay `net-backup-*` còn sót trong `osa-data/` thì chuyển ra. Riêng bản backup DB dùng sqlite backup API (mục dưới), không `cp` tệp `.db` đang mở.

`OSA_DATA_DIR` đã khai trên box là `/workspace/osa-run/data`. Thư mục đó không tồn tại. Process vẫn mở `/workspace/osa-run/osa.db`. `osa/config.py` `_db_path()` thấy `memory.db` tuyệt đối thì trả đúng đường đó. Đặt biến môi trường không chứng minh DB nằm trong data dir. OSA-015.

Từ OSA-022, Tin Tin chọn giữ nguyên đường DB. Khi gặp trường hợp này, lúc khởi động app in một dòng cảnh báo vào log, và mục Cài đặt → Sao lưu hiện đường DB thật kèm cảnh báo đỏ. Khi backup bằng tay, phải mang theo file DB ở đường tuyệt đối đó.

### Khối `security` từ v0.12

File config của box soạn theo v0.6.1 nên không có khối `security`. Thiếu khối này thì `osa/security.py` dùng mặc định `local_exec: true`, tức `exec: host`, `plugins: any`, `apps: any`: ai đăng nhập web được là chạy được lệnh trên box. Upstream khuyên máy chủ dùng `false`. Box chỉ mở trong tailnet và có mật khẩu, nhưng nên thêm vào file config trên box trước khi deploy bản 0.12:

```yaml
security:
  local_exec: false   # hoặc từng khóa: exec: sandbox, plugins: market, apps: market
```

`exec: sandbox` cần `bwrap` trong máy. Image Docker đã có. Box chạy uvicorn trực tiếp thì kiểm `command -v bwrap`. Đổi khối này là việc của operator, không commit file config.

Worktree box là checkout tách, detach tại `i18n-vi`. Không sửa code trên worktree rồi copy lên git. Sửa repo bằng PR.

### Provider

File config operator không có trong git. Khung dưới đây chỉ có URL công khai và tên biến. Model `:free` trên Experiential là mức $0 theo ghi chú phiên Kingfisher. Phiên OSA-014 không gọi API, nên giá trị $0 là `NOT_CHECKED` lại.

Experiential, bản đang chạy:

```yaml
providers:
  experiential:
    base_url: https://api.experientiallabs.ai/v1
    api_key_env: EXPERIENTIAL_API_KEY
roles:
  router:   {provider: experiential, model: deepseek-v4.1-flash:free}
  worker:   {provider: experiential, model: deepseek-v4.1-flash:free}
  reviewer: {provider: experiential, model: gpt-6-luna:free}
  filter:   {provider: experiential, model: gpt-6-luna:free}
```

Model tên `clef` trên provider này là model quyết định, không phải model chat. Đừng gán vào `roles`.

Zro là bản rollback, file config riêng trong cùng thư mục runtime:

```yaml
providers:
  zro:
    base_url: https://zro.moonmath.ai/v1
    api_key_env: ZRO_API_KEY
```

Key Zro là key có hạn mức. Hết hạn mức thì dừng. 402 và 429 hết quota không retry. 429 rate limit thì chờ `Retry-After`, trần `provider_retry_cap_s` (mặc định 120 giây).

`config.experiential.yaml` trên box vẫn để `pricing.currency` là ¥, `usd_rate` 7.1, và bảng giá tay theo CNY. Code trong `osa/prices.py` thấy nhãn CNY thì chia bảng tay cho hệ số đó rồi tính như USD. Model không có trong bảng lấy USD từ models.dev. App đang chạy với cách đọc này. Dọn file sang `$` và số USD là OSA-020, làm trên box, không commit YAML.

### Chi phí đã migrate trên DB đang mở

Một lần, lúc boot `c16e6bb`. Không chạy lại trong phiên docs.

- 103 dòng `llm_usage`.
- Tổng ¥0.18457 thành $0.02600.
- `settings.cost_unit`: `currency` USD, `legacy_cny_per_usd` 7.1, `repriced_models` 0, `divided_rows` 64.

`repriced_models` 0 nghĩa là không có dòng nào được tính lại từ bảng tay. 64 dòng khác 0 bị chia cho 7.1. Cờ `currency: USD` chặn lần chia thứ hai. Đặt `legacy_cny_per_usd: 1` chỉ khi một DB khác vốn đã lưu USD và chưa có cờ. DB này đã có cờ. Đừng chia lại.

### Tailscale

`tailscaled` chạy kiểu userspace trên box. Binary, socket, và script nằm trong thư mục runtime, không nằm trong repo. Tên gợi ý: `<run-dir>/tailscale/bin`, `<run-dir>/tailscale/state/tailscaled.sock`, `<run-dir>/tailscale/watchdog.sh`, `<run-dir>/tailscale/watchdog.log`.

`tailscale serve` chỉ trong tailnet, HTTPS trên node trỏ về `127.0.0.1:8765`. Funnel tắt. Tin Tin yêu cầu giữ tắt. Không bật Funnel, không mở tunnel công cộng. Cloudflare quick tunnel không chạy được từ box này theo phiên Kingfisher. Đó là giới hạn máy đó, không phải kết luận cho mọi mạng.

Không ghi hostname tailnet vào repo. URL có dạng `https://<node>.<tailnet>.ts.net`.

Egress của box cắt long-poll điều khiển Tailscale khoảng mỗi 2 phút, node chập chờn offline. Đây là giới hạn mạng box, không phải bug app. Chạy ổn trên máy khác là OSA-017.

Watchdog, chu kỳ 60 giây:

- `Self.Online` khác true thì khởi động lại `tailscaled`.
- `/sw.js` hỏng hai lần thì khởi động lại OSA.
- Lần đo cũ: process trở lại sau 140 giây. Deploy `c16e6bb`: tắt uvicorn rồi để watchdog kéo lại mất khoảng 2–3 phút. Cùng một cơ chế, hai lần đo. Phiên docs không đo lại.
- Dừng watchdog: `pkill -f watchdog.sh`. Trên box này script là file duy nhất khớp. Máy khác kiểm lệnh trước khi giết.
- Log: `watchdog.log` cạnh script.

### Điện thoại

Sau deploy, mở app một lần khi đang online, đóng hẳn tab hoặc PWA, rồi mở lại. Service worker mới lúc đó mới chiếm. Worker cũ giữ trang offline cũ, trước OSA-012 là tiếng Trung.

Trình duyệt của bot không đăng nhập được vào `127.0.0.1` hay URL tailnet. Ảnh UI sau login trên điện thoại là `NOT_CHECKED` cho đến khi Tin Tin thử. Viewport hay dùng khoảng 390px.

### Deploy sau khi merge (cách cũ, box `c16e6bb`)

Cách hiện tại ở mục [Deploy và restart](#deploy-và-restart). Làm trên worktree của box, sau khi PR đã vào `i18n-vi`. Không làm bước này từ phiên chỉ viết docs.

1. Tìm pid `uvicorn osa.server:app`.
2. Backup đúng file DB process đang mở, kèm `-wal` và `-shm` nếu có:

```bash
ls -l /proc/<pid>/fd | rg '\.db'
```

Trên box lúc chạy `c16e6bb`, fd là `/workspace/osa-run/osa.db`. Đừng copy `/workspace/osa-run/data` vì thư mục đó không có, và đừng suy DB từ `OSA_DATA_DIR`.
3. `git fetch` và checkout đúng SHA merge. Cây bẩn thì dừng. Không reset, không force.
4. `npm run build` trong `web/`.
5. Tắt uvicorn. Watchdog kéo process mới trong khoảng 2–3 phút. Đừng chạy thêm một uvicorn thứ hai khi port còn bị giữ.
6. Kiểm, chưa đăng nhập, `OSA_PASSWORD` đang bật:
   - `GET /` trả 303, `Location` chứa `/login`. Mã 303 này là redirect trong `osa/auth.py`.
   - `GET /login` không cookie trả 200, trang form. 303 trên `/login` chỉ khi đã có cookie hoặc chưa bật mật khẩu.
   - `GET /sw.js` trả 200 và body có `OFFLINE_COPY`.
7. Nhắc Tin Tin mở lại PWA như mục điện thoại.

Cụm "kiểm /login 303" trong ghi chú cũ nghĩa là redirect của trang được bảo vệ. Form 200 không phải deploy hỏng.

### Giới hạn box

- Mạng cắt Tailscale. Watchdog chỉ vá hiện tượng.
- Thiếu Docker thì Computer E2E là `NOT_CHECKED`. Không sửa app để giả có Docker.
- Không có bubblewrap thì ba test trong `tests/test_local_checks.py` SKIP. SKIP không phải PASS.
- Không gửi channel thật, không chạy model trả phí, không bật Funnel, khi chưa có câu duyệt đúng việc trong [PROTOCOL](PROTOCOL.md).
