# Kiểm định Chất lượng (QA) và Đóng gói Phát hành

## 1. Danh mục kiểm tra theo từng trạng thái (State Matrix QA)

| Nhóm kiểm tra | Cách thực hiện | Tiêu chí đạt (Pass Criteria) |
|---|---|---|
| **Điều khiển thủ công** | Giữ nguyên bước đầu của trang ở 0s, 30s, 120s | Không tự động nhảy bước, không tự mở kết luận khi người nói chưa bấm |
| **Độ phủ nhánh (Branches)** | Duyệt qua bước đầu, bước giữa, bước cuối và mọi bộ lọc/trạng thái lỗi | Chữ trên DOM và mô hình 3D khớp trạng thái 100%; các ô thiếu dữ liệu hiển thị rõ nhãn |
| **Bàn phím & Truy cập** | Dùng `Tab`, `Space`/`Enter`, `ArrowLeft`/`ArrowRight`, `PageDown` | Kích hoạt được mọi tương tác mà không cần chuột; không bị kẹt focus trong dropdown |
| **Tạm dừng (Pause)** | Nhấn phím tắt Pause hoặc bật `prefers-reduced-motion` | Cả vòng lặp `requestAnimationFrame` lẫn hiệu ứng chuyển động CSS đều dừng hoàn toàn |
| **Đo kiểm giao diện** | Chạy `measureSlideUI()` từ `scripts/measure-ui.js` trên từng trạng thái | `orphanLastLines` = 0; `columnGapStagePx` và `footerGapStagePx` đạt ngưỡng; `widthDensityRatio` >= 1 (hoặc khớp mức trần cấu hình) |
| **In ấn & Xuất PDF** | Kích hoạt in/xuất PDF và kiểm tra từng trang | Đủ số trang, không có trang trắng thừa, không mất chữ hoặc lệch bố cục |
| **Chạy độc lập (Offline)** | Mở file trong môi trường ngắt mạng | Phông chữ, thư viện, dữ liệu và hình ảnh nội bộ hiển thị đầy đủ không lỗi |

## 2. Cách sử dụng `scripts/measure-ui.js`

Có thể nạp script vào trình duyệt tự động (Playwright/Selenium) hoặc dán vào DevTools Console:

```js
await page.addScriptTag({ path: 'scripts/measure-ui.js' });
const report = await page.evaluate(() => globalThis.measureSlideUI());
```

Lưu ý: `measure-ui.js` giúp bắt nhanh các lỗi định lượng (dòng mồ côi, hẹp khoảng cách cột/footer, độ phân giải canvas thấp), nhưng **không thay thế bước nhìn trực tiếp ảnh render (Visual Critique)** để đánh giá bố cục, ánh sáng và độ tương phản màu sắc.

## 3. Quy trình đóng gói bàn giao

1. Chốt dữ liệu, chạy lại bản build và chụp ảnh dự phòng (nếu có thay đổi mô hình 3D).
2. Chạy kiểm tra tự động + kiểm tra trực quan trên các trang.
3. Đóng gói tách biệt:
   - **Gói trình chiếu (Viewer Package):** File HTML tự chứa (hoặc thư mục kèm tài nguyên nhẹ), bản PDF xuất sẵn và ghi chú người nói.
   - **Gói mã nguồn (Source Package):** Dữ liệu gốc, style, script runtime/scene và hướng dẫn build lại.
