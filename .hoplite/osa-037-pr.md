## Summary
- Link cùng site và trang OAuth trên Android mở `SheetActivity`, không tạo webview wry thứ hai.
- URL khác origin đi ra trình duyệt hệ thống.
- Activity dùng chung cookie với webview chính.
- Số việc chờ duyệt thành shortcut trên icon. Số 0 thì gỡ. Không phải chấm đỏ launcher.

## Verification
- `tauri android build --debug --apk --target aarch64` PASS.
- `openSheet` chờ activity đóng rồi mới trả về.
- APK ký debug, căn trang PASS. `resources.arsc` Stored. SHA-256 `a095f23e247ae0dac07a26d064f2dc3094f15b7853997cc3ef8575e4cefd6f24`.
- Máy ảo: NOT_CHECKED. Không có `/dev/kvm`.
- Điện thoại thật: chưa cài.
- Push chưa làm. Cần Firebase.
