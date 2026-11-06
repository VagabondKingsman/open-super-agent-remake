# Bốn bài mẫu phối hợp

Các yêu cầu và dữ liệu dưới đây là bài tập giả lập, không phải kết quả dự án đã chạy.

## 1. Sửa nhãn lịch còn tiếng Trung trong OSA

Yêu cầu: "Lịch mới vẫn có nhãn tiếng Trung, kiểm tra và sửa, giữ i18n VI".

Skill Flow: ai-work-method -> vibecode-kit -> unslop-vi.

TIP: REQ-1 xác định nơi tạo nhãn, REQ-2 sửa VI/EN không phá history. AC-1 lịch mới lấy đúng locale; AC-2 test lịch/quay lại locale pass; AC-3 build/frontend pass; AC-4 lịch sử cũ không bị sửa.

Contractor SCAN luồng lưu chat và locales; Builder viết fix tối thiểu và regression cho VI/EN; Verify đọc output thật, test fallback, restart và smoke. Không gọi LLM trả phí hay gửi channel chỉ để test nhãn. Docs VI qua unslop-vi. Handoff gồm patch, test log, SHA local và phần history không đổi. Push/merge chỉ khi được giao quyền tương ứng.

Không có Docker: đánh dấu Computer NOT_CHECKED/docker_missing, không chấm lỗi i18n là FAIL vì Docker.

## 2. So sánh nhà cung cấp rồi tạo slide HTML

Yêu cầu: "So sánh 5 nhà cung cấp theo giá/độ phủ, chốt kho số liệu rồi làm slide web".

Skill Flow: ai-work-method -> refinery -> owner duyệt -> sot-kernel-in-a-box -> html3d-slides -> unslop-vi.

AC-1 mỗi ô có snapshot/evidence_span/origin_id; AC-2 giá khác nhau theo ngày giữ disputed và phạm vi; AC-3 owner duyệt lựa chọn trước khi vào source_canonical; AC-4 SOT check/bites/gate pass; AC-5 slide có provenance, keyboard và fallback.

refinery trả registry cùng claims/snapshots và log bites. Nếu thiếu giá thì honest-null, không lấy 0. Owner duyệt record nào thì adapter đưa record đó vào SOT, giữ claim chưa đủ bằng chứng ở trạng thái claim. Sau gate, slide lấy đúng registry/digest, không sửa giá bằng tay. html3d-slides dựng 3 trang đại diện trước khi nhân rộng; measure-ui kiểm UI. unslop-vi sửa lời dẫn, không xóa nhãn disputed.

Không được phép bỏ qua owner vì muốn làm slide nhanh. Chưa duyệt thì bàn giao bảng nháp, phần dựng từ SOT là deferred.

## 3. Audit số doanh thu nội bộ và dựng dashboard

Yêu cầu: "Hai CSV lệch tổng doanh thu; tìm nguyên nhân, lập kho chuẩn rồi dựng dashboard".

Skill Flow: ai-work-method -> sot-kernel-in-a-box -> vibecode-kit -> unslop-vi.

Không dùng refinery thay cho owner của file nội bộ. AC-1 chỉ rõ owner và phiên bản từng CSV; AC-2 lệch số vào flagged, chưa chốt thì verified_value=null; AC-3 đủ 6 bite tests; AC-4 dashboard dùng registry đúng digest, test empty/flagged state.

Contractor xác định mẫu số, kỳ báo cáo và quy tắc nghiệp vụ từ owner. Builder viết adapter theo TIP; SOT gate là điều kiện mở TIP dashboard. Verify kiểm fingerprint khi file nguồn đổi và chặn export bằng token cũ. Docs giải thích phần chưa chốt thay vì hiển thị 0 như số thật.

## 4. Brief tiếng Việt thành bài blog tiếng Anh

Yêu cầu: "Viết bài tiếng Anh từ brief về homestay này, kèm SEO và tóm tắt tiếng Việt".

Nếu brief đủ dữ kiện, chỉ dùng unslop; thêm unslop-vi cho bản tóm tắt nếu cần. Không gọi cả bộ hoặc lập SOT cho một bài viết đơn giản.

AC-1 giữ tên, giá, tiện ích và hạn chế đúng brief; AC-2 không bịa review/giải thưởng; AC-3 có SEO pack và bản tóm tắt VI giữ cùng ý. Chạy scan_en rồi đọc ngữ cảnh; scan không thay người biên tập. Nếu người dùng yêu cầu nghiên cứu thị trường có số liệu, mới nối ai-work-method -> refinery -> unslop.

Đầu ra là bản thảo trong chat hoặc file local, không tự đăng blog.
