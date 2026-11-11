# Phiên 2026-11-11 · cursor · OSA-040

- Bắt đầu khoảng 12:16, kết thúc khoảng 12:40, Asia/Saigon (UTC+7).
- Repo `VagabondKingsman/open-super-agent-remake`. Base `dac00da` (`i18n-vi`, merge PR #45). Branch `cursor/android-connect-crash-efeb`.
- Việc: app Android tự văng khi nối server. Mô tả trong PR #32: hàng đợi webview 8 chỗ, `navigate` làm đầy, process chết, URL đã lưu nên lần mở sau cũng chết. Bản `49af947` đã bỏ `navigate` nhưng điện thoại chưa được kiểm.
- Skill Flow: osa-dev → ai-work-method → vibecode-kit.

## Đã thấy

Demo Linux, `OSA_ANDROID_URL=http://127.0.0.1:8799`, xvfb, binary `android/src-tauri`. Probe ureq tới `/manifest.json` thì xong. Ngay sau đó process abort.

Panic: `tauri-2.12.5/src/ipc/authority.rs:180`, `UnknownManifest { key: "app manifest" }`. `grant` gọi `add_capability` với `allow-android-*`. Các permission này thuộc manifest app, manifest đó không được nhúng. `unwrap` nổ trong lúc đang giữ khóa `runtime_authority`. Khóa bị độc. Luồng webview `lock().unwrap()` rồi abort.

`wry 0.57.2` `android/main_pipe.rs` dùng `bounded(8)` và `send()` chặn. Code hiện không gọi `.navigate(`.

## Đã sửa

1. `build.rs` khai báo 8 lệnh. Build sinh permission `allow-*` / `deny-*` và nhúng `__app-acl__`.
2. `capabilities/default.json` cho cửa sổ local `main`, để trang nhập địa chỉ vẫn gọi được lệnh sau khi có manifest app.
3. Capability remote lúc nối thêm `core:default` và bốn lệnh `android_*`. Không đưa `choose_remote` cho trang server.
4. Probe `/manifest.json` trước khi ghi URL và trước khi trang `location.replace`. Lỗi trả về chữ, không làm chết process. Lần mở lại cũng probe trước.
5. `usesCleartextTraffic` mặc định `true`, vì server OSAR trên LAN là HTTP. Bản debug vốn đã bật.
6. `RunEvent::Opened` chỉ biên dịch trên macOS và mobile, để bản demo Linux dựng được.

## Evidence

| AC | Kết quả | Bằng chứng |
|---|---|---|
| `cargo test --offline --lib` | PASS | 9 passed, 0 failed |
| Probe từ chối cổng đóng, không panic | PASS | `probe_refused_is_an_error_not_a_panic` |
| `http://192.168.1.10:8765` giữ HTTP | PASS | `explicit_http_stays_http` |
| Không gọi `.navigate(` | PASS | `shell_does_not_call_webview_navigate` |
| Send thứ 9 vào kênh 8 chỗ thì chặn | PASS | `ninth_pipe_send_blocks_until_drained` |
| Demo nối server giả | PASS | Log `/tmp/osa-android-demo.log`: `GET /manifest.json` ua ureq, rồi `GET /` ua WebKit. Process còn sống, không còn dòng panic |
| Panic trước khi sửa | FAIL rồi sửa | `UnknownManifest` trong `/tmp/osa-android-shell.log` của lần chạy đầu |
| APK, emulator, điện thoại lúc viết mục trên | NOT_CHECKED | SDK chưa cài ở mục đó |

## Bổ sung · emulator · 12:55 Asia/Saigon

SDK, NDK 29.0.14206865, emulator, image `aosp_atd` API 34 x86_64. `/dev/kvm` mở cho user của phiên.

| AC | Kết quả | Bằng chứng |
|---|---|---|
| APK debug x86_64 cài và chạy | PASS | `adb install` Success. SHA lúc chạy `14dae2a5fcb6d800e176ed03f9a9664130572c6a49c8c433c8b633013a8b5343`. File bị bản arm64 ghi đè sau |
| Nối `http://10.0.2.2:8799` | PASS | Server giả: `GET /manifest.json` rồi `GET /`. WebView thành `http://10.0.2.2:8799/`. pid 1830 còn sống. logcat không FATAL |
| Mở lại khi đã lưu server | PASS | `force-stop` rồi `am start`. Thêm một lượt manifest và `/`. pid 1999. Vẫn ở trang server. Không FATAL |
| Địa chỉ chết `http://10.0.2.2:1` | PASS | Ở lại `http://tauri.localhost/`. Hiện lỗi connection refused. pid 2113 không đổi. Không FATAL |
| APK debug arm64 | PASS file, chưa chạy | `lib/arm64-v8a`, `resources.arsc` Stored, zipalign 4 exit 0, apksigner v2. SHA-256 `ac5b12a3e9d1850578c1f4398e6ef4e8b86450ee4aac10df7747a876ad7ac8f5` |
| Điện thoại S22 | NOT_CHECKED | Không có máy |
| Probe cũ không ghi đè probe mới | PASS | Codex P1 trên PR #47. `ProbeGate`: lượt sau `bump` thì lượt trước `is_current` false. `cargo test --lib`: 10 passed. Emulator không chạy lại cho mục này |
| S22 văng sau mật khẩu | Sửa, điện thoại chưa kiểm lại | Trang login là HTML, chưa gọi native. Sau POST `/login` SPA gọi `setBadge`. JNI 0.21 không `ExceptionClear`, thread detach khi còn exception thì process chết. `setCount` chuyển lên UI thread và nuốt lỗi. APK mới SHA `e3cb6a28d4df9917342be429bb50ebf4ba4fc52fa0c73407b183ac93d65df58d`. Máy này không vào được hostname tailnet (dạng `<máy>.<tailnet>.ts.net`) |

- Paid usage: 0.
- Không đụng DB thật, không gửi channel.
