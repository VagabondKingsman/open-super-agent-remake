# Hướng dẫn phối hợp chuỗi Skill (Multi-Skill Flows)

Tài liệu này quy định giao thức chuyển giao dữ liệu và đầu ra giữa các skill trong bộ công cụ khi xử lý nhiệm vụ phức tạp.

## Nguyên tắc nối chuỗi

1. **Không trộn lẫn mức độ tin cậy:** Dữ liệu từ nguồn ngoài qua `refinery` (`sourced` hoặc `corroborated`) không tự động trở thành sự thật nội bộ (`verified_primary`) trong `sot-kernel-in-a-box`. Muốn đưa vào SOT phải có bước duyệt của chủ việc và ghi nhận nguồn gốc qua adapter.
2. **Dữ liệu đi trước, trình bày đi sau:** Khi làm ứng dụng (`vibecode-kit`) hoặc bài trình chiếu (`html3d-slides`) có chứa số liệu thực tế, ưu tiên chuẩn hóa dữ liệu qua `refinery` hoặc `sot-kernel-in-a-box` trước, sau đó mới nối vào giao diện.
3. **Giữ nguyên trạng thái thiếu và mâu thuẫn:** Giao diện phần mềm hoặc slide trình chiếu phải hiển thị trung thực các trường `disputed` hoặc `honest-null`, không tự làm đẹp số liệu ở tầng hiển thị.

## Các luồng phối hợp chuẩn

### Luồng A: Nghiên cứu nguồn ngoài -> Kho sự thật nội bộ (`refinery` -> `sot-kernel-in-a-box`)
1. Dùng `refinery` khởi tạo domain (`new_domain.py`), lưu bản chụp vào `snapshots/` và trích xuất `claims.jsonl`.
2. Chạy `refinery.py` và `bites.py` để lọc lỗi cấu trúc, phát hiện mâu thuẫn (`disputed`) và gom nguồn trùng gốc (`origin_id`).
3. Trình bày các mục `disputed` và `sourced` cho chủ việc duyệt (có thể dùng `review.py` để quản lý hàng đợi duyệt).
4. Những fact đã được chủ việc xác nhận được xuất sang thư mục `source_canonical/` của dự án SOT, chạy adapter + `hygiene.py` + `sot_check.py` + `sot_publish.py gate` để tạo bản xuất có kiểm định.

### Luồng B: Kho dữ liệu chuẩn -> Bài trình chiếu HTML 3D (`sot-kernel-in-a-box` / `refinery` -> `html3d-slides`)
1. Lấy dữ liệu đã qua kiểm định từ `registry/` của SOT hoặc output của `refinery`.
2. Dùng `ai-work-method` chốt brief trình chiếu (mục tiêu, đối tượng, số trang) theo `assets/brief.template.json` của `html3d-slides`.
3. Ánh xạ từng fact/claim thành vật mang nội dung (bảng, mô hình 3D, trạng thái so sánh) trong file dữ liệu trung tâm của slide; giữ nguyên nhãn cho các giá trị giả lập hoặc chưa xác minh.
4. Dựng runtime + 3D, kiểm tra bằng `scripts/measure-ui.js` và đóng gói.

### Luồng C: Kho dữ liệu chuẩn -> Phát triển ứng dụng (`sot-kernel-in-a-box` / `refinery` -> `vibecode-kit`)
1. Xác định schema dữ liệu từ `sot-kernel-in-a-box` hoặc `refinery` làm hợp đồng dữ liệu đầu vào (Data Contract).
2. Kích hoạt `vibecode-kit`: chạy SCAN codebase -> RRI làm rõ nghiệp vụ -> lập BLUEPRINT & chia TIPs.
3. Builder triển khai code theo TIP, đảm bảo UI/API xử lý đầy đủ cả 4 trạng thái dữ liệu (`verified/corroborated`, `claim/sourced`, `disputed/flagged`, `null`).
4. Chạy VERIFY đối chiếu REQ-ID, AC và sức khỏe kỹ thuật trước khi bàn giao.

## Cơ chế Đệ quy Tự tối ưu xuyên suốt các Skill (Cross-Skill Retro Rubric Loop)

Khi thực thi bất kỳ luồng đơn lẻ hay đa skill nào ở trên, mỗi bước kiểm định đều áp dụng chung nguyên lý **Retro Rubric (Thử nghiệm → Chấm điểm → Trích xuất quy tắc `RETRO-ID` → Nạp ngược → Tái thực thi)**:

| Skill đang chạy | Công cụ bắt lỗi / Chấm điểm | Cách đệ quy rút kinh nghiệm khi trượt cổng |
|---|---|---|
| `refinery` | `refinery.py` + `bites.py` | Phát hiện lỗi `SPAN_NOT_FOUND` hoặc trùng nguồn `origin_id` -> Ghi nhận quy tắc trích xuất cho domain hiện tại -> Chuẩn hóa lại `claims.json` và chạy lại tới khi `0 gate bites` |
| `sot-kernel-in-a-box` | `sot_check.py` + `sot_bites.py` | Phát hiện vi phạm A3 Guard (phơi `value` của fact chưa xác minh) hoặc lệch vân tay -> Chạy `hygiene.py fill/split` và cập nhật adapter -> Kiểm tra lại tới khi `6/6 răng cắn PASS` |
| `vibecode-kit` | `scripts/retro_rubric.py` + bộ test dự án | Chấm 5 chiều `R1..R5`; nếu `< 9/10` hoặc có chiều `0 điểm` -> Chạy `retro_rubric.py learn` đúc kết `RETRO-ID` + thêm test chặn hồi quy -> Truyền `RETRO-ID` sang các TIP kế tiếp (tối đa 3 vòng/TIP) |
| `html3d-slides` | `scripts/measure-ui.js` + Visual Critique | Đo tự động dòng mồ côi (`orphanLastLines`), khoảng cách cột/footer và mật độ Retina -> Nếu phát hiện lỗi bố cục trên trang mẫu, cập nhật quy tắc CSS/layout chung trước khi nhân rộng ra toàn bộ các trang còn lại |
