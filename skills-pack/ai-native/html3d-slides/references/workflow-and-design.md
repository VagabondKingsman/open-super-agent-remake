# Thiết kế và Storyboard cho Slide HTML 3D

## 1. Từ Brief đến Storyboard

Mỗi trang slide cần trả lời rõ 6 câu hỏi trong storyboard trước khi viết code:

| Thành phần | Câu hỏi cốt lõi |
|---|---|
| **Mục đích** | Trang này giúp người xem hiểu hoặc ra quyết định gì? |
| **Thông điệp** | Câu kết luận quan trọng nhất (Action Title) của trang là gì? |
| **Vật mang nội dung** | Bảng dữ liệu, đoạn trích nguồn hay mô hình 3D nào chứng minh cho thông điệp? |
| **Bố cục (Layout)** | Chia tỷ lệ vùng đọc chữ (DOM) và vùng mô hình (3D) như thế nào để không chèn ép nhau? |
| **Tương tác & Trạng thái** | Khi bấm nút/chọn bộ lọc thì trạng thái thay đổi ra sao (kể cả trạng thái thiếu dữ liệu)? |
| **Ghi chú người nói** | Người trình bày sẽ dẫn dắt gì trước và sau mỗi thao tác bấm? |

## 2. Kiến trúc 3 lớp hiển thị

1. **Lớp Đọc (DOM Layer):** Chứa tiêu đề, văn bản, bảng số liệu, chú thích, nút điều khiển và mã QR. Giữ hoàn toàn trong HTML/CSS để đảm bảo độ tương phản cao, sắc nét trên mọi độ phân giải, hỗ trợ copy và xuất PDF chuẩn.
2. **Lớp Hiểu (3D Model Layer):** Chứa các mô hình hình học, luồng vật chất hoặc cấu trúc không gian giúp giải thích bản chất vấn đề. Mỗi trang hoặc nhóm trang nên dùng hình tượng gắn trực tiếp với nội dung thay vì đặt các khối hình học xoay tròn vô nghĩa.
3. **Lớp Không khí (Ambient Layer):** Ánh sáng môi trường, đổ bóng mềm và chuyển động nền tốc độ thấp. Phải có độ tương phản thấp để không tranh chấp thị giác với Lớp Đọc, và phải dừng ngay khi người dùng bật chế độ Pause.

## 3. Quy tắc Typography và Khoảng cách

- **Tiêu đề hành động (Declarative Headlines):** Viết tiêu đề mang thông điệp trọn vẹn, súc tích.
- **Chống dòng mồ côi (Orphan Words):** Kết hợp `text-wrap: pretty` (hoặc `balance` cho tiêu đề), căn chỉnh độ rộng cột hợp lý và dùng `white-space: nowrap` cho các cụm số liệu đi kèm đơn vị (ví dụ: `120 triệu VND`, `09:00 - 11:00`, `16,8 ms`) để không bị rớt chữ đơn lẻ xuống dòng cuối.
- **Khoảng thoáng an toàn:** Đảm bảo khoảng cách tối thiểu giữa cột văn bản và khung cảnh 3D (thường từ `48px - 64px` trên khung chuẩn `1600x900`) và tách biệt rõ vùng nội dung chính với thanh trạng thái/footer ở đáy trang.
- **Duyệt trên trang mẫu:** Luôn dựng và chụp kiểm tra các trạng thái có nội dung dài nhất trên 3 trang đại diện trước khi triển khai hàng loạt.
