## Summary
- Thêm `android/`: app Tauri chỉ mở trang web của server OSA. QR `opensuperagent://pair` đổi vé một lần rồi vào `/login/ticket`.
- Web coi `platform: android` là điện thoại, cùng chỗ với iOS. Chat, thẻ xác nhận và Computer là giao diện web đó.
- Chưa có push, badge, trang nổi, hay APK. App iPhone không đổi. Windows chưa làm.

## Verification
- `cd web && npm test`: 34 pass, 0 fail.
- `cd web && npm run typecheck` sạch.
- APK debug arm64: PASS biên dịch. File `android/src-tauri/gen/android/app/build/outputs/apk/universal/debug/app-universal-debug.apk`, 156 MB, có `lib/arm64-v8a/libosa_android_lib.so`.
- Lỗi biên dịch đã sửa: `state(app)` tạm bị hủy khi còn giữ khóa trong `grant` và `connect` (`E0716`).
- Cài lên điện thoại và mở UI: NOT_CHECKED. Sandbox không có máy Android, không có emulator.

## Test plan
- [ ] Máy có Rust: `cargo test` trong `android/src-tauri`.
- [ ] Máy có Android SDK: `tauri android init` rồi build APK.
- [ ] Quét QR từ Cài đặt → Điện thoại, vào đúng server, chat và xác nhận như web.
