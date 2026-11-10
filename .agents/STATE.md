# Trạng thái hiện tại · 10/11/2026

Snapshot lúc 21:00 Asia/Saigon (UTC+7), viết trong phiên deep audit cài đặt. Phiên mới phải `git fetch origin` và `git rev-parse origin/i18n-vi` lại. SHA mới hơn thì đọc log mới hơn file này.

Lịch sử STATE từ 07/11 tới trước phiên này được chuyển nguyên văn sang [archive/STATE-2026-11-07-den-2026-11-10.md](archive/STATE-2026-11-07-den-2026-11-10.md). Các câu "chưa merge" trong đó là trạng thái lúc viết từng mục.

## Base

- `origin/i18n-vi` = `8c108c99ccb3fe17767ee792bea2b877a5a66e9a`, merge PR #39.
- Version `0.17.0`, nền upstream v0.17.0 (`ec02547`).
- `main` trên GitHub vẫn đứng ở `a30e3cc`, bản cũ không có `.agents/` hay `tests/`. Luôn làm trên `i18n-vi`.
- CI push trên `8c108c9`: run `42826978455`, backend, frontend, docker đều success (20:42–20:44).

## Bốn PR gần nhất

| PR | Merge (Asia/Saigon) | Merge commit | Head | Việc |
|---|---|---|---|---|
| [#36](https://github.com/VagabondKingsman/open-super-agent-remake/pull/36) | 17:08:40 | `7a0e674` | `875a71d` | TIP-04b: cửa sổ task Docker/Instabox tự phóng theo `computer.width` × `computer.height`. Handoff `.agents/`, README VI |
| [#37](https://github.com/VagabondKingsman/open-super-agent-remake/pull/37) | 20:15:33 | `0500666` | `1f5408a` | Stream model treo hoặc rớt giữa chừng thì gọi lại cùng lượt (`limits.stream_idle_s` 120, `limits.stream_retries` 1). Sửa task Nova #253 |
| [#38](https://github.com/VagabondKingsman/open-super-agent-remake/pull/38) | 20:30:03 | `e55d00a` | `0cc7217` | CI cài `bubblewrap`, `OSA_REQUIRE_SANDBOX=1`: 3 test sandbox chạy thật |
| [#39](https://github.com/VagabondKingsman/open-super-agent-remake/pull/39) | 20:42:26 | `8c108c9` | `0aa79de` | CI chạy `test_real_chrome` với Chrome thật dưới `xvfb-run -a` |

`merged_by` của cả bốn là VagabondKingsman, theo GitHub API.

## Số kiểm trên `8c108c9`

Lệnh và output đầy đủ ở [log deep audit](log/2026-11-10-deep-audit-install.md).

- `env -u DISPLAY CI=1 OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs`: 828 passed, 1 skipped. Skip là `test_real_desktop` (cần macOS và `OSA_TEST_DESKTOP=1`).
- `osa.i18n`: backend 1187 câu, frontend 1211 câu, thiếu 0, thừa 0, câu tiếng Trung chưa bọc `t()` 0.
- `osa.catalog` 40 app hợp lệ. `osa.templates` PASS. `verify-sources` 129 file PASS.
- Web: `npm ci` 0 lỗ hổng, `npm test` 34/34, `tsc --noEmit` exit 0, build exit 0, entry JS 68,89 kB.
- Cài mới từ GitHub (`git clone` + `git checkout i18n-vi`) với thư mục dữ liệu riêng, cổng 8799: chạy được, đăng nhập bằng mật khẩu đúng như tài liệu, `docker_missing` đúng khi không có Docker.
- Docker build và `docker compose up` trên box: `NOT_CHECKED`, box không có Docker. CI docker job xanh.

## Box vận hành

- OSAR chạy từ `/workspace/open-super-agent`, uvicorn trên `127.0.0.1:8765`, khởi động bằng `scripts/osa-start.sh`. `git diff origin/i18n-vi -- osa web/src tests` trên checkout đó rỗng, tức code đang chạy là code của `8c108c9` (PR #38 và #39 chỉ đổi CI và docs).
- Checkout đó đang ở nhánh local `ci/real-chrome` và có `config.yaml` sửa chưa commit (`computer.idle_pause_s: 2592000`) để VM Instabox không tự dừng. Không commit, không stash, không đổi nhánh ở checkout đó. Làm việc trong worktree riêng.
- Computer là Instabox (`backend: auto` + khóa trong vault). Một script giữ lease hoạt động của VM chạy song song. VM vẫn có trần `maxRunMinutes` 480 phút mỗi lượt chạy.
- Không ghi khóa, mật khẩu, mã máy, link VNC hay link remote vào repo.

## Đang mở

- Branch `docs/deep-audit-install` (phiên này): một sửa test, hướng dẫn cài máy mới, docs và `.agents/`. Chưa push. Patch ở thư mục evidence của box, CloudAgent `git am` rồi mở PR vào `i18n-vi`.
- Kết quả audit còn mở, chưa sửa: xem bảng trong [log deep audit](log/2026-11-10-deep-audit-install.md#phát-hiện) và [BOARD](BOARD.md).
- Việc cũ còn chờ: OSA-001, OSA-002, OSA-007, OSA-016, OSA-017, OSA-018, OSA-019, OSA-020 trên [BOARD](BOARD.md).
