# SOT · Mô hình dữ liệu và nguyên lý kiểm định

## 1. Bài toán giải quyết

Trong công việc thực tế, cùng một thông số (đơn giá, quy định, chỉ tiêu kỹ thuật) thường bị sao chép qua nhiều file; khi nguồn gốc thay đổi, các bản sao bị lệch mà không ai phát hiện, hoặc các con số ước tính ban đầu bị biến thành số liệu chính thức sau vài lần chuyển tiếp.

SOT giải quyết bằng chuỗi một chiều:
```text
Nguồn chuẩn có chủ sở hữu (source_canonical) → Adapter → Registry YAML → Baseline + Guard → Publish Gate → Tài liệu xuất
```

## 2. Ba mức độ tin cậy (Provenance Taxonomy)

- `verified_primary`: Thông tin đã có bằng chứng sơ cấp theo quy chuẩn dự án (hợp đồng, giấy phép, biên bản nghiệm thu, datasheet chuẩn). Được phép giữ trường `value`.
- `claim`: Thông tin ước tính nội bộ, dự thảo hoặc chưa đủ chứng từ sơ cấp. Công cụ `hygiene.py split` sẽ chuyển giá trị sang trường `claim` và đặt `verified_value: null` để ngăn việc sử dụng nhầm như số liệu đã chốt.
- `flagged`: Thông tin đang có mâu thuẫn giữa các nguồn nội bộ, cần chủ sở hữu phân xử.

## 3. Nghi thức cập nhật dữ liệu chuẩn

Khi có thay đổi hợp lệ từ chủ sở hữu nguồn:
1. Cập nhật file gốc trong `source_canonical/`.
2. Chạy lại adapter để sinh `registry/` mới và chạy `hygiene.py fill` + `split --apply`.
3. Kiểm tra diff của registry để đảm bảo thay đổi đúng chủ đích.
4. Chạy `sot_baseline.py <project_dir> accept` để cập nhật vân tay SHA-256.
5. Chạy `sot_check.py <project_dir>` và `sot_publish.py <project_dir> gate` để cấp lại token xuất bản mới.
