## Summary
- Link cùng site và trang OAuth trên Android mở `SheetActivity`, không tạo webview wry thứ hai.
- URL khác origin đi ra trình duyệt hệ thống.
- Activity dùng chung cookie với webview chính.

## Verification
- `tauri android build --debug --apk --target aarch64` PASS.
- APK ký debug, căn trang PASS. `resources.arsc` Stored. SHA-256 `734f3c74af9cf037b37d71aca7fb7f4c7bc8fa9baeead84e4f53f30f221f15d0`.
- Máy ảo: NOT_CHECKED. Không có `/dev/kvm`.
- Điện thoại thật: chưa cài.
- Push và badge chưa làm. Push cần Firebase.
