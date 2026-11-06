# Kiểm patch trên fixture thật, không cần Docker

OSA có hai tool giống nhau ở Router/Worker:

1. `inspect_repo(repo)`: chỉ đọc repo operator đã đăng ký; trả toàn bộ file trong allowlist, test sẵn có và snapshot SHA-256.
2. `check_patch(repo, snapshot, patch)`: yêu cầu snapshot còn đúng; kiểm đường dẫn/mode patch; copy source sang thư mục tạm; chạy git apply --check, apply và pytest trong bubblewrap offline. Chỉ trả PASS nếu cả ba exit code bằng 0, giữ nguyên bytes test cũ và repo gốc không thay đổi.

Patch cuối phải khớp patch_sha256 từ tool PASS. Đếm hunk không thay apply/test. Không giao patch khi FAIL/BLOCKED; sửa và kiểm lại trong giới hạn vòng hoặc báo blocker thật. Comment trong code như `# discount.py` là nội dung file, không tự bỏ như nhãn. Test đã tồn tại thì không tạo lại file; chỉ append import/test ở cuối.

## Đăng ký bởi operator

Mặc định không có quyền đọc/chạy repo nào. Operator đặt `local-checks.json` cạnh SQLite data DB, không phải tool của model. Ví dụ dùng đường dẫn do operator đã duyệt:

```json
{"example":{"path":"/absolute/approved/fixture","files":["example.py","test_example.py"],"tests":["test_example.py"],"acceptance_file":"/absolute/operator/test_contract.py"}}
```

Chỉ đăng ký fixture nhỏ, tin cậy; không đăng ký repo OSA, home hay thư mục chứa credential. `files` là file text hiện có, không symlink, giới hạn mỗi file; inspect result quá lớn thì báo BLOCKED và cần thu hẹp allowlist. `tests` phải thuộc files. Acceptance file tùy chọn do operator kiểm soát được bind read-only ngoài thư mục code, không cho patch sửa. JSON này và kết quả chạy trong data là local-only, không commit.

Môi trường: Linux có `bubblewrap` (`bwrap`), util-linux (`prlimit`), procps (`ps`), Git và Python/pytest trong venv OSA. User namespaces phải hoạt động. Nếu thiếu, trả BLOCKED và lý do; **không fallback sang host shell không cô lập**.

## Ranh giới an toàn

- Không có tool nhập command, cài package, chọn URL hoặc tự đăng ký repo. Lệnh Git/pytest do server cố định.
- Bubblewrap tạo user/mount/PID/network namespaces mới, clear env, drop capabilities. Chỉ bind system runtime/venv read-only, copy fixture vào /work, acceptance read-only và /tmp riêng. Không bind home/config/key của host.
- Không có mạng host/Internet trong sandbox. Smoke test kiểm file canary ngoài sandbox không tồn tại và localhost host không truy cập được.
- Timeout mỗi lệnh, CPU/memory/file-output/fd limits; process headroom tính theo số thread uid hiện có + giới hạn nhỏ vì box dùng chung. Không gọi limit đó là cgroup quota riêng.
- Test cũ append-only; không thể xóa assertion cũ qua patch để làm xanh. PASS vẫn chỉ là kết quả test được cấu hình, không chứng minh hết ngữ nghĩa hay độ an toàn của ứng dụng.
- Không apply vào repo gốc. Evidence lưu ở data/local-check-results/<id>/result.json; chỉ patch PASS mới có accepted.patch. Kết quả tool bị rút log sẽ ghi output_truncated.

Unit tests dùng source tự tạo. Test kernel isolation thực skip trên host thiếu Linux/bubblewrap; không giả PASS sandbox. Đây là đường kiểm fixture được cấp quyền, không thay Computer hay cấp khả năng chạy tùy ý trên host.
