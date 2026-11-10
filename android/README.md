# App Android

Vỏ cho điện thoại Android. OSA vẫn chạy trên server. App chỉ mở trang web của server đó.

Quét QR `opensuperagent://pair?u=<server>&t=<vé>`. Vé do `POST /api/pair` phát, sống 5 phút, dùng một lần. App mở `/login/ticket?t=...`. Sau đó chat, thẻ xác nhận và Computer là trang web.

Chưa có push, badge, hay trang nổi riêng. Link khác server mở bằng trình duyệt máy.

Chưa build được trong CI của remake: máy build cần Rust, Android SDK và `tauri android init`. Thư mục `gen/` do lệnh đó tạo, không commit. Logic địa chỉ và vé nằm ở `src-tauri/src/connect.rs`, chạy bằng `cargo test` khi có Rust.
