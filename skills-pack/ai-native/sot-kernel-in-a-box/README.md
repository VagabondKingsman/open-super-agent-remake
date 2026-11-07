# SOT Kernel-in-a-Box · Hướng dẫn sử dụng nhanh

Bộ công cụ quản lý kho dữ liệu chuẩn nội bộ (Source of Truth) có kiểm định nguồn gốc và cổng xuất bản.

## Chạy thử trên dự án mẫu (`examples/demo_org`)

Từ thư mục gốc của skill:

```bash
python3 tools/sot_check.py examples/demo_org
python3 tools/sot_bites.py examples/demo_org
python3 tools/sot_publish.py examples/demo_org gate
python3 tools/sot_publish.py examples/demo_org status
```

## Các công cụ trong `tools/`

- `sot_baseline.py <project_dir> <init|check|accept>`: Quản lý vân tay SHA-256 của các file nguồn trong `source_canonical/`.
- `hygiene.py <guard|fill|split|access|ethical|falsify> <registry_dir> --config <sot.hygiene.yaml> [--apply]`: Gắn nhãn provenance, tách các giá trị chưa xác minh sang `claim` (nguyên tắc A3) và kiểm tra các cổng mở rộng.
- `sot_check.py <project_dir>`: Chạy đồng thời `sot_baseline.py check` và `hygiene.py guard`, ghi nhật ký vào `index/verify_log.jsonl`.
- `sot_bites.py <project_dir>`: Tạo bản sao tạm, tiêm 6 loại lỗi (sửa trộm nguồn, phơi value của fact chưa xác minh, sửa registry sau gate, thiếu token, sửa nguồn sau gate, sửa cấu hình sau gate) để chứng minh các cổng hoạt động đúng.
- `sot_publish.py <project_dir> <gate|status|publish>`: Cấp `.publish_token` khi kiểm tra đạt và cho phép sao chép file sang `exports/` khi token còn hiệu lực.

## Lưu ý giới hạn

- Cổng `publish` đảm bảo tính toàn vẹn của chuỗi dữ liệu nguồn/registry/cấu hình tại thời điểm xuất, nhưng không tự đọc hiểu nội dung văn bản trong file báo cáo tự do. Luôn đối chiếu các con số trong tài liệu xuất với `registry/`.
