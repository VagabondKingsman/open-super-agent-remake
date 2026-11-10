# Sửa audit F1–F13 và deep test trên box · 10/11/2026

Giờ theo Asia/Saigon (UTC+7). Đồng hồ box chạy UTC, mọi giờ dưới đây đã cộng 7.

- Yêu cầu (t77u): sửa các điểm audit còn lại, cập nhật lên bot đang chạy trên máy ảo, deep test tới khi xong.
- Base: `origin/i18n-vi` = `91b6cfb` (merge PR #40). Worktree `/workspace/osar-fix`, nhánh `fix/audit-f1-f12`. Worktree cũ `/workspace/osar-audit` đã gỡ (nhánh của nó đã merge).
- Skill Flow: osa-dev, ai-work-method, vibecode-kit (debug 9 bước cho lỗi tìm ra lúc live), unslop-vi cho văn bản tiếng Việt.
- SHA trong bảng và các mục dưới là SHA local trên box. Cloud agent `git am` ra SHA khác, xem mục "Merge" cuối file.

## Sửa gì

| ID | Sửa | Chỗ | Test |
|---|---|---|---|
| F1 | Chunk đầu có giới hạn riêng `limits.stream_first_chunk_s` (170 giây). `stream_idle_s` chỉ đếm giữa hai chunk sau chunk đầu | `osa/providers.py` `stream_first_chunk_s`, `guard_stream` | `test_slow_first_chunk_within_first_limit_is_not_a_stall`, `test_first_chunk_never_comes_is_a_stall`, `test_mid_stream_gap_uses_idle_limit_not_first_limit`, `test_guard_stream_explicit_limits`, `test_idle_limit_shorter_than_watchdog` |
| F2 | Router gọi lại thì gửi `{"type":"stream","reset":true}`, web xóa phần thinking đang hiện (`web/src/streamDelta.ts`). Router và Worker ghi usage của lượt hỏng bằng `memory.record_partial` (không có usage thì ước tính, `estimated=1`) | `osa/router.py`, `osa/worker.py`, `web/src/store.ts` | `test_router_retry_resets_shown_thinking_and_records_usage`, `test_worker_failed_attempt_usage_is_recorded`, `web/tests/stream-reset.cjs` |
| F3 | Chờ `providers.retry_pause(attempt)` trước khi gọi lại: 2–5 giây có jitter. Test thay hàm này nên không phải chờ thật | `osa/providers.py` `stream_retry_delay`, `retry_pause` | `test_retry_delay_between_2_and_5_seconds`, `test_retry_pause_uses_delay`, `test_worker_retry_waits_before_calling_again` |
| F4 | `fit_bounds` kẹp `left`/`top` vào trong màn hình | `osa/computer/cdp_helper.py` | `test_small_task_window_is_enlarged` (sửa kỳ vọng), `test_enlarged_window_clamped_on_screen`, `test_fit_bounds_keeps_position_when_it_fits` |
| F13 | Lúc test live: màn hình X của VM là 661x1619 (người xem VNC đổi cỡ), không phải 1280x800. `fit` cứ đặt bề ngang 1280, window manager cắt lại 661, nên thao tác nào cũng `setWindowBounds` rồi chờ 0,3 giây. Giờ `fit` đọc `screen.availWidth/availHeight` của trang và chỉ phóng tới màn hình thật | `osa/computer/cdp_helper.py` `Ctx.screen`, `fit` | `test_fit_respects_real_screen_smaller_than_settings` |
| F6 | Linux không có `DISPLAY` và `WAYLAND_DISPLAY`: `host.status()` báo lỗi ngay (vi/en, nhắc `xvfb-run -a`), không chạy helper. Lỗi 20 giây của helper được dịch, thiếu màn hình thì thêm gợi ý | `osa/computer/host.py` `no_display`, `helper_error` | `test_linux_without_display_fails_fast`, `test_helper_debug_port_error_translated` |
| F7 | Cảnh báo thiếu `OSA_PASSWORD` và toàn bộ output, help, lỗi của `python -m osa.backup` qua `i18n.t`, có số nhiều tiếng Anh | `osa/server.py`, `osa/backup.py`, `osa/locales/*.json` | `tests/test_backup_cli.py` |
| F8 | `osa-start.sh`: `OSA_PORT` (mặc định 8765, kiểm là số), chờ `/manifest.json` (`OSA_START_TIMEOUT`, mặc định 60 giây), server thoát sớm thì in log và thoát 1, ghi `logs/osa.port`. `osa-stop.sh` đọc cổng đó và chờ process thoát (`OSA_STOP_TIMEOUT` 20 giây) | `scripts/` | `tests/test_start_script.py` (uv giả chạy `http.server`) |
| F9 | Ba dòng comment `stream_first_chunk_s`, `stream_idle_s`, `stream_retries` trong `limits:` của `config.yaml`. Thử trên bản clone: commit này rồi `stash pop` bản sửa `idle_pause_s` thì tự gộp | `config.yaml` | `test_config_yaml_documents_stream_defaults` |
| F10 | `docs/docker.md` viết lại bằng tiếng Việt, clone `-b i18n-vi` từ repo remake. Lần merge upstream sau sẽ đụng file này | `docs/docker.md` | `test_docker_doc_clones_the_remake_branch` |
| F12 | File `.osabak` `chmod 0600` ngay sau khi mã hóa | `osa/backup.py` | `test_exported_backup_is_owner_only`, `test_cli_export_output_translated` |
| F11 | Không sửa. Đổi nhánh mặc định GitHub là việc của Tin Tin | BOARD | — |

## Cổng kiểm (trên `76b45da`, nhánh sửa)

- `compileall` OK, `import osa.server` OK, `osa.catalog` 40 app, `osa.templates` PASS, `skillpacks verify-sources` 129 file PASS.
- `osa.i18n`: backend 1214 câu (trước 1187), en/vi thiếu 0, thừa 0. Frontend 1211 câu, thiếu 0, 0 dòng chưa bọc.
- `env -u DISPLAY CI=1 OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs`: 853 passed, 1 skipped (`test_real_desktop`, cần macOS).
- `uv run pytest -q` trơn: 853 passed, 1 skipped.
- Web: `npm test` 36/36 (thêm 2), `tsc --noEmit` OK, `npm run build` OK.

## Deploy lên box

- 21:49: backup DB bằng sqlite backup API ra `/workspace/osa-backups/osa.db.pre-audit-fixes.20261110-144912` (quyền 0600, `integrity_check` ok, số dòng bots/chats/messages/llm_calls khớp). `config.yaml` chép ra `/workspace/osa-backups/config.yaml.local.20261110-144912` kèm `.diff`.
- Trong `/workspace/open-super-agent`: `git checkout -- config.yaml`, `git checkout -B deploy/audit-f1-f12 <sha>`, `git apply` lại diff `idle_pause_s`. Nhánh `fix/audit-f1-f12` đang mở ở worktree nên không check out cùng tên được. `uv sync --locked`, `npm run build` (dist không nằm trong git).
- Lần 1 (code `bb733ba`): pid 521313. Lần 2 sau sửa F13 (`76b45da`): `osa-stop.sh` báo `stopped 521313 (port :8765)`, `osa-start.sh` chờ `/manifest.json` rồi báo `started pid=523005` lúc 21:51:34.
- `/manifest.json` 200, đăng nhập 200, Computer `instabox` `running`, máy `docker-osar-test` (`current`). Keepalive pid 335522 vẫn chạy suốt.

## Deep test

- Smoke không dùng LLM (`/workspace/osar-audit-fixes-20261110/smoke.py`): bootstrap 200, 5 Bot, Computer status/start `running`, shell (Chromium 154), ghi/đọc file, chụp desktop, mở `https://example.com`, chụp trang.
- F4/TIP-04b trên VM: thu nhỏ cửa sổ task về 510x267 rồi kéo sang góc (WM đặt ở 628,600). Sau một thao tác `read`: 0,600 661x800, nằm trong màn hình 661x1619. Thao tác tiếp theo không đổi kích thước (read 0,5 giây). File `geometry.json`.
- Stream thật với xAI (`live_stream_guard.py`, không ghi DB): effort high, TTFT 1,53 giây, 63 chunk, không lỗi. Ép `idle_s=0.001` thì `StreamStalled` sau chunk đầu, stream thật được đóng. `retry_pause(1)` chờ 2,46 giây.
- Chat Nova (chat 1, message 285): stream 7 sự kiện thinking và 36 delta, trả lời sau 5,5 giây, không lỗi, không reset (không có lượt nào hỏng nên không gọi lại).
- Task #287 (Worker, example.com): `done`, 11 bước, $0.160. Kết quả BLOCKED đúng: example.com bây giờ không còn thẻ H1 (đã `curl` kiểm). Đây là lỗi đề bài, không phải lỗi OSA.
- Task #291 (Worker, `https://www.iana.org/help/example-domains`): `done`, 5 bước, $0.040, PASS. File trên VM `/data/workspace/audit-fix-heading.txt` = `Example Domains`.
- Không có Watchdog hủy, không có sự kiện `error`.
- Chi phí mới (llm_calls từ lúc deploy): $0.328 (router 5 lượt $0.115, worker 17 lượt $0.213). `today.cost` trên `/api/usage`: 11.968 → 12.296. Lượt gọi xAI trực tiếp trong `live_stream_guard.py` không vào DB (vài chục token).

## Còn lại

- Đường gọi lại Router/Worker chưa xảy ra tự nhiên trên live. Phần đóng stream thật và thời gian chờ đã chạy live, phần `reset` chỉ có test.
- `task_timeout_s` đang chạy 7200, từ `settings.overrides`. `config.yaml` ghi 600. Không đổi.
- Thông báo `StreamStalled` in `int(n)` nên ngưỡng dưới 1 giây hiện "0 giây". Chỉ gặp khi cấu hình ngưỡng dưới 1 giây.
- Docker Compose và `xvfb-run -a scripts/osa-start.sh` với server thật: `NOT_CHECKED`.

## Merge (cập nhật 22:20)

[PR #41](https://github.com/VagabondKingsman/open-super-agent-remake/pull/41), branch `fix/audit-f1-f13`, head `9bce42d`, merge vào `i18n-vi` tại `5a1e0e7` lúc 22:12:10. CI backend, frontend, docker xanh. Cây của `5a1e0e7` trùng cây local `b8ca2c0` mà box đang chạy.

| Local | Trên `i18n-vi` | Commit |
|---|---|---|
| `d0a1df6` | `da7e0c8` | F1/F2/F3 stream |
| `eb5cb12` | `e55f772` | F4 kẹp cửa sổ |
| `044c9de` | `8091dd8` | F6 Linux không màn hình |
| `5d6ca14` | `5953e0d` | F7/F12 i18n, backup 0600 |
| `d6787ab` | `54985f8` | F8 script |
| `7c20922` | `46403a7` | F9 `config.yaml` |
| `4f84ce6` | `5f8d7a3` | F10 `docs/docker.md` |
| `bb733ba` | `614d5f7` | docs |
| `76b45da` | `30ef779` | F13 cửa sổ theo màn hình thật |
| `b8ca2c0` | `9bce42d` | `.agents/` |

## Sau merge

- 22:08–22:13: script giữ VM gọi suspend/resume trước mốc 480 phút, cả hai trả 400 thiếu `Idempotency-Key`. 22:13 VM bị nền tảng pause, cooldown tới 22:18:18. 22:19 `POST /api/bots/1/computer/start` qua OSA trả 200, VM `running` lại. Không liên quan code PR #41. Ghi ở BOARD OPEN-KEEPALIVE.
