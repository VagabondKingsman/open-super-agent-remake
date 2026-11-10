# OSA-031: port upstream v0.13.0–v0.17.0

## Mục tiêu

- BOARD: OSA-031. Owner: hoplite. Branch `hoplite/osa-031-port-v0.17`. Base `i18n-vi` `1466670` (PR #26). Head `4e3fe66`.
- Port upstream v0.13.0–v0.17.0 (`ec02547`) lên remake. Giữ tiếng Việt mặc định, prompt tiếng Anh, chi phí USD, AI Native, và các sửa bảo mật/độ tin cậy đã có. Version ghi 0.17.0.
- TIP-001 chọn máy tính và khóa Instabox trong vault. Docker chưa chạy vẫn báo `unavailable` của remake.
- TIP-002 tool chỉ đọc cạnh nhau chạy song song. Lệnh ghi, máy tính, và bước cần xác nhận vẫn tuần tự.
- TIP-003 gỡ plugin nhà phát triển, chợ plugin, `/api/plugins`, `security.plugins`. Dữ liệu cũ không bị xóa, cũng không còn nạp.
- TIP-004 giao diện theo hệ thống, sáng, hoặc tối. Bỏ trang Chi phí. Đơn giá USD ở trang Mô hình.
- TIP-005 terminal trên Mac đang cho server mượn, mặc định tắt (`computer.linked_shell`). Mỗi lệnh vẫn phải xác nhận. App Mac cũ không chạy lệnh.

## Verify

- TIP-001: `tests/test_computer_choice.py` cùng hardening, link, security: 44 pass.
- TIP-002: `tests/test_parallel_tools.py` 24 pass. Lọc worker, heavy, approval, dispatch: 82 pass.
- TIP-003: security, parallel, sources, i18n, registry: 101 pass. `uv run python -m osa.i18n`: thiếu 0, thừa 0.
- TIP-004: `tsc` sạch, web test 33/33.
- TIP-005: `tests/test_computer_link.py` 8 pass sau khi sửa assert hint tiếng Anh.
- Chưa chạy full pytest. Chưa chạy Docker Computer E2E. Chưa mở app Mac thật. DB cũ còn bảng `plugins` hay không: NOT_CHECKED.
- Không gọi model trả phí. Không gửi channel. `git diff --check` sạch trước commit.

## Rủi ro

- App Mac phải cập nhật mới chạy được lệnh terminal. App cũ nhận từ chối rõ, không chạy lệnh.
- Plugin đã cài không còn chạy. File trong `data/plugins` và bảng DB cũ còn đó.
- Rollback là revert merge commit này. Không force-push, không đụng dữ liệu người dùng.

## Quyền

Luu Giac duyệt merge cho OSA-031 trong thread này. Method `merge` (merge commit). Không squash, không rebase. Không PR lên upstream.
