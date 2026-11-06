# Kiểm tra quyền phân phối package

Kiểm tra ngày 07/11/2026 (Asia/Saigon) tại hai nguồn local: `/workspace/ai-native-skills/<name>` và `/home/box/agent-data/workflows/<name>`.
Đã rà soát danh mục file và tìm LICENSE, COPYING, NOTICE, copyright, redistribution, permission, bản quyền trong nội dung.

| Package | Kết quả trong bản cung cấp | Xử lý |
|---|---|---|
| ai-work-method | Không thấy license/grant phân phối | Cài local; không commit payload |
| vibecode-kit | Không thấy license/grant phân phối | Cài local; không commit payload |
| refinery | Không thấy license/grant phân phối | Cài local; không commit payload |
| sot-kernel-in-a-box | Không thấy license/grant phân phối | Cài local; không commit payload |
| html3d-slides | Không thấy license/grant cho package; cấu hình phông nhắc OFL | Cài local; không suy license phông thành license package |
| unslop | Không thấy license/grant; nội dung ghi nguồn cảm hứng pstack | Cài local; giữ attribution gốc |
| unslop-vi | Không thấy license/grant; nội dung ghi nguồn cảm hứng pstack | Cài local; giữ attribution gốc |

Không thấy lệnh cấm không đồng nghĩa được phép phân phối. Đây là kết quả kiểm tra bản local, không phải kết luận pháp lý hay xác nhận quyền tác giả. Muốn đưa payload lên repo công khai cần xác minh quyền và kèm license/attribution phù hợp trước.

Mentor, adapter runtime và docs mới có thể commit cùng repo; manifest chỉ giữ tên, mô tả ngắn và trạng thái quyền, không chứa bản nguồn đầy đủ. Source hash inventory và zip đầy đủ cũng để local-only.
