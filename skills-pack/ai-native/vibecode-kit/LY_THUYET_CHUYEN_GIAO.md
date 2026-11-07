# Vibecode Kit · Nguyên lý điều phối phát triển phần mềm

## 1. Giải quyết 3 điểm nghẽn khi lập trình cùng AI

1. **Yêu cầu mơ hồ dẫn đến xây sai sản phẩm:** Khắc phục bằng bước `SCAN` kết hợp phỏng vấn ngược `RRI` ưu tiên theo rủi ro trước khi viết code.
2. **Kiểm soát vụn vặt từng dòng lệnh làm giảm hiệu quả:** Khắc phục bằng việc định nghĩa rõ đầu ra và tiêu chí nghiệm thu trong `TIP`, để Builder chủ động chọn cách cài đặt tối ưu trong phạm vi cho phép.
3. **Tin vào báo cáo hoàn thành mà không kiểm tra thực tế:** Khắc phục bằng bước `VERIFY` bắt buộc đối chiếu tỷ lệ bao phủ `REQ-ID`, chạy kiểm thử thực tế từng kịch bản và kiểm tra sức khỏe kỹ thuật (build/type/lint/test).

## 2. Sàn kiểm toán tối thiểu (Audit Trail Floor)

Dù nhiệm vụ nhỏ đến đâu, luôn duy trì tối thiểu 2 dấu vết: **Gói giao việc (TIP)** và **Báo cáo hoàn thành (Completion/Verify Report)**. Mọi quyết định điều chỉnh so với thiết kế ban đầu đều được ghi nhận rõ trong mục `DEVIATIONS` hoặc `DECISIONS LOG`.
