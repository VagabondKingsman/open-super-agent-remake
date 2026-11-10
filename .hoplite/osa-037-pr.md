## Summary
- Link cùng site và trang OAuth trên Android mở `SheetActivity`, không tạo webview wry thứ hai.
- URL khác origin đi ra trình duyệt hệ thống.
- Activity dùng chung cookie với webview chính.
- Số việc chờ duyệt thành shortcut trên icon. Số 0 thì gỡ. Không phải chấm đỏ launcher.

## Verification
- `tauri android build --debug --apk --target aarch64` PASS.
- APK ký debug, căn trang PASS. `resources.arsc` Stored. SHA-256 `33aaa4fdd81a828200fb8a5f59d721f170f9159dea70af9c8769d4cbb12564ee`.
- Máy ảo: NOT_CHECKED. Không có `/dev/kvm`.
- Điện thoại thật: chưa cài.
- Push chưa làm. Cần Firebase.
