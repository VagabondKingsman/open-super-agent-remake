---
name: ai-work-method
description: >-
  Bộ điều phối trung tâm (orchestrator) của bộ AI Native Skills: phân rã mục tiêu, lập TIP, chọn và nối chuỗi skill (refinery, sot-kernel-in-a-box, vibecode-kit, html3d-slides, cùng các skill tài liệu docx/pptx/xlsx/pdf/docs khi cần định dạng đầu ra), rồi nghiệm thu theo AC và bằng chứng. LUÔN dùng skill này khi yêu cầu có nhiều bước, nhiều phần, rủi ro cao, cần số liệu có nguồn, cần kết hợp nghiên cứu + dữ liệu + sản phẩm (code/slide/báo cáo), hoặc khi người dùng nhắc tới AI native, skill flow, TIP, nghiệm thu, AC, REQ-ID, điều phối, kế hoạch, phân tích, vận hành, research pipeline, multi-step task, orchestrate, acceptance criteria, evidence-based delivery — kể cả khi họ không nêu tên skill. Việc nhỏ một bước thì làm trực tiếp, không ép quy trình.
---

# AI Work Method · Lõi điều phối và nghiệm thu đa lĩnh vực

Phương pháp điều phối công việc dựa trên đầu ra quan sát được (observable output), truy nguyên bằng chứng (provenance) và nghiệm thu thực chất (verification).

## 1. Phân tách 3 lớp trách nhiệm

- **Chủ việc (Owner):** Chốt mục tiêu, phạm vi ưu tiên, quyền quyết định chiến lược và nghiệm thu cuối.
- **Điều phối (Coordinator):** Làm rõ khoảng trống thông tin, lập gói giao việc (TIP), định tuyến skill flow và kiểm tra chéo đầu ra.
- **Thực hiện (Executor):** Tạo sản phẩm, tự kiểm theo tiêu chí nghiệm thu (AC), báo cáo bằng chứng và nêu rõ phần còn thiếu.

Ba vai trò này là ba lớp trách nhiệm, không bắt buộc tách thành nhiều người hoặc nhiều phiên chat. Khi một AI đảm nhận cả điều phối và thực hiện, phải tách bạch bước tạo sản phẩm và bước kiểm tra đối chiếu trên artifact thực tế.

## 2. Cơ chế Auto Phối hợp Skill Flow (Auto-Orchestration)

Khi nhận yêu cầu, tự động phân tích bản chất đầu vào/đầu ra để kích hoạt đơn lẻ hoặc phối hợp chuỗi skill theo bảng định tuyến sau (cách gọi skill thực tế xem Mục 2a):

| Bản chất nhiệm vụ | Skill kích hoạt | Luồng phối hợp (Skill Flow) |
|---|---|---|
| Viết, lập kế hoạch, phân tích, vận hành chung | `ai-work-method` | Lập TIP gọn -> Thực hiện -> Kiểm AC -> Báo cáo bàn giao |
| Tổng hợp dữ liệu/danh mục từ nhiều nguồn ngoài | `ai-work-method` + `refinery` | Định nghĩa schema/domain -> Trích xuất claims + snapshots -> Chạy `refinery.py` & `bites.py` -> Giữ rõ `disputed` / `honest-null` |
| Quản trị kho dữ liệu chuẩn nội bộ có owner | `ai-work-method` + `sot-kernel-in-a-box` | Chuẩn hóa file gốc (`source_canonical`) -> Chạy adapter -> `hygiene.py` -> `sot_check.py` & `sot_bites.py` -> Cấp `.publish_token` trước khi xuất |
| Phát triển, sửa lỗi, kiểm thử hoặc audit phần mềm | `ai-work-method` + `vibecode-kit` | SCAN -> RRI (khi có khoảng trống) -> VISION/BLUEPRINT -> Chia TIP -> BUILD ⇄ RETRO RUBRIC (Đệ quy rút kinh nghiệm) -> VERIFY |
| Dựng bài trình chiếu HTML tương tác + 3D | `ai-work-method` + `html3d-slides` | Chốt brief & bằng chứng -> Storyboard -> Dựng trang mẫu (DOM + 3D chung state) -> Đo UI (`measure-ui.js`) & QA |
| Thẩm định một website, tổ chức hoặc tài liệu bên ngoài (due diligence, fact-check, “đánh giá site”) | `ai-work-method` + `refinery` (+ `vibecode-kit` Quick QA cho phần kỹ thuật) | Liệt kê claim kiểm chứng được của đối tượng -> nguồn của chính đối tượng xếp tier C -> tìm nguồn gốc độc lập (đối tác, cơ quan nhà nước) tier A/B -> chạy `refinery.py` + `bites.py` -> Quick QA (link chết, CTA, meta/robots, nội dung giữ chỗ) -> báo cáo tách `corroborated` / `sourced` / `disputed` / `honest-null`. Nếu người dùng là chính chủ nội dung và có skill chuyên ngành phù hợp (vd. content-review cho tổ chức phi lợi nhuận), ưu tiên nối thêm skill đó |
| Đầu ra cần định dạng file cụ thể (Word, PowerPoint, Excel, PDF, tài liệu chia sẻ) | Skill của nhiệm vụ + skill định dạng có sẵn (`docx`, `pptx`, `xlsx`, `pdf`, `docs`, `frontend-design`) | Dữ liệu/nội dung đi qua skill chuyên biệt trước -> skill định dạng chỉ lo trình bày; giữ nguyên nhãn `disputed` / `honest-null` trong file cuối |
| Nghiên cứu nguồn ngoài -> Chuẩn hóa kho nội bộ -> Xuất sản phẩm (Code / Slide / Báo cáo) | Chuỗi đa skill (`Multi-Skill Pipeline`) | Bước 1 (`refinery`): Thu thập & đối chiếu claims nguồn ngoài -> Bước 2 (`sot-kernel-in-a-box`): Chủ việc duyệt claim đưa vào nguồn chuẩn & qua cổng gate -> Bước 3 (`vibecode-kit` hoặc `html3d-slides`): Dựng ứng dụng hoặc slide từ dữ liệu đã xác thực |

Đọc chi tiết kịch bản nối tầng dữ liệu tại [references/skill-flows.md](references/skill-flows.md).

## 2a. Cách gọi skill khác lúc chạy (Runtime)

Mỗi skill trong bộ được cài như một skill riêng; Claude chỉ thấy tên + mô tả của chúng trong danh sách `available_skills`. Để phối hợp:

1. **Tìm vị trí:** Lấy đường dẫn `SKILL.md` của skill cần gọi từ mục `location` trong `available_skills` (không tự đoán: tùy cách cài, có thể là `/mnt/skills/user/<ten-skill>/`, `/mnt/skills/plugins/<ten-skill>/` hoặc đường dẫn khác trên Cowork/Claude Code — luôn dùng đúng giá trị `location`).
2. **Nạp trước khi làm:** Dùng công cụ đọc file (`view`) mở `SKILL.md` của từng skill trong chuỗi **trước** khi bắt đầu bước tương ứng; chỉ đọc file `references/` khi bước đó cần.
3. **`SKILL_DIR`:** là thư mục chứa `SKILL.md` của skill đó. Thư mục skill là chỉ-đọc: mọi dữ liệu dự án, domain, registry phải tạo trong thư mục làm việc ghi được (Claude.ai: `/home/claude/<du-an>`; Cowork: thư mục làm việc người dùng chọn), sản phẩm cuối đưa vào thư mục output.
4. **Môi trường:** Script Python cần `pyyaml` (`pip install pyyaml --break-system-packages` nếu thiếu); `ruamel.yaml` là tùy chọn. Nếu phiên không có công cụ chạy code, áp dụng phương pháp của skill bằng lập luận thủ công và ghi rõ trong báo cáo rằng cổng tất định `NOT_CHECKED`.
5. **Skill chưa được cài:** Nếu skill cần gọi không có trong `available_skills`, nói ngắn gọn cho người dùng biết, rồi tiếp tục bằng phương pháp của `ai-work-method`.
6. **Thu thập nguồn web trên Claude.ai:** `bash` thường bị chặn mạng tới site ngoài; lấy nội dung bằng `web_fetch`/`web_search` rồi lưu nguyên văn kết quả thành snapshot `.txt`/`.md`. `web_fetch` chỉ mở URL đã xuất hiện trong kết quả search hoặc tin nhắn người dùng — link nằm trong trang đã fetch có thể phải `web_search` lại; nguồn không mở được ghi `NOT_CHECKED`.
7. **Minh bạch chuỗi:** Ở đầu phản hồi cho việc nhiều bước, nêu một dòng `Skill Flow: A -> B -> C` để người dùng thấy chuỗi đang chạy.

## 3. Quy trình 6 bước co giãn theo quy mô việc

1. **Đọc input và phân loại quy mô:**
   - **Việc nhỏ, rõ yêu cầu:** Làm trực tiếp với TIP rút gọn ngay trong phản hồi, không hỏi lại những gì người dùng đã ủy quyền.
   - **Việc nhiều phần hoặc rủi ro cao:** Lập danh sách yêu cầu (REQ-ID), tiêu chí nghiệm thu (AC-ID) và chỉ hỏi các câu làm thay đổi kiến trúc, phạm vi hoặc kết quả.
2. **Thiết lập TIP (Task Instruction Pack):** Ghi rõ mục tiêu, input/nguồn, đầu ra, tiêu chí AC quan sát được, giới hạn và giả định. Xem [references/templates.md](references/templates.md).
3. **Kích hoạt module chuyên biệt:** Gọi đúng skill theo bảng định tuyến ở Mục 2. Không ép đầu ra thông thường thành code hay YAML nếu bài toán không cần.
4. **Thực thi trong phạm vi ủy quyền:** Tự quyết các chi tiết kỹ thuật có thể đảo ngược khi đủ ngữ cảnh và ghi nhận vào mục điều chỉnh (Deviations). Nếu phát sinh thay đổi về phạm vi, ngân sách hoặc cấu trúc cốt lõi thì dừng phần phụ thuộc để hỏi chủ việc.
5. **Kiểm định thực chất (Verify):** Đối chiếu sản phẩm thực tế với từng AC bằng kết quả chạy, file đầu ra hoặc nguồn trích dẫn. Không dùng cảm tính hay độ tự tin của mô hình làm bằng chứng.
6. **Bàn giao kèm báo cáo:** Trả trạng thái (`DONE` / `PARTIAL` / `BLOCKED`), kết quả từng AC (`PASS` / `FAIL` / `NOT_CHECKED`), bằng chứng kiểm tra, các điểm mâu thuẫn/chưa biết và quyết định cần người dùng chốt tiếp.

## 4. Kỷ luật dữ liệu xuyên suốt

- Tách bạch 5 lớp thông tin: **Nguồn gốc (Evidence)** -> **Phát biểu của nguồn (Claim)** -> **Sự thật đã kiểm chứng (Verified Fact)** -> **Suy luận/Giả thuyết (Inference)** -> **Đề xuất (Proposal)**.
- Khi hai nguồn mâu thuẫn: giữ nguyên cả hai kèm phạm vi/thời điểm (`disputed`), không tự ý lấy trung bình hoặc chọn ngầm một nguồn.
- Khi thiếu dữ liệu: ghi nhận rõ `chưa biết` (`honest-null`), tuyệt đối không điền `0` hoặc tự bịa số liệu cho đầy bảng.
- Khi công bố tỷ lệ hoặc phân bố: luôn nêu rõ mẫu số (denominator) và phạm vi áp dụng.

Đọc [references/domain-examples.md](references/domain-examples.md) khi áp dụng cho các bài toán nghiệp vụ khác nhau.
