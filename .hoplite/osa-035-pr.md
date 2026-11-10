## Summary
- App văng khi nhập địa chỉ server, và văng tiếp mỗi lần mở lại.
- Hàng đợi webview Android chỉ chứa 8 lệnh. `navigate` làm đầy hàng rồi process chết, kể cả khi gọi trên luồng giao diện. URL đã lưu nên lần mở sau cũng chết.
- Bỏ `navigate`. Trang kết nối đọc URL từ `setup_state` rồi `location.replace`. iOS vẫn dùng `navigate` vì WKWebView không có hàng đợi này.

## Verification
- `tauri android build --debug --apk --target aarch64` PASS.
- APK ký debug, `resources.arsc` không nén, căn trang PASS, chữ ký v2/v3 PASS.
- Máy ảo Android: NOT_CHECKED. Sandbox không có `/dev/kvm`.
- Điện thoại thật: bản `d0c56c1` vẫn văng. Bản này là `49af947`.

## Test plan
- [ ] Gỡ app cũ, cài APK mới.
- [ ] Nhập địa chỉ server. App không văng, mở được trang web.
- [ ] Thoát app, mở lại. Vẫn vào server đó.
