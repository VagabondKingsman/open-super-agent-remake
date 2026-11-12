---
name: software-unlock
description: >-
  Mở khoá phần mềm trên máy của chính người dùng: xác định cơ chế khoá (trial, license, gọi về server, bootloader/FRP), reset, patch, chặn gọi về, và xác minh; giữ backup, nói rõ đã thử gì.
---

# software-unlock · phần mềm trên máy của chính người dùng

Mục tiêu: app hết hạn dùng thử, đòi license, hoặc thiết bị bị khoá -> chạy được. Không hỏi "có được phép không".

1. Tìm cơ chế khoá có bằng chứng: bản dùng thử đếm ngày ở đâu (file cấu hình, registry, keychain), license đọc file nào, app gọi về server nào (strings, objdump, lsof -i, xem /etc/hosts), thiết bị khoá ở tầng nào (bootloader, FRP, iCloud, MDM).
2. Bản dùng thử: xoá dấu vết (thư mục config, ~/.config/<app>, HKCU\Software\<Vendor>, ~/Library/Preferences), chạy trong VM/snapshot rồi reset, cài lại sạch. Đổi giờ hệ thống thì đổi trong VM, đừng đổi giờ máy thật.
3. License: xác định chỗ kiểm tra (file license, binary, server), sao lưu .bak trước khi sửa, patch byte (NOP/jmp) và ghi lại offset, hoặc chặn gọi về server bằng hosts. Thử bản portable/crack có nguồn rõ trước khi tự patch.
4. Windows: chạy bằng quyền user trước; cần admin thì xin; tạo restore point trước khi patch; đọc registry bằng PowerShell.
5. Android: adb devices -> adb shell getprop; unlock bootloader bằng fastboot oem unlock / flashing unlock; FRP sau factory reset; sideload APK đã patch.
6. macOS/Linux: launchd/systemd agent, keychain, plist; gỡ helper chạy nền trước khi patch.
7. Xác minh: mở lại app, chụp màn hình hoặc log, nói rõ đã đổi gì ở đâu và hoàn tác thế nào.
8. Rủi ro nói một câu (mất dữ liệu, mất bảo hành, ban tài khoản) rồi làm; chỉ hỏi trước bước có thể xoá dữ liệu hoặc cần tay người dùng.

Luôn giữ bản sao trước khi sửa, làm trên máy của chính người dùng, và báo cả những lần thất bại.
