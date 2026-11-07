---
name: html3d-slides
description: >-
  Thiết kế, dựng mới hoặc nâng cấp bộ slide trình chiếu HTML tương tác có đồ họa 3D (Three.js/WebGL/WebGPU): brief, storyboard, kiến trúc 3 lớp DOM + 3D + Ambient chung một state, điều khiển nhịp theo người nói, đo kiểm UI bằng measure-ui.js, QA và đóng gói HTML chạy độc lập. Dùng khi người dùng muốn slide web, bài thuyết trình HTML, deck tương tác, presentation có 3D/animation, keynote trình chiếu trên trình duyệt hoặc nâng cấp slide HTML sẵn có. Nếu người dùng cần file PowerPoint (.pptx) thì dùng pptx thay vì skill này. Thuộc bộ AI Native: khi slide chứa số liệu cần kiểm chứng, đọc thêm ai-work-method.
---

# Slide HTML 3D · Phương pháp dựng bài trình chiếu tương tác

Tạo trải nghiệm trình chiếu trên trình duyệt giúp người xem đọc rõ nội dung, hiểu cấu trúc qua mô hình 3D và tương tác trực tiếp trên dữ liệu thật.

## 1. Xác định phạm vi và Brief đầu vào

Trước khi viết code hoặc sửa bộ slide hiện có, xác định rõ yêu cầu qua [assets/brief.template.json](assets/brief.template.json):
- **Người xem & Mục tiêu:** Đối tượng nghe là ai, họ cần nắm được thông điệp hay quyết định gì sau buổi trình chiếu.
- **Cấu trúc & Nguồn dữ liệu:** Số lượng trang, thời lượng, nguồn số liệu (kết nối với `sot-kernel-in-a-box` hoặc `refinery` nếu có dữ liệu cần truy nguyên).
- **Phong cách & Thiết bị:** Tông màu, cặp phông chữ, cách điều khiển (bấm phím thủ công từng bước), thiết bị chiếu (màn hình Retina, máy chiếu hội trường, offline viewer).

Tham khảo thông số khởi điểm trung lập tại [assets/default-profile.json](assets/default-profile.json) và tùy biến theo chủ đề thực tế, tuyệt đối không áp cứng một bảng màu hay số trang cố định cho mọi đề tài.

## 2. Quy trình thực hiện 6 bước

1. **Chốt thông điệp và vật mang nội dung (Artifact):** Mỗi trang truyền tải một thông điệp rõ ràng gắn với một vật mang nội dung cụ thể (bảng đối chiếu, sơ đồ luồng, mô hình 3D, bộ lọc tương tác). Phân biệt rõ số liệu thật và ví dụ giả lập. Đọc [references/workflow-and-design.md](references/workflow-and-design.md).
2. **Dựng Storyboard:** Lập bảng gồm `id | mục đích | thông điệp | artifact | layout | scene 3D | thao tác (action) | các trạng thái (states) | lời dẫn`. Tránh lặp lại cùng một khối 3D trang trí vô nghĩa cho mọi trang.
3. **Thử nghiệm trên 3 trang đại diện:** Chọn 1 trang bìa/mở đầu, 1 trang nhiều dữ liệu và 1 trang có tương tác phức tạp để chốt bố cục, ánh sáng và độ nét ở mọi trạng thái trước khi nhân rộng toàn bộ deck.
4. **Xây dựng kiến trúc 3 lớp & Đồng bộ State:**
   - **Lớp Đọc (DOM):** Giữ tiêu đề, nội dung chính, bảng biểu, nút bấm và mã QR trên lớp HTML/CSS để sắc nét tuyệt đối, dễ truy cập bàn phím và in ấn.
   - **Lớp Hiểu (3D Canvas):** Đặt mô hình 3D minh họa cấu trúc/quan hệ trong vùng `scene-window`.
   - **Lớp Không khí (Ambient):** Ánh sáng nền, lưới phối cảnh nhẹ, không gây nhiễu vùng đọc chữ.
   - Cả DOM và tương tác 3D (Raycaster) đều gọi chung hàm `action(name, value)` và đọc từ một `state` duy nhất. Đọc [references/engineering.md](references/engineering.md).
5. **Render và Đo kiểm giao diện:** Kiểm tra trạng thái đầu, giữa, cuối và các trạng thái rỗng/lỗi của từng trang. Chèn [scripts/measure-ui.js](scripts/measure-ui.js) để đo tự động dòng mồ côi (orphan words), khoảng cách cột, khoảng cách footer và mật độ điểm ảnh canvas (`widthDensityRatio`).
6. **Kiểm định QA và Đóng gói:** Áp dụng danh sách kiểm tra tại [references/qa-and-release.md](references/qa-and-release.md). Đảm bảo chế độ tạm dừng (Pause), điều hướng bàn phím, ảnh tĩnh dự phòng (fallback khi thiếu GPU) và xuất gói HTML/PDF hoàn chỉnh.

## 3. Các nguyên tắc bắt buộc khi trình chiếu thủ công

- **Người nói làm chủ nhịp độ:** Chỉ thao tác của người trình bày (bấm phím/click) mới chuyển bước nội dung hoặc mở kết luận. Biến thời gian (`time`) chỉ dùng cho chuyển động vào cảnh (entrance) hoặc dao động nền (ambient loop), không tự động lật trang hay đổi dữ liệu theo bộ đếm giờ.
- **Khả năng truy cập & Bàn phím:** Mọi điểm tương tác trên mô hình 3D phải có nút bấm DOM tương đương để điều khiển được bằng phím `Tab`, `Space`/`Enter` và phím mũi tên chuyển trang.
- **Bảo toàn độ sắc nét:** Chữ chính và mã QR luôn nằm ngoài canvas 3D và không chịu hiệu ứng hậu kỳ (bloom/blur). Khi vẽ nhãn ngắn lên texture 3D, phải nạp xong phông chữ (`document.fonts.load`) trước khi gọi `fillText` và giữ đúng tỷ lệ khung hình.
- **Quản lý tài nguyên:** Chỉ chạy một vòng lặp render (RAF) cho cảnh đang hiển thị; dừng toàn bộ RAF và animation CSS khi bấm Pause (`P`), khi ẩn tab hoặc khi bật `prefers-reduced-motion`.

## Runtime (Claude.ai / Cowork)

- `SKILL_DIR` = thư mục chứa file `SKILL.md` này (lấy từ `location` trong `available_skills`, ví dụ `/mnt/skills/user/html3d-slides` hoặc `/mnt/skills/plugins/html3d-slides` tùy cách cài). Thư mục này chỉ-đọc: tạo và ghi dữ liệu dự án trong thư mục làm việc ghi được, không ghi vào `SKILL_DIR`.
- Cần `pyyaml` cho script Python (`pip install pyyaml --break-system-packages` nếu thiếu).
- Việc nhiều bước hoặc nối với skill khác trong bộ AI Native: đọc `SKILL.md` của `ai-work-method` để lấy bảng định tuyến và mẫu TIP/báo cáo.
