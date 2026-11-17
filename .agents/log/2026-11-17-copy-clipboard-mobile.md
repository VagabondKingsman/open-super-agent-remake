# Phiên 2026-11-17 · cursor · copy-clipboard-mobile

- Bắt đầu/kết thúc: 17:36–18:30 Asia/Saigon (10:36–11:30 UTC)
- Repo/base/branch: `origin/i18n-vi` = `63c99f6`, branch `fix/copy-clipboard-mobile`, head = commit này
- Approval/scope: operator báo trên chat OSA (web Android + app) nút sao chép hiện "đã sao chép" mà clipboard rỗng; phạm vi: sửa `copyText` phía web + test, không đụng backend
- Skill Flow/TIP/AC: không có task ID trên BOARD; AC tự đặt: (1) bấm sao chép trên http thật sự đưa chữ vào clipboard, (2) khi không copy được thì UI không được báo thành công, (3) có đường copy tay luôn dùng được

## Trình tự đã làm

1. Đọc `web/src/copyText.ts`, `Chat.tsx CopyBtn`, `Markdown` `.code-copy`: bản dist đã có fallback nhưng vẫn tin `execCommand('copy')` trả true; textarea nằm ngoài màn hình (`left:-9999px`) và có `readonly` — đúng hai thứ Android Chrome/WebView hay nuốt. App Android là Tauri WebView mở đúng URL http của tailnet, nên cũng rơi vào đường này.
2. Viết lại `copyText`: (a) clipboard API, (b) textarea trong viewport + `copy` listener tự đặt `clipboardData`, (c) contentEditable + range; thành công **chỉ** khi sự kiện `copy` thật sự bắn ra; (d) cả ba hỏng thì mở bảng chọn tay (long-press), kèm gợi ý https khi trang là http.
3. `web/tests/copy-text.cjs`: 6 ca, gồm ca `execCommand` trả true mà không có copy event (đúng kiểu Android) phải trả false và mở bảng.
4. Verify thật bằng Chrome headless (CDP) trên origin http không phải localhost (`169.254.0.21:18765` → socat → 127.0.0.1:8765): `isSecureContext=false`, `navigator.clipboard` undefined; bấm bằng `Input.dispatchMouseEvent` (có user activation) → đọc lại clipboard từ trang localhost (secure context) thấy đúng nội dung; thay `document.execCommand` bằng hàm chỉ trả true → nhãn "Không sao chép được" và bảng copy tay mở, đúng chữ.
5. `npm test` 55/55, `npm run build` OK, `python -m osa.i18n` 0 thiếu/0 thừa và 0 dòng chưa bọc t(), `tsc --noEmit` sạch.

## Evidence

| AC | PASS/FAIL/PARTIAL/NOT_CHECKED | Command/artifact/exit/count + giới hạn |
|---|---|---|
| AC-1 | PARTIAL | Chrome 157 headless, origin http private IP: clipboard đọc lại đúng chữ sau một cú bấm thật (`copy_verify5.py`). Chưa chạy trên máy Android thật |
| AC-2 | PASS | `node --test tests/copy-text.cjs` 6/6; và trên trang thật khi `execCommand` giả trả true: nhãn "Không sao chép được" |
| AC-3 | PASS | Bảng copy tay mở đúng lúc, textarea chứa đúng nội dung, có nút Đóng |

- Secrets/PII/private-path scan: diff chỉ 2 file web + CHANGELOG, không có key/URL riêng tư (origin test là IP link-local của chính máy).
- Paid usage: 0.
- Trạng thái: đã push branch, PR mở về `i18n-vi`.

## Còn mở / next step

- Android thật: cần operator thử lại trên S24/trình duyệt; nếu vẫn hỏng thì đường chắc chắn là **https**: `sudo tailscale serve --bg --https=443 http://127.0.0.1:8765` (tailnet đã có `CertDomains: osa.taila99125.ts.net`), sau đó mở `https://osa.taila99125.ts.net` — secure context nên `navigator.clipboard` có mặt cho cả web lẫn WebView app.
- App Tauri: nếu WebView vẫn chặn clipboard API (cần `onPermissionRequest`), bảng copy tay là đường dự phòng; đường native (plugin clipboard-manager) cần build APK mới, để PR riêng.
