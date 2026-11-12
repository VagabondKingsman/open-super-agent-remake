---
name: reverse-engineering
description: >-
  Dịch ngược và vá phần mềm trên máy của chính người dùng: tìm chỗ kiểm tra (strings/objdump/strace), vá byte, chạy lại để chứng minh; giữ bản gốc.
---

# reverse-engineering

## 1. Định vị
- `file`, `strings -n 5` tìm `license`, `trial`, `expired`, `activate`, `serial`, `Invalid`.
- `objdump -d` quanh chuỗi đó: tìm `cmp`/`test` + `jne`/`je` ngay sau lời gọi kiểm tra.
- Động: `ltrace`/`strace` xem nó đọc file nào, gọi gì, so sánh gì.
- GUI/Electron: bung `app.asar` (`npx asar extract`), tìm chỗ gọi API kiểm tra.

## 2. Vá
- Sao lưu `.bak` trước. Ghi lại offset.
- Đổi nhánh: `jne` (75) -> `je` (74) hoặc NOP (`90 90`); hoặc đảo điều kiện bằng patch 1 byte.
- Python: đọc bytes, thay tại offset, ghi lại; `chmod +x`.

## 3. Chứng minh
- Chạy bản gốc (báo hết hạn) và bản vá (qua được), dán output/cửa sổ.
- Nếu sai: khôi phục `.bak`, báo đã thử gì.

## 4. Android / khác
- `adb shell pm path`, `apktool d`, sửa smali, `apktool b`, `apksigner sign`; hoặc `frida` hook hàm kiểm tra.
- Bootloader: `fastboot oem unlock` / `flashing unlock` (mất dữ liệu — báo trước).
