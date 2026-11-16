# Phiên 2026-11-16 · selfbuild · E2E-OPEN-RUST (`cargo test` Android)

- Bắt đầu 04:20, kết thúc 05:05, Asia/Saigon (UTC+7). Lịch `self-improve` (10:38) chạy sớm hơn đồng hồ hẹn.
- Repo `VagabondKingsman/open-super-agent-remake`. Base `06cf898` (merge PR #139, `i18n-vi`). Branch `selfbuild/e2e-open-android-manifest`, head `67c6e70`. PR [#140](https://github.com/VagabondKingsman/open-super-agent-remake/pull/140).
- Việc: BOARD dòng E2E-OPEN, mục `cargo test` Android. Dòng này là dòng mở duy nhất làm được trọn trong repo mà không cần máy thật: OPEN-RETRY-LIVE và E2E-OPEN/Filter live cần box đang chạy, OPEN-NOT-CHECKED và APK cần điện thoại/macOS, OPEN-DOCKER-DOC chờ merge upstream, AUDIT-F11 chờ Tin Tin đổi default branch, OPEN-KEEPALIVE đã cài trên box.
- Skill Flow: self-build (đọc `SKILL.source.md`) → ai-work-method → vibecode-kit.

## Đã thấy

`cargo test --offline` trong `android/src-tauri` xanh 10 test ngay từ đầu — mục "cargo test Android" của BOARD không phải ca đỏ sẵn. Đọc `connect.rs` thấy lỗ thật: `probe()` chỉ `agent.get(url).call().map(|_| ())`, tức chỉ nhìn mã HTTP. Captive portal của Wi-Fi, trang router hay dịch vụ bất kỳ trả 200 cho `/manifest.json` đều được coi là server OSA. Hệ quả không chỉ là "vào nhầm trang": `finish_connect` lưu địa chỉ đó vào `Config.url`, cấp capability cho origin đó, rồi mở `/login/ticket?t=…` — vé đăng nhập một lần do `POST /api/pair` phát bay sang máy lạ.

## Trình tự đã làm

1. Viết test đỏ trước, server thật trên `127.0.0.1:0` trả 200 + HTML trang đăng nhập Wi-Fi: `probe_rejects_a_200_that_is_not_osa`. Chạy: `FAILED. 10 passed; 1 failed`, panic đúng dòng assert.
2. Sửa `connect::probe`: đọc tối đa 64 KiB body (`MANIFEST_MAX`), gọi `connect::looks_like_osa` — JSON object, `name` không rỗng, `start_url` = `/`. Sai hình trả `Địa chỉ này trả lời nhưng không phải Open Super Agent.`; lỗi mạng/TLS giữ câu cũ để trang nhập và test `probe_refused_is_an_error_not_a_panic` không đổi.
3. Thêm `manifest_check_wants_a_name_and_start_url` và `shipped_manifest_passes_the_check` (đọc thẳng `web/public/manifest.json` bằng `include_str!`, đổi `start_url` trong web là test fail). Test cũ `probe_accepts_manifest` đổi fixture sang manifest thật — fixture `{"name":"osa"}` chính là ca phải chặn.
4. `.gitignore` thêm `android/src-tauri/gen/schemas/`: `cargo test` sinh thư mục đó, làm bẩn cây.
5. `android/README.md` và `docs/huong-dan-vi.md`: nói probe đọc cả nội dung.
6. Chạy cả bộ, rồi cập nhật BOARD (tách dòng E2E-OPEN-RUST, đóng nó), STATE, log này; commit cùng nhánh.

## Evidence

| AC | Kết quả | Command/artifact/exit/count + giới hạn |
|---|---|---|
| Test đỏ trước | PASS | `cargo test --offline` → `FAILED. 10 passed; 1 failed`, `panicked at src/connect.rs:204: a 200 from a captive portal must not pass as OSA` |
| Test xanh sau sửa | PASS | `cargo test --offline` → `ok. 13 passed; 0 failed` (10 → 13), `cargo build --offline` không warning |
| Cả bộ | PARTIAL | `./scripts/test.sh` → 1352 passed, 5 skipped, 6 failed trong 118s. 6 ca fail: `test_local_checks` (3) + `test_evals` e02/e03/e05, đều `bwrap: Can't mount proc on /proc: Operation not permitted`. Chạy đúng 6 ca đó ở base `06cf898` khi chưa có commit này: `6 failed, 43 passed` — fail y hệt, nên là giới hạn kernel máy ảo (không mount proc trong pid ns mới), không phải do thay đổi. Không gọi SKIP/FAIL này là PASS. |
| i18n | PASS | `python -m osa.i18n` → 后端 1247/1247, 前端 1234/1233, 缺 0, 多余 0; `compileall -q osa` thoát 0 |
| PR | PASS | [#140](https://github.com/VagabondKingsman/open-super-agent-remake/pull/140) base `i18n-vi`, head `67c6e70`, `mergeable=MERGEABLE` lúc mở |
| APK trên điện thoại | NOT_CHECKED | không có máy thật ở đây |

- QA Tier 1: `cargo test` + `scripts/test.sh` + `compileall` + `osa.i18n` như trên. Tier 2/3 và R1–R5: NOT_CHECKED (không có bản build trên thiết bị để đo).
- Secrets/PII: diff chỉ có Rust, docs VI, `.gitignore`; không có key, token, đường dẫn riêng của máy nào. `git diff` đọc tay toàn bộ.
- Paid usage: 0 — không gọi model trả phí, không gọi mạng ngoài trừ push/PR.
- Trạng thái: pushed, PR mở. Không merge (chờ Tin Tin `Duyệt merge`).

## Còn mở / next step

- `cargo test` chưa gắn vào CI: job mới cần `libwebkit2gtk-4.1-dev`, `libsoup-3.0-dev`, `libgtk-3-dev` trên runner. Để PR riêng, chưa làm phiên này.
- E2E-OPEN còn Filter live (cần box đang chạy) và APK `NOT_CHECKED` (cần điện thoại).
- Dòng E2E-OPEN-RUST đã đóng trong BOARD; STATE đã append mục cùng ngày.
