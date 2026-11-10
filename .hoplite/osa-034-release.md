APK debug arm64 để cài thử trên điện thoại. Không phải bản release, ký bằng khóa debug của Android.

- File: `OpenSuperAgent-debug.apk`
- SHA-256: `230ef2d3a124c62430b545bea3aab518981e259c1c37b1162e31ad5196e1f4bd`
- Code: `08d7f76` trên `hoplite/osa-036-android-switch`
- Máy: Android 7 trở lên, CPU arm64
- Gỡ app cũ trước khi cài. Không gọi `navigate`. Nút đổi server xóa địa chỉ đã lưu rồi mở lại trang kết nối.
- `resources.arsc` không nén. Chữ ký v2/v3.
- Chưa chạy trên máy ảo. Sandbox không có KVM.
