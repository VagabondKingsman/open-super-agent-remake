---
name: sot-kernel-in-a-box
description: >-
  Xây dựng, kiểm toán và vận hành kho dữ liệu chuẩn nội bộ (Source of Truth - SOT) dựa trên file: owner cho từng file gốc, adapter sang registry, vân tay SHA-256 phát hiện lệch nguồn, tách verified_primary/claim/flagged (A3 Guard), 6 bite test tiêm lỗi và publish gate gắn digest. Dùng khi số liệu nội bộ phân tán giữa Excel/CSV/Word dễ mâu thuẫn, cần một nguồn sự thật duy nhất, data governance, single source of truth, audit số liệu trước khi xuất báo cáo/deck/báo giá/đề án, hoặc đưa dữ liệu đã duyệt từ refinery vào kho chuẩn. Thuộc bộ AI Native: với việc nhiều bước, đọc thêm ai-work-method.
---

# SOT Kernel-in-a-Box · Kho dữ liệu chuẩn có kiểm định

Thiết lập chuỗi dữ liệu có thể kiểm toán từ file nguồn chuẩn đến registry máy đọc và các tài liệu xuất bản:

```text
source_canonical → adapter → registry → baseline/check → publish gate → exports
```

Mọi cổng kiểm tra đều chạy tất định bằng script Python. Sử dụng AI để khảo sát, đề xuất, viết adapter hoặc soạn thảo tài liệu; tuyệt đối không dùng LLM thay thế bước kiểm định (`sot_check.py`, `sot_bites.py`, `sot_publish.py`).

## 1. Bảy nguyên tắc bất biến

1. **Nguồn chuẩn duy nhất:** Chỉ sửa dữ liệu tại `source_canonical/`. Mọi file trong `registry/` và `exports/` đều là bản dẫn xuất.
2. **Chủ sở hữu rõ ràng:** Mỗi file nguồn chuẩn phải có người chịu trách nhiệm (owner) ghi trong `PROJECT.yaml`.
3. **Bảo toàn mức độ tin cậy (Provenance A3):**
   - `verified_primary`: Đã có bằng chứng sơ cấp theo chuẩn dự án -> được phép giữ trường `value`.
   - `claim`: Ước tính, bản nháp hoặc chưa đủ bằng chứng sơ cấp -> tách sang `claim` và đặt `verified_value: null` để chặn việc vô tình trích xuất như sự thật cứng.
   - `flagged`: Có mâu thuẫn hoặc tranh chấp -> đưa vào `_queue/conflicts_pending.md` chờ chủ sở hữu phân xử.
4. **Fail-loud (Báo lỗi tường minh):** Vi phạm cấu trúc hoặc provenance phải dừng cổng xuất (exit code 2), không tự động hạ mức lỗi để lấy kết quả xanh.
5. **Chứng minh cổng biết bắt lỗi:** Chỉ tin tưởng hệ thống sau khi chạy `sot_bites.py` xác nhận cả 6 phép tiêm lỗi đều bị chặn.
6. **Cổng xuất gắn digest:** Mọi thao tác xuất qua `sot_publish.py` yêu cầu `.publish_token` khớp với digest hiện tại của nguồn, cấu hình, adapter và registry.
7. **Tách biệt dữ liệu dự án:** Dữ liệu thực tế nằm ở thư mục dự án riêng của người dùng, không lưu lẫn vào thư mục cài đặt skill.

Đọc [README.md](README.md) để xem lệnh chạy nhanh và [LY_THUYET_CHUYEN_GIAO.md](LY_THUYET_CHUYEN_GIAO.md) để nắm rõ mô hình dữ liệu và giới hạn.

## 2. Chọn chế độ vận hành

- **Khởi tạo dự án SOT mới:** Sao chép `project_template/` sang thư mục dự án của người dùng và làm theo quy trình 7 bước bên dưới.
- **Kiểm toán (Audit) dự án SOT hiện có:** Đọc `PROJECT.yaml`, `sot.yaml`, `sot.hygiene.yaml`, kiểm tra nguồn chuẩn, adapter, registry, sau đó chạy `sot_check.py` và `sot_bites.py`.
- **Cập nhật khi file nguồn thay đổi hợp lệ:** Chạy lại adapter -> đối chiếu diff trong `registry/` -> chạy `hygiene.py fill/split --apply` (nếu có fact mới) -> chạy `sot_baseline.py accept` -> `sot_check.py` -> cấp lại token qua `sot_publish.py gate`.
- **Xuất bản tài liệu (Publish):** Chạy `sot_publish.py gate`, kiểm tra `status`, đối chiếu số liệu trong tài liệu với `registry/` rồi xuất qua `sot_publish.py publish`.

## 3. Quy trình dựng dự án SOT mới

1. Sao chép `project_template/` sang thư mục đích do người dùng chỉ định.
2. Điền thông tin dự án và chủ sở hữu nguồn vào `PROJECT.yaml`; cập nhật tên `org` trong `sot.yaml`.
3. Ánh xạ từ vựng trạng thái nội bộ (ví dụ: `VERIFIED`, `CHỐT`, `DRAFT`, `INT`, `FLAG`) vào 3 mức chuẩn trong `sot.hygiene.yaml`.
4. Đặt các file dữ liệu gốc vào `source_canonical/`.
5. Tạo hoặc chỉnh sửa adapter trong `adapters/` (dựa trên mẫu `adapters/adapter_csv.py`) đảm bảo mỗi fact có ID duy nhất, trạng thái rõ ràng và kết quả chạy tất định.
6. Chạy chuỗi lệnh chuẩn hóa và khởi tạo vân tay:

```bash
python3 "$SKILL_DIR/tools/hygiene.py" fill "$PROJECT_DIR/registry" --config "$PROJECT_DIR/sot.hygiene.yaml" --apply
python3 "$SKILL_DIR/tools/hygiene.py" split "$PROJECT_DIR/registry" --config "$PROJECT_DIR/sot.hygiene.yaml" --apply
python3 "$SKILL_DIR/tools/sot_baseline.py" "$PROJECT_DIR" init
python3 "$SKILL_DIR/tools/sot_check.py" "$PROJECT_DIR"
python3 "$SKILL_DIR/tools/sot_bites.py" "$PROJECT_DIR"
python3 "$SKILL_DIR/tools/sot_publish.py" "$PROJECT_DIR" gate
```

## 4. Tiêu chí hoàn thành (Completion Criteria)

Chỉ báo cáo hệ thống SOT sẵn sàng khi:
- Đã ghi nhận chủ sở hữu cho toàn bộ file trong `source_canonical/`.
- Adapter chạy tất định và đã kiểm tra diff của `registry/`.
- `sot_check.py` trả về `PASS` (khớp vân tay baseline + 0 vi phạm A3 Guard).
- `sot_bites.py` trả về `TẤT CẢ RĂNG CẮN ✓` (6/6 bài kiểm thử tiêm lỗi đều bắt được).
- `sot_publish.py status` xác nhận token hợp lệ với digest hiện tại.
- Liệt kê minh bạch các mục đang ở trạng thái `claim` hoặc `flagged` để người dùng nắm.

## Runtime (Claude.ai / Cowork)

- `SKILL_DIR` = thư mục chứa file `SKILL.md` này (lấy từ `location` trong `available_skills`, ví dụ `/mnt/skills/user/sot-kernel-in-a-box` hoặc `/mnt/skills/plugins/sot-kernel-in-a-box` tùy cách cài). Thư mục này chỉ-đọc: tạo và ghi dữ liệu dự án trong thư mục làm việc ghi được, không ghi vào `SKILL_DIR`.
- Cần `pyyaml` cho script Python (`pip install pyyaml --break-system-packages` nếu thiếu).
- Việc nhiều bước hoặc nối với skill khác trong bộ AI Native: đọc `SKILL.md` của `ai-work-method` để lấy bảng định tuyến và mẫu TIP/báo cáo.
