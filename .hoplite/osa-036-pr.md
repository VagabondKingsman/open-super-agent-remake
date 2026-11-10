## Summary
- Nút Đổi server trên Android trước đây không làm gì, vì `navigate` đã bị bỏ để tránh văng app.
- Lệnh xóa địa chỉ đã lưu. Trang chờ lệnh xong rồi mới tải `http://tauri.localhost/`.
- Lỗi invoke trên trang kết nối hiện lên màn hình, không nuốt im.

## Verification
- `tauri android build --debug --apk --target aarch64` PASS trên `08d7f76`, trước khi sửa race.
- APK của commit đó: ký debug, căn trang PASS. SHA-256 `230ef2d3a124c62430b545bea3aab518981e259c1c37b1162e31ad5196e1f4bd`.
- Head `8eaac9b` chỉ đổi thứ tự JS: chờ lệnh xong rồi mới `location.replace`. Chưa build lại APK.
- Máy ảo: NOT_CHECKED. Không có `/dev/kvm`. Điện thoại thật: chưa cài.
