# Phiên 07/11/2026 · grok-bot · OSA-004

- Bắt đầu khoảng 12:16, kết thúc kiểm tra khoảng 12:23, **Asia/Saigon (UTC+7)** (đồng hồ UTC+7 tính từ `datetime` UTC 05:23).
- Base: `3c08269da64dc26941e064267221c7af28af1dca` (`i18n-vi`, merge PR #6).
- Branch: `grok-bot/port-upstream-v0.6.1`. Commit port: `8fd4327b4581a5adc3b5e026dd7e22bfdf718fa7`. Ba SHA upstream cùng trỏ commit này vì lịch sử không chung và các file đè lên nhau.
- Skill Flow: osa-dev → ai-work-method → vibecode-kit → unslop-vi.
- Scope: port đúng ba commit upstream `0897360`, `ec71362`, `3432671`. Không desktop/Tauri, không local-Chrome, không `v0.7.0-preview`, không rewrite README.
- Upstream `kadaliao/open-super-agent` chỉ fetch. `remote.upstream.pushurl=DISABLED`. Không push, không PR upstream.

## TIP-PORT-061

Mục tiêu: đưa bản vá bảo mật v0.6.1, số version 0.6.1 và `OSA_DATA_DIR` vào remake mà giữ VI mặc định, Chinese-as-key, missing-Docker và script/docs hiện có.

| REQ/AC | Tiêu chí |
|---|---|
| AC-1 | Fix `0897360` có mặt. Test chặn Origin lạ và Host không thuộc localhost/IP/`*.local`/`*.ts.net` khi chưa có mật khẩu. |
| AC-2 | `OSA_DATA_DIR` trỏ temp dir: DB, khóa, apps, workspace, giá model, dữ liệu Computer và log/PID đi theo thư mục đó. Không phát sinh file mới dưới `data/` hoặc `logs/` của repo. |
| AC-3 | `pyproject.toml`, `uv.lock`, `web/package.json`, `web/package-lock.json` là `0.6.1`. Không thêm hậu tố remake vì repo đang dùng số trần. |
| AC-4 | `osa.i18n` exit 0, pytest không tụt so với 172, frontend test/build, `verify-sources` PASS. |
| AC-5 | `git diff --check` sạch. Scan secret trên diff đã review. Không push upstream. |
| AC-6 | STATE/BOARD/log cập nhật. PR theo template, có bảng provenance và VERIFY. |

Giữ nguyên: `_lang()` VI của remake, regex header task trong `memory.py`, `docker_missing` trong `computer/local.py`, `skills.ai_native_defaults` trong `config.yaml`, script test trong `web/package.json`.

## Vì sao không cherry-pick máy

`git merge-base HEAD 9790ffa` không có ancestor chung. Ba commit đứng liền sau tag `v0.6.0` (`9790ffa` → `0897360` → `ec71362` → `3432671`). Commit desktop bắt đầu từ `1433de4`, sau `3432671`, nên ba commit này không phụ thuộc phần ngoài scope.

Remake đã sửa cùng vài file (`auth.py`, `memory.py`, `computer/local.py`, `catalog/__init__.py`, `config.yaml`, `web/package.json`). Patch được áp tay để không đè các sửa đó.

## Phán đoán đã ghi

- `3432671` nằm sau tag v0.6.1. Upstream không tăng version ở commit đó. Remake giữ `0.6.1`. CHANGELOG để `OSA_DATA_DIR` dưới mục chưa phát hành, đúng cây upstream tại `3432671`.
- AC-2 yêu cầu log cũng ra khỏi repo. Upstream chỉ chuyển DB/khóa/apps/workspace/Computer. `scripts/osa-start.sh` và `osa-stop.sh` đưa log/PID vào `$OSA_DATA_DIR/logs` khi biến này có giá trị. Không đặt thì vẫn `logs/` trong checkout.
- `OSA_START_DRY_RUN=1` in đường dẫn rồi thoát, để test không bật uvicorn. `OSA_DOTENV=0` bỏ qua `.env` local trong lúc test. Mặc định script vẫn nạp `.env`.
- Test HTTP của remake dùng `base_url="http://test"`. Host `test` bị chặn khi chưa có mật khẩu. Đổi thành `http://127.0.0.1`. Không thêm `test` vào allowlist sản phẩm.
- Câu từ chối Host mới có bản EN đúng upstream và bản VI mới. Khóa tiếng Trung nằm trong `t()`.

## VERIFY REPORT · TIP-PORT-061

- Date: 07/11/2026 12:23 Asia/Saigon. Base `3c08269`. Branch `grok-bot/port-upstream-v0.6.1`.
- Máy: Linux, Python qua `uv`, Node v22.23.4, bubblewrap 0.9.0 (cài trong phiên vì thiếu sẵn; 9 test `test_local_checks.py` PASS sau khi có `bwrap`).

### REQUIREMENT COVERAGE

6/6 AC P0 PASS trên cây đã chạy. Docker Computer E2E, Worker live, rendered browser: NOT_CHECKED, ngoài scope.

### SCENARIO RESULTS

| REQ/AC | Tier | Kết quả | Evidence |
|---|---|---|---|
| AC-1 | Tier 1 / P0 | PASS | `tests/test_auth.py` trong suite. Origin lạ đóng WebSocket và chặn POST, kể cả `/hooks/`. Host `evil.example` 403, trang text/plain. IP, localhost, `*.local`, `*.ts.net`, allowlist và webhook có token được phủ. Có mật khẩu thì vẫn chặn Origin lạ và không kiểm Host. |
| AC-2 | Tier 1 / P0 | PASS | `tests/test_data_dir.py`: DB/apps/workspace/prices/computer nằm trong temp dir; `session.key` được tạo ở đó; snapshot `data/`+`logs/` của repo không đổi. Dry-run script đặt log/PID dưới temp dir. |
| AC-3 | Tier 1 / P0 | PASS | `pyproject.toml`, `uv.lock`, `web/package.json`, `web/package-lock.json` đều `0.6.1`. |
| AC-4 | Tier 1 / P0 | PASS | Lệnh và số ở bảng dưới. |
| AC-5 | Tier 1 / P0 | PASS | `git diff --check` exit 0. Scan diff: chỉ tên file `session.key`/`vault.key` và placeholder `.env.example`. Fixture test dùng `test-password` và token `t`, không phải secret thật. `upstream` push URL `DISABLED`. |
| AC-6 | Tier 1 / P0 | PASS | STATE append, BOARD thêm OSA-004, log này. PR body theo `.github/pull_request_template.md` và `.agents/templates/PR.md`. |

Tier 2: đường dẫn DB tuyệt đối vẫn thắng `OSA_DATA_DIR`; Host rỗng (không phải trình duyệt) được phép; webhook không token từ host lạ bị 403. UI 375/768/1440 NOT_CHECKED (không đổi layout).

Tier 3 security: xem mục dưới. Performance/a11y NOT_CHECKED. Build JS vẫn cảnh báo >500 kB, không phải fail.

### TECHNICAL HEALTH

| Gate | Kết quả |
|---|---|
| `uv run python -m osa.i18n` | exit 0. EN/VI backend 501, frontend 883, thiếu 0, thừa 0, Chinese UI chưa wrap 0. |
| `uv run pytest -q -ra` | exit 0. **193 passed, 0 skipped.** Baseline 172. Thêm 21 test (17 auth + 4 data dir). Lần chạy trước khi cài bwrap: 190 passed, 3 skipped ở `tests/test_local_checks.py`. Sau `bubblewrap 0.9.0`: 9/9 file đó PASS, full suite 193. |
| `cd web && npm ci && npm test && npm run build` | exit 0. npm ci 131 packages, 0 vulnerabilities. npm test 15 passed, 0 skipped. Build PASS. JS 1,153.85 kB, gzip 374.59 kB. Warning chunk >500 kB còn. |
| `uv run python -m osa.skillpacks verify-sources` | PASS, 129 file, sha256 PASS. |
| `git diff --check` | sạch. |
| unslop-vi `scan_vi.py` | Chạy trên `docs/huong-dan-vi.md`, `README.md`, `docs/cap-nhat-tu-upstream.md`, `.agents/ARCHITECTURE.md`. V12 phần lớn là backtick bị mask thành khoảng trắng. Đã tách câu DNS rebinding để bỏ dấu hai chấm nối câu ở đoạn mới. |

Paid LLM: 0. Không gửi channel, không bật scheduler thật, không dùng DB thật. Pytest dùng temp DB từ `conftest` trước import.

### RETRO RUBRIC SCORE

`skills-pack/ai-native/vibecode-kit/scripts/retro_rubric.py` trên `/tmp/retro-osa-port`, tip `TIP-PORT-061`.

| Vòng | R1 | R2 | R3 | R4 | R5 | Tổng | Gate |
|---|---|---|---|---|---|---|---|
| 1 | 2 | 2 | 2 | 2 | 2 | 10/10 | PASS, 0 chiều 0, first-pass, 0 RETRO-ID |

### Security review của bản vá

Giữ đúng hành vi upstream:

- WebSocket và method ngoài GET/HEAD/OPTIONS luôn so Origin với Host, kể cả khi chưa có `OSA_PASSWORD` và kể cả `/hooks/`. `Origin: null` bị từ chối. Request không có Origin (curl) được phép.
- Chưa có mật khẩu thì Host phải là `localhost`, IP (kể cả `::1`), hậu tố `.localhost`/`.local`/`.ts.net`, hoặc `server.allowed_hosts` / `OSA_ALLOWED_HOSTS`. `fnmatch` sau khi hạ chữ. `*.example.com` không khớp `example.com.evil.example`.
- Có mật khẩu thì không kiểm Host. Cookie gắn với host đã đăng nhập, nên DNS rebinding sang tên khác không mang cookie localhost. Đường public vẫn cần cookie. Đây là thiết kế upstream, không nới thêm.
- Webhook có `OSA_WEBHOOK_TOKEN` bỏ qua allowlist Host vì endpoint tự kiểm header. Origin lạ vẫn bị chặn ở middleware. Trang khác không gửi được header tùy ý sang origin khác. Cùng origin sau DNS rebinding chỉ gọi được webhook nếu biết token.

Không thấy secret trong diff. Không đụng `main`. Không force-push.

### OVERALL STATUS

READY cho phần port này. Deferred: Docker desktop E2E, Worker live, rendered browser. Cảnh báo kích thước JS là nợ cũ (OSA-003). Chưa merge. GO kỹ thuật không phải quyền merge.

## Next step

Tin Tin review [PR #8](https://github.com/VagabondKingsman/open-super-agent-remake/pull/8) vào `i18n-vi`. Code port nằm ở `8fd4327b4581a5adc3b5e026dd7e22bfdf718fa7`. Không tự merge. OSA-006 (`grok-bot/contributing-bots`) cùng sửa STATE/BOARD; phần thêm ở đây là append và một ô owner OSA-004.
