# Phiên 2026-11-10 · cursor (Kingfisher) · DOCS-INSTALL deep audit

- Bắt đầu, kết thúc: 20:55 – 21:20 Asia/Saigon (UTC+7). Đồng hồ box chạy UTC, các giờ dưới đây đã đổi sang UTC+7.
- Repo, base: `VagabondKingsman/open-super-agent-remake`, `origin/i18n-vi` = `8c108c9` (merge PR #39). Branch local `docs/deep-audit-install`, worktree `/workspace/osar-audit`.
- Yêu cầu của Tin Tin: deep audit repo trên bản mới nhất, cập nhật docs tiếng Việt và handoff `.agents/` đủ để team dev cài full flow trên máy mới.
- Skill Flow: `osa-dev` → `ai-work-method` → `vibecode-kit`, thêm `unslop-vi` cho văn tiếng Việt.
- Không gọi model trả phí. Không gửi kênh chat. Không restart server thật, không đụng script giữ VM, không commit `config.yaml` của box.

## Trình tự

1. Tạo worktree từ `origin/i18n-vi`, chạy đủ gate như CI.
2. Clone mới từ GitHub vào thư mục tạm, làm đúng các bước README: `git checkout i18n-vi`, chép `.env`, `uv sync --locked`, `npm ci && npm test && npm run build`. Chạy server ở cổng 8799 với `OSA_DATA_DIR` riêng, gỡ key provider và khóa Instabox khỏi môi trường. Kiểm HTTP, rồi chạy lại với `OSA_PASSWORD` ngẫu nhiên để kiểm đăng nhập. Xuất thử backup CLI. Tắt server, xác nhận cổng 8799 đã đóng.
3. Đọc README, README.en, `docs/huong-dan-vi.md`, CONTRIBUTING, `docs/configuration.md`, `docs/docker.md`, `.env.example`, `compose*.yaml`, Dockerfile, CI và toàn bộ `.agents/`. Đối chiếu với `config.yaml` và code.
4. Đọc diff PR #36 và #37 (`osa/providers.py`, `osa/router.py`, `osa/worker.py`, `osa/computer/base.py`, `osa/computer/cdp_helper.py`), cùng `host.py`, `local.py`, `backup.py`, `scripts/osa-start.sh`.
5. Tái hiện một lỗi cài đặt: Linux không màn hình, có Chrome, chạy `uv run pytest -q` trơn thì `test_real_chrome` fail sau 20 giây. Sửa trong test, kiểm ba chế độ.
6. Viết `docs/vi/cai-dat-may-moi.md`, sửa README, docs, CHANGELOG, `.agents/`. Quét văn tiếng Việt bằng `scan_vi.py`. Chạy lại pytest, xuất patch.

## Evidence

Output thô nằm trong thư mục evidence của box (`/workspace/osar-deep-audit-20261110/`), không đưa vào git.

| AC | Kết quả | Lệnh và số |
|---|---|---|
| Gate Python | PASS | `uv sync --locked` exit 0; `compileall` 0; `import osa.server` 0; `osa.catalog` 40 app; `osa.templates` PASS; `osa.i18n` backend 1187, frontend 1211, thiếu 0, thừa 0, chưa bọc 0; `verify-sources` 129 PASS |
| Pytest như CI | PASS | `env -u DISPLAY CI=1 OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs`: 828 passed, 1 skipped (`test_real_desktop`), 69,6 giây |
| Web | PASS | `npm ci` 0 lỗ hổng; `npm test` 34/34; `npx tsc --noEmit` exit 0; `npm run build` exit 0, entry JS 68,89 kB |
| Clone mới theo README | PASS | clone mặc định ra `main` (`a30e3cc`), `git checkout i18n-vi` ra `8c108c9`. `git clone -b i18n-vi` cũng ra `8c108c9`. uv sync, web 34/34, build OK |
| Chạy lần đầu (cổng 8799) | PASS | lên sau 4 giây. `/`, `/api/settings`, `/api/status`, `/api/bootstrap`, `/sw.js`, `/manifest.json` 200; `lang="vi-VN"`; `sw.js` có `OFFLINE_COPY`; một Bot Nova; Host lạ 403; `/api/files` và Computer của bot trả `docker_missing` |
| Đăng nhập | PASS | `GET /` 303 tới `/login`; `/login` 200; API không cookie 401; sai mật khẩu 401; đúng 303 kèm cookie; API có cookie 200 |
| Backup CLI | PASS | `python -m osa.backup export` ra `.osabak` (1 Bot, 8 skill, 2 lịch, 0 key) |
| Test Chrome trên Linux không màn hình | FAIL rồi PASS | trước sửa: 1 failed sau 20,6 giây. Sau `b29e85b`: không cờ thì SKIP kèm gợi ý; `OSA_TEST_CHROME=1` + `xvfb-run` PASS 4,3 giây; `xvfb-run` không cờ PASS 4,0 giây. Chạy lại cả suite trên head: như CI 828 passed, 1 skipped; `uv run pytest -q` trơn không màn hình 827 passed, 2 skipped |
| CI trên `8c108c9` | PASS | run `42826978455`: backend, frontend, docker success, 20:42–20:44 |
| Docker build, compose | NOT_CHECKED | box không có Docker. Chỉ có CI |
| Computer Docker live | NOT_CHECKED | box không có Docker |
| Computer Instabox từ bản cài mới | NOT_CHECKED | gói miễn phí một máy, box vận hành đang dùng. Không thử để tránh tranh máy |
| Chrome host trên server mới | NOT_CHECKED trên server | chỉ kiểm qua `test_real_chrome` |
| Cài gói hệ thống trên Ubuntu sạch | NOT_CHECKED | box đã có sẵn gói. Lệnh lấy từ CI và Dockerfile |
| macOS | NOT_CHECKED | không có máy |

- Secret: lệnh chạy server mới gỡ `INSTABOX_API_KEY`, `XAI_API_KEY`, `OSA_XAI_API_KEY`, `DEEPSEEK_API_KEY`, `OSA_VAULT_KEY`, `OSA_WEBHOOK_TOKEN`. Mật khẩu thử là chuỗi ngẫu nhiên, không in. Diff đã quét, không có giá trị secret, mã máy Instabox hay link.
- Paid usage: 0.

## Phát hiện

| ID | Mức | File:dòng | Vấn đề | Đề xuất | Sửa trong PR này |
|---|---|---|---|---|---|
| AUDIT-F1 | Medium | `osa/providers.py:353-359` | `guard_stream` đếm cả thời gian chờ chunk đầu. Model ra chunk đầu sau 120–180 giây (mức suy nghĩ cao, không stream phần suy nghĩ) trước đây vẫn xong trong 3 phút của Watchdog, giờ bị đóng stream, gọi lại, rồi fail | ngưỡng riêng cho chunk đầu (ví dụ `limits.stream_first_chunk_s`, gần 170 giây) hoặc chỉ đếm sau chunk đầu, kèm test | Không |
| AUDIT-F2 | Low | `osa/router.py:411-415` | Router gọi lại thì phần suy nghĩ đã đẩy lên UI hiện hai lần. Usage của lượt hỏng không ghi | gửi sự kiện xóa thinking của lượt hỏng, ghi usage ước tính | Không |
| AUDIT-F3 | Low | `osa/worker.py:127-136`, `osa/router.py:411` | Gọi lại ngay lập tức. Lỗi "at capacity" dễ lặp lại | chờ 2–5 giây có jitter trước khi gọi lại | Không |
| AUDIT-F4 | Low | `osa/computer/cdp_helper.py:567` | `fit` giữ `left`/`top`. Cửa sổ ở xa mép phải bị phóng tràn khỏi màn hình | kẹp `left`/`top` theo kích thước màn hình | Không |
| AUDIT-F5 | Medium (cài đặt) | `tests/test_host_computer.py:280-292` | Trên Linux không màn hình có Chrome, `uv run pytest -q` trong README fail 1 test sau 20 giây | SKIP khi không có `DISPLAY`/`WAYLAND_DISPLAY`, trừ khi `OSA_TEST_CHROME=1` | Có, `b29e85b` |
| AUDIT-F6 | Low | `osa/computer/cdp_helper.py:360` | Lỗi Chrome 20 giây chỉ có tiếng Trung, không nói nguyên nhân thiếu màn hình | `host.status()` kiểm màn hình trên Linux, trả lỗi có bản dịch | Không (docs đã ghi) |
| AUDIT-F7 | Low | `osa/server.py:92`, `osa/backup.py` | Cảnh báo thiếu `OSA_PASSWORD` lúc khởi động và output CLI backup chỉ có tiếng Trung | bọc `i18n.t` | Không |
| AUDIT-F8 | Low | `scripts/osa-start.sh:45` | Cố định cổng 8765. In "started" trước khi server lên, kể cả khi cổng đã bị giữ | nhận `OSA_PORT`, chờ `/manifest.json` rồi mới báo | Không (docs ghi cách chạy cổng khác) |
| AUDIT-F9 | Low | `config.yaml:51-62` | Không có dòng `stream_idle_s`, `stream_retries`. Mặc định chỉ trong code | thêm hai dòng sau khi box vận hành dọn bản sửa `idle_pause_s`, để `git pull` trên box không vướng | Không (docs ghi mặc định) |
| AUDIT-F10 | Low | `docs/docker.md:10` | Bản upstream tiếng Trung, lệnh clone trỏ upstream | đổi URL sang remake `-b i18n-vi` hoặc viết mục Compose tiếng Việt | Một phần, hướng dẫn VI có cảnh báo |
| AUDIT-F11 | Info | GitHub repo settings | Nhánh mặc định `main` ở `a30e3cc`, clone trơn ra bản cũ | đổi default branch sang `i18n-vi` hoặc đồng bộ `main`. Cần Tin Tin quyết | Docs: `git clone -b i18n-vi` |
| AUDIT-F12 | Low | `osa/backup.py:187` | `.osabak` ghi ra với quyền 0644 | `chmod 0600` sau khi ghi | Không |

Tài liệu cũ đã sửa trong PR này: README (tip `90d820c`, CI `aa1ab7e`), README.en (clone ra `main`, thiếu `uv sync`), `docs/huong-dan-vi.md` (`aa1ab7e`), CONTRIBUTING (172/193 test, chunk 1,15 MB, "push chỉ ghi `main`"), ARCHITECTURE (v0.6.1, CI chỉ `main`), HANDOFF (head `90d820c`, thiếu PR #36–#39), BOARD (TIP-04b "chưa push", E2E-OPEN còn lỗi stream), STATE (snapshot 07/11), OPS (box `c16e6bb`).

## Retro rubric

R1 đủ yêu cầu (audit, docs VI, `.agents/`): 2. R2 test chạy thật, 828/1: 2. R3 ca biên (không màn hình, cổng bận, Instabox một máy): 2. R4 phạm vi nhỏ, không đụng code sản phẩm, không đụng `config.yaml`: 2. R5 chống lặp: lỗi Chrome headless có test chặn: 2. Tổng 10/10, 1 vòng. RETRO-01: chạy pytest trơn trên máy không màn hình trước khi ghi lệnh vào README.

## Còn mở

- PR cho branch `docs/deep-audit-install`: patch nằm ở `/workspace/osar-deep-audit-20261110/patches/` trên box. Cloud agent `git am` lên `i18n-vi` rồi mở PR. Chưa push.
- AUDIT-F1 nên làm trước các mục Low.
- AUDIT-F11 cần Tin Tin chọn.
