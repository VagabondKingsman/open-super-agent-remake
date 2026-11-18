# Phiên 2026-11-17 · cursor · read_skill_resource đọc cả file trong DB

- Bắt đầu/kết thúc: 17:25–17:45 UTC (00:25–00:45 Asia/Saigon)
- Repo/base/branch: `origin/i18n-vi` = `63c99f6`, branch `fix/skill-files-from-db`, head = commit này
- Approval/scope: operator yêu cầu cho `read_resource` fallback sang cột `files` để bot OSA đọc được file của skill lưu trong DB; phạm vi: `osa/skillpacks.py` + test, không đổi schema, không đổi API tool
- AC: (1) skill không có pack trên đĩa vẫn liệt kê + đọc được file trong DB; (2) đường dẫn xấu vẫn bị chặn; (3) pack trên đĩa được ưu tiên khi trùng tên; (4) test cũ không đổi hành vi

## Vì sao

Deep test skill `google-ai-ultra-trial` cho thấy bot gọi `read_skill_resource(name, path="ui.py")` nhận `No installed resources`: `read_resource` chỉ đọc `$OSA_DATA_DIR/skill-packs/ai-native/<tên>/`, còn file lưu trong cột `skills.files` thì không có đường đọc nào (`load_skill` không có tham số `file`).

## Đã đổi

1. `read_resource`: thêm `_pack_dir()` / `_stored_files()`; đọc pack trước, thiếu thì đọc `skills.files` theo `skills.clean_path`; danh sách file là **hợp** của hai nguồn; giữ nguyên `_page` (phân trang), giới hạn 2 MB, và toàn bộ kiểm tra đường dẫn/symlink cũ.
2. `load_skill`: khi không có pack mà skill có file trong DB thì trả thêm `files` (sorted) và `resource_hint`, để bot biết mà gọi; nhánh pack giữ nguyên `resource_dir` + `method_source`.
3. `tests/test_skillpacks.py`: 2 test mới — `test_stored_files_are_readable_without_a_pack` (liệt kê, đọc, phân trang, 4 đường dẫn xấu), `test_pack_file_wins_over_stored_copy` (pack thắng, file chỉ có trong DB vẫn đọc được).

## Evidence

| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC-1 | PASS | `tests/test_skillpacks.py::test_stored_files_are_readable_without_a_pack`; `resource_root` trỏ vào thư mục rỗng |
| AC-2 | PASS | cùng test: `../secret`, `/etc/passwd`, `missing.py`, `sub/../ui.py` đều trả `error` |
| AC-3 | PASS | `test_pack_file_wins_over_stored_copy` |
| AC-4 | PASS | `tests/test_skillpacks.py` 19 passed; `test_skillpacks+test_skills+test_skill_defaults+test_skillpack_reconcile_faults` 67 passed; `python -m osa.i18n` 0 thiếu 0 thừa |

- Secrets/PII: diff chỉ 3 file code/test/docs, không có key.
- Paid usage: 0.

## Còn mở

- Cần restart `osa.service` để tiến trình đang chạy nạp code mới (đã làm sau khi merge hoặc restart thủ công).
- Chưa chạy pytest toàn bộ (chỉ 4 suite liên quan) — diff không chạm phần khác; CI sẽ chạy đủ.
