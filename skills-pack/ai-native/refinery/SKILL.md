---
name: refinery
description: >-
  Tập hợp và đối chiếu dữ liệu từ nhiều nguồn ngoài (web, báo cáo, tài liệu công khai) thành registry truy nguyên được (claims, snapshots, evidence_span, origin_id, disputed, honest-null) bằng engine Python tất định có bite test. Dùng khi người dùng cần danh mục/bảng so sánh đối thủ, sản phẩm, nhà cung cấp, giá, thông số, dataset nghiên cứu, market research, competitor table, source-backed dataset, fact-check nhiều nguồn, hoặc bất kỳ bảng số liệu nào mà mỗi ô phải có nguồn kiểm chứng. Không dùng thay kho dữ liệu nội bộ đã có owner (dùng sot-kernel-in-a-box). Thuộc bộ AI Native: với việc nhiều bước, đọc thêm ai-work-method.
---

# Refinery · Engine tinh luyện và đối chiếu dữ liệu nguồn ngoài

Xây dựng bộ dữ liệu (registry) truy nguyên được từ từng ô số liệu về đúng phát biểu gốc (`claims.jsonl`), đoạn văn bản nguyên mẫu (`evidence_span`) và bản chụp tài liệu (`snapshots/`).

## 1. Bốn trạng thái dữ liệu cốt lõi

- `sourced`: Có 1 nguồn hợp lệ trích xuất rõ ràng.
- `corroborated`: Cùng giá trị được xác nhận bởi ít nhất 2 nguồn độc lập (`origin_id` khác nhau) thuộc nhóm chất lượng A hoặc B.
- `disputed`: Các nguồn đưa ra giá trị khác nhau cho cùng một trường. Giữ nguyên tất cả các claims đối lập và đặt `value: null`, tuyệt đối không tự động chọn nguồn thắng.
- `null` (`honest-null`): Chưa có dữ liệu hoặc chưa có nguồn hợp lệ. Giữ trống minh bạch thay vì suy đoán.

## 2. Quy trình thực thi 5 bước

1. **Khởi tạo domain và khai báo schema:**
   Chạy `python3 "$SKILL_DIR/new_domain.py" <ten-domain> "<Nhãn thực thể>" --output-root <thu-muc-dich>` để tạo khung chuẩn gồm `domain.yaml`, file claim rỗng (`claims.json`; engine chấp nhận cả `claims.json` và `claims.jsonl`) và thư mục `snapshots/`. Khai báo các trường (`schema.fields`), ánh xạ tên gọi (`alias_map`), cụm tên dễ nhầm (`ambiguous_clusters`) và mẫu số (`universe.estimate` + `basis`) nếu cần tính tỷ lệ bao phủ.
2. **Lưu bản chụp và trích xuất claims:**
   Lưu nội dung văn bản/HTML gốc vào `snapshots/`. Mỗi dòng trong `claims.jsonl` gồm: `entity`, `field`, `value`, `evidence_span` (đoạn trích nguyên văn nằm trong snapshot), `extraction` (`verbatim` | `normalized` | `inferred`), `tier` (`A` | `B` | `C`) và `capture` (`url`, `fetched_at`, `snapshot`, `source`, `origin_id`).
3. **Khử trùng nguồn sao chép (`origin_id`):**
   Nếu hai trang web dẫn lại cùng một bản tin hoặc báo cáo gốc, phải gán chung `capture.origin_id` để engine không đếm nhầm thành hai nguồn độc lập (`corroborated`).
4. **Chạy pipeline tất định và kiểm thử răng cắn (`bites`):**
   ```bash
   python3 "$SKILL_DIR/refinery.py" "<duong-dan-domain>"
   python3 "$SKILL_DIR/bites.py" "<duong-dan-domain>"
   ```
   Engine tự động kiểm tra sự tồn tại của snapshot, đối chiếu `evidence_span` (sau khi chuẩn hóa HTML entity và Unicode NFC), chạy Auditor độc lập dựng lại toàn bộ bảng từ claims và kiểm tra tính tất định (idempotent).
5. **Duyệt ngữ cảnh và bàn giao:**
   Dùng `python3 "$SKILL_DIR/review.py" "<duong-dan-domain>" list|approve|reject` nếu có quy trình duyệt claim từ `staging.jsonl`. Khi bàn giao kết quả, luôn giữ rõ các mục `disputed`, `null` và mẫu số phân bố.

## 3. Lưu ý và phối hợp với các Skill khác

- **Snapshot trên Claude.ai:** lưu nội dung lấy từ `web_fetch` thành file `.txt`/`.md` (không bắt buộc `.html`); `evidence_span` phải chép nguyên văn từ chính file đó.
- **Phân tier khi thẩm định:** trang của chính đối tượng đang bị kiểm (tự tuyên bố) xếp tier `C` để không tự cộng điểm `corroborated`; nguồn đối tác/cơ quan nhà nước là `A`; trang tổng hợp lại danh sách nhà nước là `B` và các trang tổng hợp cùng một danh sách gốc phải chung `origin_id`.
- **Cổng `VALUE_IN_SPAN` (khuyến nghị bật cho số liệu):** khai `domain_gates.value_in_span_fields: [amount, quantity, ...]` để engine chặn claim có số trong `value` không xuất hiện trong `evidence_span`.
- **Giới hạn đã biết:** `refresh_days` hiện chỉ là khai báo, engine chưa tự đánh dấu dữ liệu cũ — tự đối chiếu `fetched_at`/thời điểm nguồn khi hai giá trị lệch nhau theo thời gian (vd. địa chỉ cũ vs mới) và ghi rõ trong báo cáo thay vì tự chọn bên thắng.

- Gate máy xác nhận `evidence_span` nằm trong `snapshot`, nhưng người thực hiện vẫn phải đọc ngữ cảnh để đảm bảo đoạn trích thực sự khẳng định `value` (không trích sai ngữ cảnh hoặc nhầm mục tiêu kế hoạch thành kết quả thực tế).
- Khi cần chuyển các dữ liệu đã chốt từ `refinery` vào kho chuẩn nội bộ, hãy kết hợp với skill `sot-kernel-in-a-box`: chủ việc duyệt các claim được chọn rồi đưa qua adapter vào `source_canonical/`.

Đọc [README.md](README.md) để xem hướng dẫn lệnh CLI và [LY_THUYET_CHUYEN_GIAO.md](LY_THUYET_CHUYEN_GIAO.md) để nắm chi tiết 7 giai đoạn tinh luyện dữ liệu.

## Runtime (Claude.ai / Cowork)

- `SKILL_DIR` = thư mục chứa file `SKILL.md` này (lấy từ `location` trong `available_skills`, ví dụ `/mnt/skills/user/refinery` hoặc `/mnt/skills/plugins/refinery` tùy cách cài). Thư mục này chỉ-đọc: tạo và ghi dữ liệu dự án trong thư mục làm việc ghi được, không ghi vào `SKILL_DIR`.
- Cần `pyyaml` cho script Python (`pip install pyyaml --break-system-packages` nếu thiếu).
- Việc nhiều bước hoặc nối với skill khác trong bộ AI Native: đọc `SKILL.md` của `ai-work-method` để lấy bảng định tuyến và mẫu TIP/báo cáo.
