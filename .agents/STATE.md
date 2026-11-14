# Trạng thái hiện tại · 11/11/2026

> 14/11: snapshot dưới đây **cũ**. Trạng thái mới nhất ở [log 13–14/11 full mode](log/2026-11-14-cursor-unrestricted-full-mode.md); head `origin/i18n-vi` = `ad6b87b`.

Snapshot sau merge PR #54 (`8bc4119`) và câu ứng dụng điện thoại bỏ chữ iPhone. Phiên mới phải `git fetch origin` và `git rev-parse origin/i18n-vi` lại. SHA mới hơn thì đọc log mới hơn file này.

## Base

- `origin/i18n-vi` trước commit này là `8bc4119788aff587508d68419e8f812d661f81cc`, merge [PR #54](https://github.com/VagabondKingsman/open-super-agent-remake/pull/54). Head lúc merge `1c3a94a`. Trước đó [PR #51](https://github.com/VagabondKingsman/open-super-agent-remake/pull/51) merge `14449fd`, head `6e550b0`.
- Cùng ngày, trước #51: [PR #50](https://github.com/VagabondKingsman/open-super-agent-remake/pull/50) merge `30dfb24` (head `fa0372d`). [PR #49](https://github.com/VagabondKingsman/open-super-agent-remake/pull/49) merge `887fd7d`. [PR #48](https://github.com/VagabondKingsman/open-super-agent-remake/pull/48) merge `c0fc919`. [PR #47](https://github.com/VagabondKingsman/open-super-agent-remake/pull/47) merge `3c631a3` (head `9b931f6`).
- Version sản phẩm `0.17.0`, nền upstream v0.17.0 (`ec02547`). Tag APK `v1.0` không đổi version Python.
- APK arm64 debug: SHA-256 `e3cb6a28d4df9917342be429bb50ebf4ba4fc52fa0c73407b183ac93d65df58d`. Release <https://github.com/VagabondKingsman/open-super-agent-remake/releases/tag/v1.0>.
- `main` trên GitHub vẫn `a30e3cc`. Luôn làm trên `i18n-vi` (AUDIT-F11, chờ người có quyền repo).
- CI PR #47 trên `9b931f6`: backend, frontend, docker SUCCESS. `cargo test --lib` trong `android/src-tauri`: 10 passed. Lần chạy có cache nên cờ `--offline` cũng qua. Máy mới bỏ cờ đó để Cargo tải crate.
- S22 Ultra 11/11/2026: nối `http://<máy>.<tailnet>.ts.net/`, đăng nhập, thấy AutoBot và Nova.

Phần dưới là snapshot 10/11 và các mục bổ sung. Câu "chưa merge" trong đó là lúc viết.

## Bổ sung · menu bot · cursor · 11/11/2026

Đã merge [PR #54](https://github.com/VagabondKingsman/open-super-agent-remake/pull/54) tại `8bc4119`. ID bot là số gán lúc tạo (`bots._next_id`), hiện trong Chi tiết và sao chép được. Menu thanh bên thêm đánh dấu chưa đọc, ẩn, sửa chi tiết, xóa. Bot chính vẫn không xóa được.

## Bổ sung · nút kết nối lại trên APK · cursor · 11/11/2026

Nhánh `cursor/apk-reconnect-efeb`, chưa vào `i18n-vi`. Chấm đỏ là WebSocket `/ws` đóng. Nút chỉ hiện trên Android khi chấm đỏ. Bấm thì thử ngay trong 8 giây. Thành công chấm xanh, thất bại chấm đỏ, cả hai có dòng tự mất sau 2,5 giây. Không build APK mới: trang lấy từ server.

# Trạng thái 10/11/2026

Snapshot lúc 22:20 Asia/Saigon (UTC+7), viết sau khi PR #41 merge.

Lịch sử STATE từ 07/11 tới trước phiên deep audit nằm nguyên văn ở [archive/STATE-2026-11-07-den-2026-11-10.md](archive/STATE-2026-11-07-den-2026-11-10.md). Các câu "chưa merge" trong đó là trạng thái lúc viết từng mục.

## Base

- `origin/i18n-vi` = `5a1e0e7f88a1379bc81442e4f553e81eb95d32ca`, merge PR #41.
- Version `0.17.0`, nền upstream v0.17.0 (`ec02547`).
- `main` trên GitHub vẫn đứng ở `a30e3cc`, bản cũ không có `.agents/` hay `tests/`. Luôn làm trên `i18n-vi` (AUDIT-F11, chờ Tin Tin).
- CI trên PR #41: backend, frontend, docker xanh.

## PR #35–#41 (10/11/2026)

| PR | Merge (UTC+7) | Merge commit | Head | Việc |
|---|---|---|---|---|
| [#35](https://github.com/VagabondKingsman/open-super-agent-remake/pull/35) | 16:23:51 | `90d820c` | `e5d9f5a` | E2E-B1–B6: effort fallback, chặn dispatch bịa, reviewer gộp draft, tự handoff, ảnh cả màn hình |
| [#36](https://github.com/VagabondKingsman/open-super-agent-remake/pull/36) | 17:08:40 | `7a0e674` | `875a71d` | TIP-04b: cửa sổ task Docker/Instabox tự phóng theo `computer.width` × `computer.height` |
| [#37](https://github.com/VagabondKingsman/open-super-agent-remake/pull/37) | 20:15:33 | `0500666` | `1f5408a` | Stream treo hoặc rớt giữa chừng thì gọi lại cùng lượt (Nova #253) |
| [#38](https://github.com/VagabondKingsman/open-super-agent-remake/pull/38) | 20:30:03 | `e55d00a` | `0cc7217` | CI cài `bubblewrap`, 3 test sandbox chạy thật |
| [#39](https://github.com/VagabondKingsman/open-super-agent-remake/pull/39) | 20:42:26 | `8c108c9` | `0aa79de` | CI chạy `test_real_chrome` dưới `xvfb-run -a` |
| [#40](https://github.com/VagabondKingsman/open-super-agent-remake/pull/40) | 21:16:04 | `91b6cfb` | `f7307a1` | Deep audit cài máy mới, `docs/vi/cai-dat-may-moi.md`, `.agents/` |
| [#41](https://github.com/VagabondKingsman/open-super-agent-remake/pull/41) | 22:12:10 | `5a1e0e7` | `9bce42d` | Sửa AUDIT-F1–F13 (stream, cửa sổ, Chrome không màn hình, i18n, script, backup) |

Giờ merge lấy từ commit merge. Chi tiết PR #41: [log sửa audit](log/2026-11-10-audit-fixes.md).

## Số kiểm trên code của PR #41

Chạy trên nhánh `fix/audit-f1-f12` trước khi xuất patch. Cây của `5a1e0e7` trùng cây đó (`git diff` rỗng).

- `env -u DISPLAY CI=1 OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs`: 853 passed, 1 skipped. Skip là `test_real_desktop` (cần macOS và `OSA_TEST_DESKTOP=1`).
- `uv run pytest -q` trơn trên box: 853 passed, 1 skipped.
- `osa.i18n`: backend 1214 câu, frontend 1211 câu, en/vi thiếu 0, thừa 0, 0 dòng tiếng Trung chưa bọc `t()`.
- `osa.catalog` 40 app. `osa.templates` PASS. `verify-sources` 129 file PASS.
- Web: `npm test` 36/36, `tsc --noEmit` OK, `npm run build` OK.
- Docker build và `docker compose up` trên box: `NOT_CHECKED`, box không có Docker. CI docker job xanh.

## CI

- Backend cài `bubblewrap` + `xvfb`, mở user namespace, chạy pytest với `OSA_REQUIRE_SANDBOX=1` (thiếu sandbox thì 3 test trong `tests/test_local_checks.py` FAIL, không SKIP) và `OSA_TEST_CHROME=1` dưới `xvfb-run -a` (`test_real_chrome` chạy với Chrome thật).
- Frontend: `npm ci`, `npm test`, `npm run build`.
- Docker: `compose config`, build image, smoke `docker run`.

## Box vận hành

- OSAR chạy từ `/workspace/open-super-agent`, uvicorn `127.0.0.1:8765`, pid 523005, khởi động 21:51:34 bằng `scripts/osa-start.sh`.
- Checkout đó ở nhánh local `deploy/audit-f1-f12` (`b8ca2c0`). Cây của nó trùng `5a1e0e7`, tức code đang chạy là code đã merge. Checkout **không** ở `i18n-vi`. Cách đưa về: [OPS](OPS.md#đưa-checkout-vận-hành-về-i18n-vi).
- `config.yaml` có `computer.idle_pause_s: 2592000` chưa commit. Không commit, không xóa dòng đó.
- `limits.task_timeout_s` đang chạy là 7200, lấy từ `settings.overrides` trong DB (Cài đặt → Giới hạn). `config.yaml` ghi 600. Override thắng.
- Computer: Instabox, máy `docker-osar-test`, `backend: auto` + `INSTABOX_API_KEY` trong vault của OSA. Màn hình X của VM lúc kiểm 10/11 là 661 × 1619 (người xem VNC đổi cỡ), không phải 1280 × 800.
- Giữ VM thức: `/workspace/instabox-keepalive/lease-keepalive.py` (pid 335522) gia hạn activity lease 600 giây mỗi 3 phút. Cùng thư mục có `osa-keepalive.service` chạy `keepalive.py` trong VM để tạo tải CPU nhẹ. Service đó có đang chạy trong VM hay không: `NOT_CHECKED` phiên này. Instabox vẫn áp trần `maxRunMinutes` 480 phút mỗi lượt chạy.
- Lỗi đang có (22:08–22:13): gần hết 480 phút, script gọi suspend rồi resume để tránh cooldown, cả hai trả 400 `Idempotency-Key header is required`. VM bị nền tảng pause lúc 22:13 và vào cooldown tới 22:18:18. 22:19 gọi `POST /api/bots/1/computer/start` qua OSA, trả 200, VM `running` lại (màn 661×1619). Script nằm ngoài repo, cần thêm header `Idempotency-Key` cho hai lệnh đó. Phiên docs không sửa script.
- Không ghi khóa, mật khẩu, mã máy, link VNC hay link remote vào repo.

## Đang mở

- AUDIT-F11 (nhánh mặc định GitHub) chờ Tin Tin.
- `NOT_CHECKED`: đường gọi lại stream của Router/Worker trên live (chỉ có test), Docker Compose live, app macOS, cài Instabox từ bản cài thứ hai.
- ~~Thông báo stream treo in "0 giây" khi ngưỡng dưới 1 giây~~ — sửa 14/11: `secs` in một chữ số thập phân dưới 10 giây (`web/src/components/Chat.tsx`).
- `docs/docker.md` giờ là tiếng Việt, lần merge upstream sau sẽ xung đột ở file này.
- Script giữ VM thiếu `Idempotency-Key` (mục trên). Trên box này không còn process keepalive; VM Instabox có thể `paused`, `Computer.start()` tự `resume`.
- `gmail-reg-watchdog` để **tắt** (14/11): Google chặn ở bước cross-device/SMS, máy chưa có `SMS_API_KEY` và không có `/dev/kvm`. Lý do đã ghi trong chính routine.
- `daily-brief` bật lại 14/11 (web search kiểm được, 2 023 ký tự), hẹn 09:00 hằng ngày.
- Việc cũ còn chờ: OSA-001, OSA-002, OSA-007, OSA-017, OSA-018, OSA-019, E2E-OPEN trên [BOARD](BOARD.md). OSA-016 và OSA-020 xong ngày 14/11.

## Bổ sung · merge PR #50 và #51 · cursor · 11/11/2026

Royan giao audit hai PR đang mở trên `i18n-vi`, chạy test, không lỗi thì merge.

- #50 `cursor/audit-abc-cache`, head `fa0372d`. Pytest máy này: 1152 passed, 1 skipped (1:51). `python -m osa.i18n` thoát 0, thừa 3 khóa backend (cảnh báo, không fail). CI backend/frontend/docker đã xanh trước merge. Merge commit `30dfb24`, 23:09 Asia/Saigon.
- #51 `cursor/direct-chat-label` đứng trên `887fd7d`, đè changelog, locale và `Chat.tsx` với #50. Pytest riêng: 913 passed, 1 skipped. Sau khi #50 vào `i18n-vi`, GitHub báo conflict. Merge `origin/i18n-vi` vào nhánh, giữ cả hai bên, commit `6e550b0`. Pytest cây ghép: 1157 passed, 1 skipped. Web `npm test` 43/43, `tsc --noEmit` sạch. Merge commit `14449fd`, 23:16 Asia/Saigon.
- Không có key trong diff. `scripts/net-fast.sh`, `tailnet-serve.sh`, `tailscale-up.sh` là script máy boxes: `/home/boxes`, hostname `osa`, đọc `TS_AUTHKEY` từ `.env`. Không chạy chúng ở nơi khác.
- APK `v1.0` không đổi. Không gọi model trả phí trong phiên này. PR #50 ghi một lần đo grok thật khoảng 0,5 USD đã chạy trước đó, không nằm trong commit.

## Bổ sung · OSA-040 Android văng khi nối · cursor · 11/11/2026

Đã merge PR #47 tại `3c631a3`. Head `9b931f6`. S22 Ultra đăng nhập được ngày 11/11/2026. APK release `v1.0`, SHA-256 `e3cb6a28d4df9917342be429bb50ebf4ba4fc52fa0c73407b183ac93d65df58d`. Đoạn dưới là lúc đang làm, trước merge.

Demo trên Linux (xvfb, WebKit): server giả `127.0.0.1:8799`. Lần đầu `add_capability` panic `UnknownManifest { key: "app manifest" }`, khóa ACL bị độc, luồng giao diện abort. Sau khi khai báo lệnh trong `build.rs` và capability `main-setup`, cùng demo ghi `GET /manifest.json` (ureq) rồi `GET /` (WebKit) và process không chết. `cargo test --offline --lib`: 9 passed.

Emulator API 34 x86_64, APK debug cùng commit: nối `http://10.0.2.2:8799` mở được trang, mở lại không chết, địa chỉ cổng 1 hiện lỗi và ở lại trang nhập. logcat không FATAL. APK arm64 ký v2, `resources.arsc` Stored, SHA-256 `ac5b12a3e9d1850578c1f4398e6ef4e8b86450ee4aac10df7747a876ad7ac8f5`, chưa chạy trên điện thoại. Không gọi model trả phí.

## Bổ sung · PR #43, #44 đã merge · e27 còn xfail · hoplite · 10/11/2026

Append. BOARD cũ ghi P0-2 chưa nhận và EVAL-SUITE chờ PR. Đó là trạng thái lúc viết.

[PR #44](https://github.com/VagabondKingsman/open-super-agent-remake/pull/44) merge tại `feeae4c`, `merged_at` `2026-11-10T17:18:58Z`. [PR #43](https://github.com/VagabondKingsman/open-super-agent-remake/pull/43) merge tại `b961870`, `merged_at` `2026-11-10T17:19:21Z`. CI push trên `b961870` FAIL: e27 XPASS strict vì YAML còn `xfail` sau khi `resolve_approval` đã chặn bot. Sửa nằm ở OSA-038.
