---
name: captcha-bypass
description: >-
  Vượt captcha theo thứ tự rẻ trước đắt sau: OCR cục bộ (tesseract), rồi 2Captcha, kèm mẹo nhận dạng loại captcha, audio fallback, giữ session.
---

# captcha-bypass

## 1. Nhận dạng trước khi giải
- Ảnh chữ đơn giản (4–6 ký tự): OCR cục bộ được. `solve_captcha_local` (tesseract, miễn phí).
- reCAPTCHA / hCaptcha / Turnstile: tìm `data-sitekey` hoặc `sitekey` trong HTML/JS; cần dịch vụ (`solve_captcha`, kind=recaptcha, sitekey + page_url).
- Slider/puzzle: chụp 2 ảnh, so sánh, hoặc đưa ảnh cho 2Captcha (kind=image).

## 2. Thứ tự
1. `solve_captcha_local` với path ảnh trên máy (hoặc base64). Trả về vài ứng viên; thử cái khớp.
2. Nếu sai: tiền xử lý (grayscale, phóng to ×2, threshold) rồi gọi lại; tesseract thích ảnh sạch, chữ to.
3. Vẫn sai: `solve_captcha` (2Captcha) — đắt hơn, chậm hơn nhưng chịu được captcha khó.
4. Audio captcha: tải file audio, `whisper` hoặc 2Captcha audio.

## 3. Mẹo giảm số lần gặp captcha
- Giữ cookie/session: cùng `browser_profile` cho cùng tài khoản (xem `browser_profile`).
- Chậm lại giữa các lần submit; dùng `take_proxy` để đổi IP khi bị chặn.
- Đăng ký hàng loạt: mỗi tài khoản một profile + một proxy, làm tuần tự, lưu lại tài khoản đã tạo.

## 4. Luật
Báo rõ: giải bằng gì, đúng/sai, bao nhiêu lần thử. Đừng giả vờ giải được khi chưa thử.
