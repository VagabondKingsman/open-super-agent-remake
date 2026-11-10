## Summary
- PR #45 đã merge tại `dac00da`.
- App Android giữ địa chỉ `http://IP:cổng` thay vì ép sang HTTPS.
- Bản Android bật cleartext. Kiểm tra `/manifest.json` của host LAN chấp nhận chứng chỉ tự ký.

## Verification
- `tauri android build --debug --apk --target aarch64` PASS.
- APK ký debug, căn trang PASS. `resources.arsc` Stored. SHA-256 `24838d930ada03fe3ede41012b629353360f9e7ab3f487c31e4db2631bc7add0`.
- S22 Ultra: NOT_CHECKED. Không có máy trong sandbox.
- WebView chính vẫn từ chối HTTPS tự ký. Dùng `http://` trên LAN.
