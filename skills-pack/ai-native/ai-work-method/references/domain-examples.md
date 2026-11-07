# Ví dụ áp dụng đa lĩnh vực

Các tình huống minh họa cách áp dụng `ai-work-method` và phối hợp module mà không biến mọi bài toán thành tác vụ lập trình.

| Lĩnh vực | Đầu ra | Input | Tiêu chí nghiệm thu (AC) | Bằng chứng kiểm tra | Skill Flow |
|---|---|---|---|---|---|
| Nội dung & Truyền thông | Bài phân tích hoặc tài liệu giới thiệu 600-800 từ | Brief mục tiêu, tệp độc giả, bảng số liệu | Đúng thông điệp & CTA; 100% con số khớp nguồn; đúng độ dài | Đếm từ, đối chiếu từng số liệu với nguồn gốc | `ai-work-method` |
| Nhân sự & Đào tạo | Kế hoạch onboarding 2 tuần | Mô tả vai trò, khung lịch, danh sách mentor | Mỗi buổi có đầu ra & người phụ trách; không trùng lịch; có bài đánh giá | Bảng kiểm tra xung đột lịch, ánh xạ mục tiêu -> bài tập | `ai-work-method` |
| Mua sắm & Vận hành | Bảng đối chiếu báo giá nhà cung cấp | Các báo giá, điều kiện giao hàng, kỳ hiệu lực | Cùng đơn vị quy đổi; mục chưa có báo giá ghi rõ "chưa rõ"; không gán 0 cho phí ẩn | Bảng đối chiếu từng dòng với file báo giá gốc | `ai-work-method` (+ `sot-kernel-in-a-box` nếu lưu trữ lâu dài) |
| Nghiên cứu thị trường | Bộ danh mục đối thủ / sản phẩm từ nguồn công khai | Các trang web, báo cáo công bố, tài liệu thu thập | Mỗi thông số gắn snapshot & đoạn trích verbatim; nguồn lệch nhau gắn `disputed` | Chạy `refinery.py` và `bites.py` PASS, kiểm tra ngữ cảnh trích dẫn | `ai-work-method` + `refinery` |
| Kỹ thuật phần mềm | Tính năng mới hoặc bản vá lỗi có kiểm thử | Codebase hiện tại, mô tả yêu cầu hoặc log lỗi | Toàn bộ AC đạt; build/lint/test xanh; không phát sinh regression | Diff code, kết quả chạy test thực tế, Verify Report | `ai-work-method` + `vibecode-kit` |
| Thuyết trình tương tác | Bộ slide HTML 3D trình chiếu trực tiếp | Nội dung chuyên môn, số liệu đã kiểm, yêu cầu thiết kế | Chữ tách khỏi hiệu ứng 3D, điều khiển từng bước theo người nói, không lỗi dòng mồ côi | Render kiểm tra các trạng thái, chạy `measure-ui.js` | `ai-work-method` + `html3d-slides` |
