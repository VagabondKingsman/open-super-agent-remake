# Retro Rubric Protocol · Đệ quy tối ưu và rút kinh nghiệm từ lần chạy thử sai

## 1. Mục đích và Khi nào kích hoạt

Giao thức **Retro Rubric** biến mọi lần build/test thất bại thành quy tắc phòng ngừa tự động cho các vòng lặp kế tiếp, giúp AI không lặp lại cùng một kiểu lỗi trong suốt dự án.

**Kích hoạt tự động khi:**
1. Lần chạy thử (`BUILD` hoặc `TEST`) báo lỗi biên dịch, lỗi kiểu (type/lint), hoặc trượt bất kỳ tiêu chí nghiệm thu (`AC`) nào.
2. Bước `VERIFY` phát hiện điểm số trong **Bảng chấm Retro Rubric 5 chiều** chưa đạt ngưỡng chuẩn (có bất kỳ mục nào `FAIL` hoặc tổng điểm `< 9/10`).
3. Người dùng yêu cầu chạy chế độ tự tối ưu đệ quy (*"chạy retro rubric"*, *"đệ quy tối ưu build"*).

## 2. Bảng chấm Retro Rubric 5 chiều (5-Dimension Scorecard)

Mỗi vòng chạy thử (`Iteration #k`) được chấm trên 5 tiêu chí (thang điểm `0 - 2` mỗi chiều, tổng `10`):

| Mã | Chiều đánh giá | Mức 2 (PASS - Chuẩn) | Mức 1 (WARN - Cần gọt) | Mức 0 (FAIL - Bắt buộc đệ quy) |
|---|---|---|---|---|
| **R1** | **Spec & Contract Fidelity** (Độ khớp đặc tả & Hợp đồng) | Đạt 100% AC trong TIP; giữ đúng API/Schema/UI đã chốt | Đạt AC chính nhưng thiếu tinh chỉnh nhỏ về thông báo/hiển thị | Trượt AC bắt buộc hoặc tự ý làm lệch hợp đồng giao tiếp |
| **R2** | **Runtime & Test Integrity** (Thực thi & Kiểm thử thực tế) | Build xanh, 0 lỗi type/lint, 100% test chạy thực tế PASS | Build và test chính PASS nhưng còn cảnh báo lint/type nhẹ | Lỗi biên dịch/runtime, test FAIL hoặc chưa chạy test thực tế |
| **R3** | **Edge-Case & Resilience** (Tình huống biên & Chịu lỗi) | Xử lý trọn vẹn dữ liệu rỗng, đầu vào sai, lỗi mạng/biên | Xử lý được luồng chính và lỗi cơ bản, thiếu 1 tình huống biên phụ | Crash hoặc trả kết quả sai im lặng khi gặp dữ liệu biên/rỗng |
| **R4** | **Blast-Radius, Hygiene & YAGNI** (Phạm vi, Sạch code & YAGNI Thực dụng) | Chỉ sửa đúng phạm vi TIP, tái sử dụng tốt hàm sẵn có, không tạo abstraction/file thừa, không gây hồi quy | Có mã thừa/log tạm hoặc tạo helper phụ chưa tối giản nhưng không gây lỗi hồi quy | Gây regression ở tính năng cũ, sửa lan ngoài TIP, hoặc vi phạm nặng YAGNI (viết lại hàm đã có / đẻ tầng trung gian dự phòng) |
| **R5** | **Anti-Repeat Discipline** (Kỷ luật không lặp lỗi cũ) | Tuân thủ 100% các `RETRO-ID` đã ghi nhận từ các vòng trước | Phải sửa lại một lỗi tương tự ở vòng nháp nhưng đã tự bắt được | Tái phạm một lỗi đã từng có trong danh sách `RETRO-ID` |

**Điều kiện qua cổng (Exit Gate):** Tổng điểm `>= 9/10` **VÀ** không có tiêu chí nào bị `0 (FAIL)`.

### Tiêu chuẩn kiểm tra YAGNI Thực dụng trong chiều `R4`

Trước khi tạo bất kỳ file, class hoặc hàm mới nào trong bước `BUILD`, và khi chấm điểm chiều `R4` ở bước `VERIFY`, luôn áp dụng 3 câu hỏi lọc:

1. **Sự tồn tại (Existence):** Thành phần này có phục vụ trực tiếp một `AC` trong `TIP` hiện tại không? (Nếu chỉ là `Factory`/`Interface`/`Wrapper` dự phòng cho tương lai chưa có trong Blueprint → hạ `R4` và xóa bỏ).
2. **Tái sử dụng (Reuse):** Đã đối chiếu mục `REUSABLE_COMPONENTS` trong `SCAN REPORT` và thư viện chuẩn chưa? (Nếu tự viết lại một hàm tiện ích đã tồn tại trong codebase → `R4 = 0 FAIL`, bắt buộc xóa hàm trùng và gọi hàm sẵn có).
3. **Độ phức tạp tối thiểu (Minimum Viable Complexity):** Nếu buộc phải viết mới, giải pháp đã chọn có phải là cách đơn giản, trực tiếp và ít tầng trung gian nhất mà vẫn giữ trọn vẹn kiểm tra kiểu (`R2`) và xử lý biên (`R3`) không? (Cấm rút gọn cực đoan kiểu "code golf" làm mất xử lý lỗi hoặc giảm khả năng đọc hiểu).


## 3. Vòng lặp Đệ quy 4 bước (Recursive Self-Optimization Loop)

```text
   ┌───────────────────────────────────────────────────────────────────────┐
   │                                                                       │
   ▼                                                                       │
[BUILD & TEST] ──► [CHẤM RETRO RUBRIC (R1..R5)] ──► Đạt Gate? ──► (PASS) ──┼──► Bàn giao / Qua TIP mới
                             │                                             │
                        (Chưa đạt)                                         │
                             │                                             │
                             ▼                                             │
              [1. Phân tích Root Cause & Điểm trượt Rubric]                │
                             │                                             │
                             ▼                                             │
              [2. Đúc kết Quy tắc RETRO-ID (Symptom → Cause → Guardrail)]  │
                             │                                             │
                             ▼                                             │
              [3. Nạp ngược Guardrail vào Test + TIP hiện tại & kế tiếp] ──┘
```

Khi bất kỳ tiêu chí `R1..R5` nào trượt, AI tự động thực hiện 4 bước đệ quy (không cần chờ người dùng nhắc từng lỗi):

### Bước 1: Chẩn đoán nguyên nhân gốc theo Rubric (Rubric Gap Diagnosis)
- Không sửa mò (no blind patching). Xác định chính xác tiêu chí nào trượt (`R1`..`R5`), dòng code/cấu hình gây lỗi và giả định sai ban đầu.

### Bước 2: Đúc kết Quy tắc Phòng ngừa (`RETRO-ID`)
- Ghi nhận một mục mới theo định dạng chuẩn:
  ```text
  RETRO-[XX]:
    - Bối cảnh / Triệu chứng (Symptom): [Lỗi gì đã xảy ra ở vòng thử #k]
    - Nguyên nhân gốc (Root Cause): [Vì sao cách làm cũ bị sai]
    - Quy tắc chặn (Executable Guardrail): [Điều kiện kiểm tra hoặc test case bắt buộc phải thoả mãn ở mọi lần build sau]
  ```

### Bước 3: Nạp ngược vào Hệ thống (Feed-Forward Mutation)
1. **Nạp vào bộ kiểm thử (Regression Bite):** Viết thêm assertion hoặc test case bắt trực tiếp lỗi vừa gặp để nếu lỗi tái xuất hiện, test sẽ đỏ ngay lập tức.
2. **Nạp vào TIP hiện tại & các TIP tiếp theo:** Thêm `RETRO-[XX]` vào mục `ACTIVE RETRO GUARDRAILS` của TIP đang chạy và toàn bộ các TIP chưa chạy trong `TASK GRAPH`.

### Bước 4: Tái thực thi và Chấm lại (Re-Build & Re-Score)
- Chạy lại code/test, chấm lại bảng `R1..R5` và ghi nhận sự tiến bộ (`Iteration #k -> Iteration #k+1`).

## 4. Cầu chì chống lặp vô hạn (Circuit Breaker)

- Giới hạn tối đa **3 vòng đệ quy liên tiếp** cho cùng một lỗi/TIP.
- Nếu sau vòng thử thứ 3 vẫn chưa vượt qua cổng Retro Rubric:
  1. Dừng tự sửa để tránh làm nát kiến trúc (thrashing).
  2. Kích hoạt `Debug Protocol` hoặc xuất báo cáo `Escalation Report (Level 2/3)` gửi Contractor/Con người, đính kèm bảng nhật ký cả 3 vòng thử và danh sách `RETRO-ID` đã thu thập.

## 5. Mẫu Nhật ký Đệ quy (Retro Rubric Log)

```markdown
## RETRO RUBRIC LOG — TIP-[XXX]

### Bảng tiến trình điểm qua các vòng thử
| Vòng thử | R1 (Spec) | R2 (Runtime) | R3 (Edge) | R4 (Hygiene) | R5 (No-Repeat) | Tổng | Kết quả |
|----------|-----------|--------------|-----------|--------------|----------------|------|---------|
| Vòng #1  | 2         | 0 (FAIL)     | 1         | 2            | 2              | 7/10 | RETRY   |
| Vòng #2  | 2         | 2            | 2         | 2            | 2              | 10/10| PASS    |

### Các bài học đã chuyển hóa thành Guardrail (Active Retro Rules)
- **RETRO-01:**
  - *Triệu chứng:* Lỗi `TypeError` khi API trả về mảng rỗng ở bộ lọc trạng thái (Vòng #1).
  - *Nguyên nhân gốc:* Hàm map dữ liệu giả định response luôn có trường `items` dạng mảng khác null.
  - *Quy tắc chặn (Guardrail):* Mọi hàm đọc danh sách từ API phải chuẩn hóa `const items = Array.isArray(res?.items) ? res.items : []` và có 1 unit test cho trường hợp payload rỗng `{}`.
```

## 6. Công cụ thực thi tất định (`scripts/retro_rubric.py`)

Đi kèm với giao thức là engine CLI `scripts/retro_rubric.py` giúp khóa chặt kỷ luật đệ quy bằng mã lệnh (chặn việc bỏ qua bước rút kinh nghiệm hoặc lặp vô hạn):

```bash
# 1. Khởi tạo sổ cái Retro Rubric cho dự án (mặc định tối đa 3 vòng/TIP, ngưỡng đạt 9/10)
python3 "$SKILL_DIR/scripts/retro_rubric.py" init "$PROJECT_DIR"

# 2. Chấm điểm sau một vòng chạy thử (trả về exit 0 = PASS, exit 2 = RETRY, exit 3 = ESCALATE)
python3 "$SKILL_DIR/scripts/retro_rubric.py" evaluate "$PROJECT_DIR" --tip TIP-001 --r1 2 --r2 0 --r3 1 --r4 2 --r5 2 --notes "Lỗi null mảng"

# 3. Bắt buộc đúc kết bài học RETRO-ID để mở khóa vòng chạy thử tiếp theo
python3 "$SKILL_DIR/scripts/retro_rubric.py" learn "$PROJECT_DIR" --tip TIP-001 \
  --symptom "TypeError khi mảng rỗng" \
  --cause "Thiếu bước chuẩn hóa response" \
  --guardrail "Luôn fallback về mảng rỗng và có unit test kiểm tra" \
  --test-cmd "pytest tests/test_empty_payload.py"

# 4. Kiểm tra hồi quy toàn bộ các quy tắc RETRO-ID đã khóa (đảm bảo R5 = 2/2)
python3 "$SKILL_DIR/scripts/retro_rubric.py" verify-guardrails "$PROJECT_DIR"

# 5. Xuất bảng điểm và nhật ký đệ quy ra Markdown để chèn vào Completion / Verify Report
python3 "$SKILL_DIR/scripts/retro_rubric.py" report "$PROJECT_DIR" --tip TIP-001

# 6. Tự kiểm tra tính toàn vẹn của cổng đệ quy và cầu chì
python3 "$SKILL_DIR/scripts/retro_rubric.py" selftest
```
