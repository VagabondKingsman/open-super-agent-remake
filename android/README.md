# App Android

Vỏ cho điện thoại Android. OSA vẫn chạy trên server. App chỉ mở trang web của server đó.

## Cài bản đã phát hành

Bản arm64 để cài thử nằm ở release `v1.0`:

<https://github.com/VagabondKingsman/open-super-agent-remake/releases/tag/v1.0>

File `OpenSuperAgent-v1.0-arm64-debug.apk`. Ký bằng khóa debug của Android, không phải bản cửa hàng. Máy cần Android 7 trở lên và CPU arm64. Gỡ app cũ trước khi cài. Server trên LAN hoặc Tailscale nhập `http://máy:8765`, ví dụ `http://máy.ts.net/`. Đừng thêm `https://` nếu server không có chứng chỉ mà WebView tin.

Đã kiểm trên Samsung Galaxy S22 Ultra ngày 11/11/2026: nối server, đăng nhập, vào được chat của AutoBot và Nova. Cài đặt hiện đúng tên server và có nút Đổi máy chủ.

## Cách nối

1. Mở app, nhập địa chỉ, bấm Kết nối. App gọi `GET /manifest.json` trước. Không tới được thì ở lại trang nhập và hiện lỗi.
2. Trang mật khẩu là form của server, `POST /login`. Đúng mật khẩu thì vào giao diện web.
3. QR `opensuperagent://pair?u=<server>&t=<vé>`. Vé do `POST /api/pair` phát, sống 5 phút, dùng một lần. App mở `/login/ticket?t=...`.

Bản `v1.0` đã phát hành dùng ô `type=url`, nên phải gõ đủ `http://` hoặc `https://`. Code sau bản đó để ô là text: tên không scheme được Rust hiểu là `https://`. `http://` giữ nguyên. HTTP được phép vì server trên LAN là HTTP.

## Việc app làm và không làm

- Nhớ server lần mở sau. Probe lại trước khi nhảy vào trang. Probe cũ không ghi đè server vừa chọn.
- Không gọi `WebviewWindow::navigate`. Hàng đợi webview Android của wry 0.57.2 chỉ chứa 8 lệnh. `navigate` làm đầy hàng thì process chết.
- Sau khi vào trang chính, app cập nhật shortcut "pending" theo số thẻ chờ duyệt. Lệnh này chạy trên UI thread. Exception JNI được xóa trước khi thread detach, để app không chết ngay sau đăng nhập.
- Trang nổi cùng server (`openSheet`) và link khác server mở bằng trình duyệt máy.
- Chưa có push Firebase.

Logic địa chỉ và vé nằm ở `src-tauri/src/connect.rs`. Chạy `cargo test --lib` trong `src-tauri`. Lần đầu cần mạng để Cargo tải crate. Không cần Android SDK. Lần chốt v1.0, máy đã có cache: 10 passed.

Build APK cần Rust, Android SDK, NDK và `npx tauri android build --debug --apk --target aarch64` trong thư mục `android/`. CI của remake không build APK. Thư mục `gen/` đã có trong cây.
