# Cài OSA remake trên máy mới

Tài liệu này là nguồn chính để cài Open Super Agent remake (OSAR) từ đầu. Tài liệu gồm cách chạy server, chạy test giống CI, bật Computer và nâng cấp bản cũ. README, [Hướng dẫn tiếng Việt](../huong-dan-vi.md) và CONTRIBUTING chỉ tóm tắt rồi trỏ về đây.

Bản được kiểm là `i18n-vi` tại `8c108c9` (merge PR #39), ngày 10/11/2026, giờ Asia/Saigon (UTC+7). Mỗi lệnh có ghi một trong ba nhãn:

- **Đã chạy.** Lệnh đã chạy trên bản này và có kết quả ghi trong `.agents/log/2026-11-10-deep-audit-install.md`.
- **CI.** Lệnh chạy trên GitHub Actions (Ubuntu 24.04) ở run `42826978455`, không chạy trên máy kiểm.
- **Chưa kiểm.** Lệnh lấy từ tài liệu của công cụ, chưa ai chạy trên máy sạch. Đọc kỹ trước khi dùng.

Máy kiểm là Debian 13, Python 3.13.5, uv 0.13.7, Node 24.22.1, bubblewrap 0.12.0, Google Chrome, không có Docker.

## 1. Cần gì

| Thành phần | Bắt buộc khi | Ghi chú |
|---|---|---|
| Python 3.11 trở lên | luôn luôn | `pyproject.toml` ghi `>=3.11`. uv tự chọn bản có sẵn trên máy |
| `uv` | luôn luôn | cài và khóa thư viện Python theo `uv.lock` |
| Node `^20.19.0` hoặc `>=22.12.0`, kèm npm | build giao diện web | CI dùng Node 22. Máy kiểm dùng Node 24 vẫn build được |
| `git` | luôn luôn | cũng dùng cho `inspect_repo` / `check_patch` |
| `bubblewrap` (`bwrap`), `prlimit` (gói `util-linux`), `ps` (gói `procps`) | `run_code`, `quick_code`, `inspect_repo`, `check_patch` trên Linux | thiếu thì OSA báo BLOCKED, không chạy thẳng trên máy. 3 test sandbox SKIP |
| Google Chrome hoặc Chromium | Computer kiểu "Chrome trên máy này" và `test_real_chrome` | Linux không có màn hình cần thêm `xvfb` |
| Docker Engine hoặc Docker Desktop | Computer kiểu "Docker trên máy này", hoặc chạy bằng Docker Compose | không có Docker vẫn dùng được UI, API và việc không cần desktop |
| Khóa Instabox | Computer kiểu "Instabox" | nhập trên panel Computer, hoặc đặt `INSTABOX_API_KEY` |

### Ubuntu và Debian

**Chưa kiểm trên máy sạch.** Tên gói lấy từ workflow CI và Dockerfile:

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends git bubblewrap util-linux procps xvfb
```

Từ Ubuntu 24.04, AppArmor chặn user namespace của user thường, nên `bwrap` báo lỗi namespace. CI mở lại bằng lệnh dưới (**CI**). Lệnh này có hiệu lực tới lần khởi động lại máy. Muốn giữ lâu dài thì ghi vào một file trong `/etc/sysctl.d/`.

```bash
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
```

Debian cũ có thể cần `sudo sysctl -w kernel.unprivileged_userns_clone=1` (**chưa kiểm**). Debian 13 trên máy kiểm không cần.

Kiểm sandbox (**Đã chạy**, exit 0):

```bash
bwrap --unshare-all --die-with-parent --ro-bind / / true
```

Cài uv và Node theo trang chính thức của từng công cụ (<https://docs.astral.sh/uv/>, <https://nodejs.org/>) hoặc qua `nvm`. Tài liệu này không chép lệnh cài vì chưa chạy chúng trên máy sạch.

Với Chrome, cài gói `google-chrome-stable` từ Google, hoặc `chromium` của bản phân phối. OSA tìm lần lượt `google-chrome`, `google-chrome-stable`, `chromium`, `chromium-browser`, `microsoft-edge` trên PATH. Đặt `computer.chrome_path` khi Chrome nằm chỗ khác.

### macOS

**Chưa kiểm.** Cài Python, uv, Node bằng Homebrew hoặc bộ cài chính thức. macOS không có `bwrap`. OSA dùng `sandbox-exec` có sẵn của hệ thống cho `run_code`. Ba test trong `tests/test_local_checks.py` chỉ chạy trên Linux nên sẽ SKIP. Test `test_real_desktop` chỉ chạy trên macOS khi đặt `OSA_TEST_DESKTOP=1`, và nó điều khiển chuột, bàn phím thật.

## 2. Lấy source

**Đã chạy.** Nhánh mặc định trên GitHub là `main`, nhưng `main` đứng ở `a30e3cc`, một bản rất cũ không có `.agents/` hay `tests/`. Luôn lấy `i18n-vi`:

```bash
git clone -b i18n-vi https://github.com/VagabondKingsman/open-super-agent-remake.git
cd open-super-agent-remake
git rev-parse --short HEAD
```

Clone từ repo remake, không clone từ upstream `kadaliao/open-super-agent`.

## 3. Cài thư viện và build web

**Đã chạy** trên bản clone mới: `uv sync --locked` exit 0; `npm ci` không có lỗ hổng; `npm test` 34/34; `npm run build` exit 0, entry JS 68,89 kB.

```bash
test -f .env || cp .env.example .env
uv sync --locked
(cd web && npm ci && npm test && npm run build)
```

`npm run build` chạy `tsc --noEmit` rồi `vite build`, ghi ra `osa/static/dist/`. Thư mục này không có trong git. Thiếu nó, server trả trang tĩnh cũ tiếng Trung. Mỗi lần pull code mới phải build lại.

## 4. Cấu hình

OSA đọc cấu hình theo ba lớp. `config.yaml` trong repo là mặc định. Giá trị chỉnh trên UI lưu trong database và đè lên YAML. Biến môi trường dùng cho secret và vị trí dữ liệu.

`.env` chép từ `.env.example`, không có trong git. `scripts/osa-start.sh` đọc file này bằng Bash, nên chỉ đặt vào đó những dòng bạn tự viết. Chú thích phải nằm trên dòng riêng.

### Biến môi trường hay dùng

| Biến | Việc |
|---|---|
| `OSA_DATA_DIR` | thư mục dữ liệu, nên là đường dẫn tuyệt đối ngoài checkout. DB, `vault.key`, `session.key`, workspace, dữ liệu Computer, log và PID của script start nằm ở đây |
| `OSA_CONFIG` | dùng file YAML khác thay cho `config.yaml` |
| `OSA_PASSWORD` | bật trang đăng nhập. Bắt buộc trước khi mở ra ngoài localhost |
| `OSA_BIND` | Docker Compose dùng biến này làm địa chỉ nghe. Khác `127.0.0.1` mà chưa có `OSA_PASSWORD` thì server từ chối khởi động |
| `OSA_ALLOW_NO_PASSWORD` | đặt `1` để vẫn chạy khi nghe ngoài loopback mà chưa có mật khẩu. Chỉ dùng trong mạng tin cậy |
| `OSA_ALLOWED_HOSTS` | khi chưa có mật khẩu, thêm tên host được phép (localhost, IP, `*.local`, `*.ts.net` đã được nhận) |
| `DEEPSEEK_API_KEY` | key cho provider mặc định trong `config.yaml`. Có thể bỏ trống rồi nhập key trên UI |
| `INSTABOX_API_KEY` | Computer Instabox. Có thể nhập trên panel thay cho biến này |
| `OSA_VAULT_KEY` | khóa vault. Không đặt thì OSA tự tạo `vault.key` trong thư mục dữ liệu. Đừng đổi khóa trên dữ liệu đã có |
| `OSA_WEBHOOK_TOKEN` | token cho header `X-OSA-Token` của webhook cũ |
| `OSA_BACKUP_PASSPHRASE` | mật khẩu cho lệnh backup CLI |
| `TZ` | ví dụ `Asia/Ho_Chi_Minh`, để lịch chạy theo giờ Việt Nam |
| `OSA_AI_NATIVE_DEFAULTS` | `false` thì không cài lại bộ skill AI Native lúc khởi động |
| `HTTPS_PROXY` | proxy cho provider hoặc kênh chat khi mạng cần |

`OSA_LOCALE` của bản cũ không còn tác dụng. Ngôn ngữ chọn trên UI.

### Khóa trong `config.yaml` nên biết

| Khóa | Mặc định | Việc |
|---|---|---|
| `limits.task_timeout_s` | `600` | một task chạy tối đa bao nhiêu giây. Task Computer dài có thể cần số lớn hơn, chỉnh ở Cài đặt → Giới hạn |
| `limits.daily_token_budget` | `2000000` | số token tối đa mỗi ngày |
| `limits.worker_max_steps` | `30` | số bước tối đa của một Worker |
| `limits.stream_idle_s` | `120` (trong code, không có dòng trong `config.yaml`) | stream của model im quá số giây này thì OSA đóng stream. Phải nhỏ hơn 3 phút của Watchdog. `0` là không giới hạn |
| `limits.stream_retries` | `1` (trong code) | số lần gọi lại cùng lượt khi stream treo, rớt kết nối, gặp 5xx hoặc lỗi "at capacity". Lỗi hết quota không gọi lại |
| `limits.provider_transient_retries` | `5` | số lần thử lại 408, 409, 5xx trước khi stream mở |
| `computer.backend` | `auto` | trong app desktop là `host`. Ngoài app desktop, có khóa Instabox thì là `instabox`, không có thì là `local` (Docker) |
| `computer.choices` | không đặt | giới hạn các kiểu Computer hiện trên panel, ví dụ `[instabox]` |
| `computer.width`, `computer.height` | `1280`, `800` | cửa sổ trình duyệt của task trên Docker và Instabox nhỏ hơn 90% kích thước này thì được phóng lên (không vượt màn hình) |
| `computer.parallel` | `3` | số task dùng Computer cùng lúc |
| `computer.idle_pause_s` | `900` | Computer không dùng quá số giây này thì tạm dừng |
| `computer.host_shell`, `computer.linked_shell` | `false` | terminal trên Chrome máy này và trên Mac cho mượn. Bật thì mỗi lệnh vẫn phải xác nhận |
| `security.local_exec` | `true` | máy chủ public nên đặt `false` |
| `skills.ai_native_defaults` | `true` | cài sẵn bộ skill AI Native cho mọi Bot |

Muốn đặt `stream_idle_s` hay `stream_retries` khác mặc định thì thêm vào khối `limits:` của file YAML bạn dùng.

## 5. Chạy lần đầu

**Đã chạy** trên bản clone mới với thư mục dữ liệu riêng và cổng 8799.

Cách thường dùng là script, nghe ở `127.0.0.1:8765`:

```bash
bash scripts/osa-start.sh
bash scripts/osa-stop.sh
```

Script ghi PID và log vào `logs/` trong checkout, hoặc `$OSA_DATA_DIR/logs/` khi có biến đó. Xem trước đường dẫn mà không khởi động:

```bash
OSA_START_DRY_RUN=1 bash scripts/osa-start.sh
```

Script luôn dùng cổng 8765. Cổng đó đã có process khác thì chạy foreground với cổng khác. Cách này không tự nạp `.env`, nên nạp trước:

```bash
set -a; source .env; set +a
OSA_DATA_DIR="$HOME/osa-data" uv run uvicorn osa.server:app --host 127.0.0.1 --port 8799
```

Dòng "started" của script chưa chứng minh server đã sẵn sàng. Kiểm bằng HTTP:

```bash
curl -sf http://127.0.0.1:8765/manifest.json >/dev/null && echo ok
curl -s http://127.0.0.1:8765/api/files
```

Kết quả trên bản clone mới, chưa đặt mật khẩu: `/`, `/api/settings`, `/api/status`, `/api/bootstrap`, `/sw.js` đều trả 200; trang có `lang="vi-VN"`; có sẵn một Bot tên Nova; Host lạ bị 403. Máy không có Docker thì `/api/files` trả `"reason":"docker_missing"`. Đó là kết quả đúng, không phải lỗi.

Lần khởi động đầu, OSA tạo DB, cài 8 skill AI Native, nhập 2 lịch từ khối `triggers` của `config.yaml`, và tải bảng giá công khai từ models.dev.

### Mật khẩu đăng nhập

**Đã chạy.** Đặt `OSA_PASSWORD` trong `.env` hoặc môi trường rồi khởi động lại. Kết quả kiểm: `GET /` trả 303 về `/login`; `/login` trả 200; API không có cookie trả 401; sai mật khẩu trả 401; đúng mật khẩu trả 303 và cookie phiên dùng được.

Mật khẩu chỉ nằm trong `.env` hoặc kho secret của bạn. Đừng ghi vào lệnh lưu lịch sử shell, và đừng commit `.env`.

### Model và secret

Thêm model ở Cài đặt → Mô hình. API key nhập qua form, được mã hóa vào vault bằng `vault.key` hoặc `OSA_VAULT_KEY`. Nút Thử gọi API thật và có thể tính phí. Muốn dùng Computer, chọn model đọc được ảnh và gọi được tool.

## 6. Chạy test giống CI

**Đã chạy** trên worktree tại `8c108c9`: 828 passed, 1 skipped. Test bị skip là `test_real_desktop` (cần macOS và `OSA_TEST_DESKTOP=1`).

```bash
uv run python -m compileall -q osa
uv run python -c "import osa.server"
uv run python -m osa.catalog
uv run python -m osa.templates
uv run python -m osa.i18n
uv run python -m osa.skillpacks verify-sources
env -u DISPLAY CI=1 OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs
(cd web && npm ci && npm test && npx tsc --noEmit && npm run build)
```

Kết quả phụ: 40 app có manifest hợp lệ; i18n thiếu 0, thừa 0 ở backend và frontend; `verify-sources` PASS 129 file; web 34/34.

Pytest dùng DB tạm và model giả, không gọi model trả phí, không gửi kênh chat. Ba biến điều khiển test:

| Biến | Tác dụng |
|---|---|
| `OSA_REQUIRE_SANDBOX=1` | 3 test sandbox phải chạy. Thiếu `bwrap` thì chúng FAIL thay vì SKIP |
| `OSA_TEST_CHROME=1` | ép chạy `test_real_chrome`. `0` là bỏ qua. Không đặt thì test chạy khi có Chrome, có màn hình và không có biến `CI` |
| `OSA_TEST_DESKTOP=1` | chạy `test_real_desktop`, chỉ trên macOS |

Chạy `uv run pytest -q` trơn trên máy Linux không màn hình vẫn được. Từ bản này `test_real_chrome` tự SKIP với gợi ý dùng `xvfb-run -a`, thay vì fail sau 20 giây.

## 7. Computer

Panel Computer có ba kiểu. `computer.choices` giới hạn danh sách hiện trên panel.

### Docker trên máy này

**Chưa kiểm trên máy kiểm** (không có Docker). Lần đầu một task dùng Computer, OSA tự build image `osa-computer:1` từ `osa/computer/image/` (mất vài phút), rồi tạo container `osa-computer`. Workflow `computer-image.yml` trên CI build image này mỗi khi thư mục đó đổi. Sửa image xong thì `docker rm -f osa-computer` để lần sau OSA tạo lại.

### Chrome trên máy này

**Đã chạy** qua `test_real_chrome` (pass sau khoảng 4 giây dưới `xvfb-run -a`). OSA mở Chrome với profile riêng và cổng debug riêng. Trên Linux không có màn hình, Chrome không mở được cổng debug và panel báo lỗi `Chrome 没有在 20 秒内开启调试端口` (câu này chưa có bản dịch, nghĩa là Chrome không mở cổng debug trong 20 giây). Chạy OSA bên trong màn hình ảo, ví dụ `xvfb-run -a bash scripts/osa-start.sh` (**chưa kiểm** với server thật), hoặc trỏ `DISPLAY` tới một Xvfb đang chạy.

### Instabox

**Đã chạy** trên box vận hành ngày 10/11 (E2E B1–B6 và TIP-04b). Nhập khóa trên panel Computer. OSA thử khóa rồi mới mã hóa vào vault. `INSTABOX_API_KEY` trong môi trường cũng dùng được. Với `backend: auto`, có khóa là OSA chọn Instabox.

Những điều cần biết:

- VM tạm dừng sau `computer.idle_pause_s` giây không dùng (mặc định 900). Muốn VM thức lâu hơn thì tăng số này trong YAML của máy bạn, và đừng commit giá trị đó lên repo.
- Box vận hành chạy thêm một script giữ lease hoạt động của Instabox (gia hạn lease 600 giây theo chu kỳ). Instabox vẫn áp trần thời gian chạy của máy (`maxRunMinutes`, là 480 phút lúc kiểm ngày 10/11). Hết trần thì VM vẫn bị dừng dù lease còn. Script đó và mã máy là của box vận hành, không có trong repo.
- Gói miễn phí chỉ có một máy. Hai server OSA dùng chung một khóa sẽ tranh nhau máy đó. Không thử Instabox từ bản cài thứ hai khi box vận hành đang dùng.
- `GET /shot` trả 409 trên Instabox vì panel dùng live view. Đây không phải lỗi.
- Không ghi khóa, link VNC hay link điều khiển VM vào repo, log hay chat.

## 8. Chạy bằng Docker Compose

**Chưa kiểm** bằng `docker compose up` trên máy nào. CI chỉ kiểm `docker compose config --quiet` cho `compose.yaml` và `compose.yaml` + `compose.computer.yaml`, build image app, rồi smoke test bằng `docker run` (**CI**, xanh).

```bash
cp .env.example .env
docker compose up -d
```

Image app đã có Node, uv và bubblewrap, không cần cài Python hay build web trên máy host. Muốn dùng Computer Docker, thêm dòng `COMPOSE_FILE=compose.yaml:compose.computer.yaml` vào `.env` rồi `docker compose up -d` lại. File đó gắn `docker.sock`, tức là cấp cho server quyền gần như root trên host. Chỉ dùng Instabox thì đừng thêm file đó.

Chi tiết (HTTPS qua Caddy, mirror, lỗi thường gặp) ở [docs/docker.md](../docker.md). Từ bản sửa AUDIT-F10, file đó là tiếng Việt và clone repo remake với `-b i18n-vi`.

## 9. Nâng cấp từ bản cũ

1. Đợi task quan trọng chạy xong.
2. Sao lưu. Cách thứ nhất là Cài đặt → Sao lưu & di chuyển. Cách thứ hai là CLI (**Đã chạy** trên DB mới, ra file `.osabak`):

   ```bash
   OSA_BACKUP_PASSPHRASE='...' uv run python -m osa.backup export -o ~/osa-backups
   ```

   Backup không chứa `.env`, `session.key`, log hay đăng nhập trình duyệt trong Computer. Muốn chắc chắn, copy thêm file DB đang mở khi server đã dừng. Tìm đúng file bằng `ls -l /proc/<pid>/fd | grep '\.db'`. Đừng đoán đường dẫn từ `OSA_DATA_DIR`, vì `memory.db` viết đường tuyệt đối thì không đi theo biến đó.
3. `git fetch origin && git switch i18n-vi && git pull --ff-only`. Cây có thay đổi chưa commit thì dừng lại xem, đừng `reset`.
4. `uv sync --locked` và `(cd web && npm ci && npm run build)`.
5. `bash scripts/osa-stop.sh`, xác nhận process cũ đã tắt, rồi `bash scripts/osa-start.sh`.

Migration DB chạy lúc khởi động. Git không hạ được schema DB, nên muốn quay lại bản cũ phải restore từ backup.

Những gì đổi ở các bản gần đây:

- PR #37: thêm `limits.stream_idle_s` và `limits.stream_retries` (có mặc định trong code, không phải sửa YAML).
- PR #36: cửa sổ task Docker/Instabox tự phóng theo `computer.width` × `computer.height`.
- PR #35: `reasoning_effort` chỉ nhận rỗng, `low`, `medium`, `high`, `xhigh`, `max`. Giá trị khác trên role cũ sẽ bị từ chối khi lưu.
- Từ PR #23: Compose mặc định không còn `docker.sock`. Đang dùng Computer Docker qua Compose thì thêm `compose.computer.yaml`, và `docker rm -f osa-computer` để container mới nhận cờ bảo mật.

## 10. Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Chrome 没有在 20 秒内开启调试端口` (Chrome không mở cổng debug trong 20 giây) | Linux không có màn hình, hoặc Chrome của Bot đã mở sẵn mà không có cổng debug | chạy dưới `xvfb-run -a` hoặc đặt `DISPLAY`. Nếu có màn hình thì đóng cửa sổ Chrome của Bot rồi thử lại |
| 3 test trong `tests/test_local_checks.py` SKIP | thiếu `bwrap`, `prlimit`, `git` hoặc `ps`, hoặc kernel chặn user namespace | cài gói ở mục 1, mở userns, kiểm lại bằng lệnh `bwrap` ở mục 1. Đặt `OSA_REQUIRE_SANDBOX=1` để biến SKIP thành FAIL |
| `run_code` báo BLOCKED | như dòng trên | như dòng trên. OSA không chạy code ngoài sandbox |
| Task bị hủy với "Không có tiến triển trong 3 phút" | stream model im lâu | từ PR #37, OSA đóng stream sau `stream_idle_s` (120 giây) và gọi lại một lần. Vẫn bị hủy thì xem log task và trạng thái provider |
| Log task có dòng "Lượt gọi model lỗi giữa chừng (...), đang gọi lại" | provider báo "at capacity", 5xx, hoặc rớt kết nối giữa stream | OSA tự gọi lại `stream_retries` lần. Lỗi lặp lại thì đổi model hoặc thử lại sau |
| Panel Computer báo `docker_missing` | máy không có Docker hoặc không nối được daemon | cài Docker, hoặc dùng Instabox hay Chrome trên máy này |
| Trang web hiện tiếng Trung, giao diện cũ | chưa build `web/` | `(cd web && npm ci && npm run build)` rồi tải lại trang |
| Server không khởi động, báo cần mật khẩu | nghe ngoài loopback mà chưa có `OSA_PASSWORD` | đặt `OSA_PASSWORD`, hoặc nghe `127.0.0.1` |
| `git clone` ra bản không có `tests/` | clone nhánh mặc định `main` | `git switch i18n-vi` |

## 11. An toàn

Mặc định server chỉ nghe localhost. Trước khi mở ra mạng, đặt `OSA_PASSWORD` và dùng HTTPS. Không public VNC, CDP, `.env`, vault, database hay file backup. Đọc [SECURITY.md](../../SECURITY.md).
