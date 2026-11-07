# Refinery · Hướng dẫn vận hành nhanh

Bộ công cụ tất định giúp tổng hợp dữ liệu từ nhiều nguồn ngoài, bảo toàn dấu vết trích dẫn và phát hiện mâu thuẫn.

## Chạy thử trên domain mẫu (`domains/training-demo`)

```bash
python3 refinery.py domains/training-demo
python3 bites.py domains/training-demo
python3 new_domain.py my-catalog "Danh mục sản phẩm" --output-root /tmp
```

## Cấu trúc một thư mục Domain

```text
<domain_dir>/
├── domain.yaml      # Khai báo schema, alias_map, ambiguous_clusters, universe, domain_gates
├── claims.jsonl     # Danh sách các claim đã trích xuất (mỗi dòng 1 JSON)
├── staging.jsonl    # (Tuỳ chọn) Hàng đợi các claim chờ người duyệt qua review.py
└── snapshots/       # Các bản chụp văn bản/HTML gốc làm bằng chứng đối chiếu
```

## Các cổng kiểm tra tự động (Gates)

- `SOURCED_ATTR`: Kiểm tra đầy đủ `entity`, `field`, `value`, `tier` (A/B/C), `extraction` và `capture`.
- `CAPTURE_MISSING`: Đảm bảo file snapshot khai báo thực sự tồn tại trong `snapshots/`.
- `SPAN_NOT_FOUND`: Đảm bảo `evidence_span` xuất hiện nguyên văn trong snapshot (hỗ trợ giải mã HTML entity và chuẩn hóa Unicode NFC).
- `AMBIGUOUS_MERGE_UNFLAGGED`: Chặn việc tự ý gộp hai thực thể nằm trong nhóm dễ nhầm lẫn (`ambiguous_clusters`).
- `DISTRIBUTION_NO_DENOMINATOR`: Chặn việc công bố thống kê phân bố (`rollup_field`) mà không khai báo mẫu số (`universe.estimate`).
- `AUDIT` & `IDEMPOTENT`: Auditor độc lập tính toán lại toàn bộ các ô và tổng hợp từ `claims.jsonl` để chống sai lệch; chạy lặp 2 lần đảm bảo kết quả khớp từng byte.
