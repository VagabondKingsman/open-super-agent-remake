---
name: vibecode-kit
description: >-
  Phương pháp phát triển phần mềm AI-First (Vibecode Kit): 3 vai trò Homeowner/Contractor/Builder, quy trình 8 bước tự co giãn (SCAN, RRI, VISION, BLUEPRINT, TASK GRAPH, BUILD, VERIFY, REFINE), TIP có AC, vòng đệ quy Retro Rubric R1-R5 với retro_rubric.py, cùng giao thức Debug 9 bước, QA 3 tầng và X-Ray. Dùng cho mọi việc code: xây app/web/tool/script mới, thêm tính năng, sửa bug, debug sâu, refactor, viết test, QA, review hoặc audit/bàn giao codebase, kể cả khi người dùng chỉ nói 'làm app', 'viết code', 'fix lỗi', 'build feature'. Thuộc bộ AI Native: khi app dùng số liệu cần kiểm chứng hoặc việc nhiều giai đoạn, đọc thêm ai-work-method.
---

# Vibecode Kit · Phương pháp phát triển phần mềm AI-First

## 1. Triết lý cốt lõi

```text
Chủ thầu làm rõ điều chưa biết, giao việc chuẩn (TIP), kiểm tra bằng chứng thực tế.
Thợ thi công đúng phạm vi, tự kiểm thử, tự đệ quy tối ưu qua Retro Rubric và báo cáo minh bạch.
Con người ra quyết định chiến lược về mục tiêu, phạm vi và quyền phát hành.

Tin AI, kiểm định đầu ra (Verify output), đệ quy rút kinh nghiệm từ lỗi thực tế.
```

## 2. Ba vai trò và Chế độ vận hành linh hoạt

```text
                    CON NGƯỜI (Homeowner)
                    Mục tiêu · Ưu tiên · Phê duyệt
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       CHỦ THẦU                      THỢ
      (Contractor)                 (Builder)
     Thiết kế + Điều phối        Code + Test + Retro Loop
              ◄──── TIP / Report ────►
```

| Vai trò | Trách nhiệm chính | Ranh giới tin cậy (Trust Boundary) |
|---|---|---|
| **Con người (Homeowner)** | Đưa mục tiêu chiến lược, chốt scope/kiến trúc lớn, quyết định ship | Không cần đi vào chi tiết triển khai |
| **Chủ thầu (Contractor)** | Khảo sát, phỏng vấn ngược (RRI), thiết kế Blueprint, chia TIP, nghiệm thu (Verify & Retro Gate) | Không tự ý viết code khi chưa có TIP |
| **Thợ (Builder)** | Viết code theo TIP, chạy test + tự đệ quy qua Retro Rubric, nộp Completion Report | Không tự ý đổi kiến trúc/scope; thấy hướng tốt hơn thì ghi vào `SUGGESTIONS` |

**Chế độ thực thi (Single-Agent vs Multi-Agent):**
- **Khi người dùng làm việc trực tiếp với một AI duy nhất (Auto-Flow):** AI tự động đảm nhận tuần tự các pha trong cùng luồng: Pha 1 (*Contractor*) phân tích yêu cầu, lập TIP kèm Retro Guardrails -> Pha 2 (*Builder*) viết code, chạy test và tự đệ quy sửa lỗi qua **Retro Rubric Loop** -> Pha 3 (*Contractor Verify*) đối chiếu kết quả chạy với AC/Rubric và xuất báo cáo nghiệm thu.
- **Khi người dùng tách riêng phiên thiết kế và phiên code:** Xuất bản đầy đủ gói `TIP` và mẫu `Completion Report` kèm `Retro Rubric Log` để bàn giao giữa hai phiên.

## 3. Quy trình 8 bước tự co giãn kèm Vòng lặp Đệ quy Retro Rubric

```text
SCAN → RRI → VISION → BLUEPRINT → TASK GRAPH → BUILD ⇄ VERIFY & RETRO RUBRIC (Đệ quy tối ưu) → REFINE
```

- **Task nhỏ (sửa bug, thêm trường, 1 TIP):** Rút gọn thành `SCAN nhanh → TIP → BUILD ⇄ RETRO RUBRIC → VERIFY`. Không ép phỏng vấn dài dòng nhưng vẫn giữ định dạng TIP, chấm Retro Rubric và xuất Completion Report.
- **Task vừa (tính năng/module mới, 2–5 TIPs):** Chạy đủ 8 bước; mỗi TIP khi chạy qua vòng `BUILD ⇄ RETRO RUBRIC` sẽ tự động truyền các quy tắc chống lặp lỗi (`RETRO-ID`) sang các TIP kế tiếp.
- **Task lớn (ứng dụng mới, bản phát hành lớn, 5+ TIPs):** Chạy đủ 8 bước kèm kiểm thử QA đa tầng, rà soát bảo mật và duy trì sổ cái `RETRO RUBRIC LOG` xuyên suốt dự án.

### Chi tiết các bước

1. **SCAN:** Khảo sát cấu trúc thư mục, tech stack, các mẫu thiết kế sẵn có, khoảng trống và sức khỏe mã nguồn. Đọc [references/scan-report-format.md](references/scan-report-format.md).
2. **RRI (Reverse Requirements Interview):** Phỏng vấn ngược theo 5 góc nhìn (*End User, Business Analyst, QA/Tester, Developer, Operator*) bằng 3 chế độ câu hỏi (`CHALLENGE`, `GUIDED`, `EXPLORE`). Tự động trả lời những điều đã rõ từ bước SCAN; chỉ hỏi các khoảng trống làm thay đổi kết quả. Xem [references/rri-methodology.md](references/rri-methodology.md) và [references/rri-question-bank.md](references/rri-question-bank.md).
3. **VISION:** Đề xuất kiến trúc tổng thể, luồng người dùng, định hướng giao diện (nếu có UI) và tech stack. Xem [references/vision-guide.md](references/vision-guide.md).
4. **BLUEPRINT:** Bản thiết kế chi tiết gồm cấu trúc module/file, schema dữ liệu, ánh xạ `REQ-ID` và danh sách công việc dự kiến.
5. **TASK GRAPH:** Chia nhỏ Blueprint thành các gói giao việc `TIP` (Task Instruction Pack) có thứ tự phụ thuộc, tiêu chí nghiệm thu (`AC`) và danh sách `ACTIVE RETRO GUARDRAILS`. Xem [references/tip-and-report-formats.md](references/tip-and-report-formats.md).
6. **BUILD ⇄ RETRO RUBRIC LOOP (Thi công theo YAGNI Thực dụng & Đệ quy tối ưu):**
   - **Bộ lọc YAGNI Thực dụng trước khi viết code (áp dụng cho mọi File / Class / Hàm mới):**
     1. *Sự tồn tại (Existence):* Thành phần này phục vụ trực tiếp `AC` nào trong `TIP`? Nếu chỉ để "dự phòng tương lai" → **Bỏ, không viết.**
     2. *Tái sử dụng (Reuse):* Trong báo cáo `SCAN` (`REUSABLE_COMPONENTS`) hoặc thư viện chuẩn của dự án đã có sẵn hàm/component nào làm được việc này chưa? Nếu có → **Tái sử dụng, cấm viết lại.**
     3. *Độ phức tạp tối thiểu (Minimum Viable Complexity):* Nếu bắt buộc phải viết mới, chọn cách viết **đơn giản, tường minh, ít tầng trung gian nhất** mà vẫn đảm bảo đủ kiểm tra kiểu (`R2`) và xử lý tình huống biên (`R3`) — tuyệt đối không đánh đổi khả năng đọc/bắt lỗi để lấy code ngắn kiểu "code golf".
   - **Tự chấm và đệ quy qua Bảng Retro Rubric 5 chiều** (`R1: Spec Fidelity`, `R2: Runtime & Test`, `R3: Edge-Case Resilience`, `R4: Blast-Radius, Hygiene & YAGNI`, `R5: Anti-Repeat`):
   - Nếu bất kỳ tiêu chí nào bị `FAIL` (0 điểm) hoặc tổng `< 9/10`, AI **tự động đệ quy (tối đa 3 vòng)**:
     1. Chẩn đoán nguyên nhân gốc (Root Cause) khiến lần chạy thử bị trượt Rubric.
     2. Đúc kết thành quy tắc phòng ngừa `RETRO-[XX]` (*Triệu chứng → Nguyên nhân gốc → Quy tắc/Test chặn*).
     3. Bổ sung test chặn lỗi (Regression Bite) và nạp `RETRO-[XX]` vào ràng buộc của TIP hiện tại lẫn các TIP phía sau.
     4. Build và chạy test lại cho đến khi đạt chuẩn Rubric.
   - Có thể chạy công cụ tất định [scripts/retro_rubric.py](scripts/retro_rubric.py) (`init`, `evaluate`, `learn`, `verify-guardrails`, `report`) để khóa sổ cái đệ quy. Đọc chi tiết tại [references/retro-rubric-protocol.md](references/retro-rubric-protocol.md).
7. **VERIFY:** Kiểm tra độc lập trên sản phẩm thực tế. Một `VERIFY REPORT` hợp lệ bắt buộc có đủ 5 mục định lượng:
   ```text
   REQUIREMENT COVERAGE: số REQ đã hoàn thành / tổng số REQ (%)
   SCENARIO RESULTS:     kết quả PASS/FAIL từng AC + mức độ nghiêm trọng
   TECHNICAL HEALTH:     kết quả build / lỗi kiểu (type) / lint / số test pass
   RETRO RUBRIC SCORE:   điểm số R1..R5 (/10) + số vòng đệ quy + danh sách RETRO-ID đã khóa
   OVERALL STATUS:       READY | READY-với-deferred (liệt kê rõ) | NOT READY
   ```
8. **REFINE:** Xử lý các điểm tồn đọng từ bước Verify hoặc tinh chỉnh chi tiết trong phạm vi module. Nếu muốn thêm tính năng hoàn toàn mới ngoài phạm vi -> quay lại bước `VISION`.

## 4. Quy tắc phân cấp quyết định (Escalation L1 / L2 / L3)

- **Level 1 (Builder tự quyết & tự đệ quy):** Chi tiết cài đặt nội bộ và các lỗi kỹ thuật/test trong phạm vi 3 vòng đệ quy Retro Rubric không làm thay đổi hợp đồng giao tiếp (API/Schema/UI) đã chốt -> tự xử lý và ghi vào `DEVIATIONS` + `RETRO RUBRIC LOG`.
- **Level 2 (Builder -> Contractor):** Mơ hồ về đặc tả trong TIP, thay đổi pattern ảnh hưởng sang các TIP khác, hoặc **đã chạy hết 3 vòng đệ quy Retro Rubric mà vẫn chưa qua cổng**.
- **Level 3 (Contractor -> Con người):** Thay đổi phạm vi tính năng, kiến trúc cốt lõi, quy tắc nghiệp vụ, bảo mật hoặc chi phí.

> **Luật một câu phân định L1/L2:** Quyết định này có làm thay đổi bất kỳ điều gì đã chốt trong TIP/Blueprint, ảnh hưởng ra ngoài TIP hiện tại, hoặc vượt quá 3 vòng tự đệ quy Retro Rubric không? **Có → L2/L3. Không và đủ ngữ cảnh → L1 (tự xử lý và ghi nhận vào DEVIATIONS / RETRO LOG).**

## 5. Tài liệu tham chiếu chuyên sâu (`references/`)

Chỉ đọc file tham chiếu tương ứng khi bước công việc cần đến:

| Giao thức / Tài liệu | Đường dẫn | Khi nào sử dụng |
|---|---|---|
| **Retro Rubric Protocol (Đệ quy tối ưu)** | [references/retro-rubric-protocol.md](references/retro-rubric-protocol.md) | **Khi chạy vòng lặp BUILD ⇄ VERIFY, chấm điểm Rubric 5 chiều và rút kinh nghiệm đệ quy** |
| Debug Protocol (9 bước) | [references/debug-protocol.md](references/debug-protocol.md) | Khi vòng đệ quy Retro Rubric chạm trần 3 lần hoặc gặp lỗi hệ thống phức tạp |
| QA Protocol (3 tầng) | [references/qa-protocol.md](references/qa-protocol.md) | Bước Verify hoặc khi người dùng yêu cầu kiểm thử toàn diện |
| X-Ray Protocol (6 bước) | [references/xray-protocol.md](references/xray-protocol.md) | Khi tiếp nhận codebase mới, kiểm toán kỹ thuật hoặc bàn giao dự án |
| RRI Methodology | [references/rri-methodology.md](references/rri-methodology.md) | Khi cần chạy RRI, RRI-T (kiểm thử) hoặc RRI-UX (đánh giá UX) |
| RRI Question Bank | [references/rri-question-bank.md](references/rri-question-bank.md) | Ngân hàng câu hỏi gợi ý theo 5 personas |
| Vision Guide | [references/vision-guide.md](references/vision-guide.md) | Khi lập đề xuất kiến trúc và hướng thiết kế ở bước Vision |
| TIP & Report Formats | [references/tip-and-report-formats.md](references/tip-and-report-formats.md) | Mẫu chuẩn cho Scan, RRI, Blueprint, TIP, Completion, Retro Log & Verify Report |
| Templates | [references/templates.md](references/templates.md) | Mẫu đề xuất Vision, Refine, sơ đồ phụ thuộc Task Graph & Escalation |
| Walkthrough Example | [references/walkthrough-example.md](references/walkthrough-example.md) | Ví dụ minh họa xuyên suốt 8 bước từ đầu đến cuối |
| Scan Report Format | [references/scan-report-format.md](references/scan-report-format.md) | Hướng dẫn phân loại mức độ Scan codebase |

## Runtime (Claude.ai / Cowork)

- `SKILL_DIR` = thư mục chứa file `SKILL.md` này (lấy từ `location` trong `available_skills`, ví dụ `/mnt/skills/user/vibecode-kit` hoặc `/mnt/skills/plugins/vibecode-kit` tùy cách cài). Thư mục này chỉ-đọc: tạo và ghi dữ liệu dự án trong thư mục làm việc ghi được, không ghi vào `SKILL_DIR`.
- Cần `pyyaml` cho script Python (`pip install pyyaml --break-system-packages` nếu thiếu).
- Việc nhiều bước hoặc nối với skill khác trong bộ AI Native: đọc `SKILL.md` của `ai-work-method` để lấy bảng định tuyến và mẫu TIP/báo cáo.
