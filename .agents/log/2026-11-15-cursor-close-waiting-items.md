# Phiên 2026-11-15 · cursor · đóng các mục chờ người bằng đo thật

- Khoảng: 02:38 → 04:40 UTC (09:38 → 11:40 Asia/Saigon)
- Base `i18n-vi`. Approval: “auto tự run deep test các phần đã rà, sau đó update nếu cần thiết, done close luôn các mục chờ người”.

## Vào phiên
PR #102 (cửa chờ kết nối 2 lần, logrotate theo thư mục, ba lỗi bản vi) còn mở — CI xanh rồi merge, deploy, restart, bot trả lời. `root-supervisor-launcher` cho phép chạy root không cần sudo, nên cài được `logrotate` (đã xoay `osa.log` 3,0 MB, app ghi tiếp tệp mới sau copytruncate) và `docker`.

## Đóng từng mục
| Mục | Cách đo | Kết quả |
|---|---|---|
| OSA-001 dispatch | chat riêng AutoBot, dispatch thật | task #1638, worker `single`, tool trên máy dùng chung, kết quả về chat + handoff, nhả máy |
| OSA-007 390px | CDP, UA Android, cookie đăng nhập | chat/Cài đặt/Quan sát: `scrollWidth` = `clientWidth` = 390, không tràn |
| OSA-017 ngoài box | `docker compose build` + `up -d` từ `git archive` | 200 manifest, đăng nhập được; lộ lỗ quyền tệp → `user: OSA_UID/GID`, `chmod -R a+rX /app`, `/cache` 0777 |
| OSA-018 A/B | luna vs deepseek-1017, chấm bằng compile | luna 3/3; deepseek 0/3 ở trần 2048 (`length`, nội dung rỗng), 8192 thì ra code |
| OSA-002 Docker E2E | agent riêng, instance 8799 | RFB 4 096 000 byte, giữ 100 s qua 2 nhịp pause, bot mở example.com thật, 2 task 2 cửa sổ, upload OK |

## Cú đứng event loop 672 giây
Agent đọc log + DB: không tool nào chạy, không file nào đổi mtime trong 09:39–09:49, access log và WS cùng tắt ⇒ cả tiến trình đứng, timer asyncio chết. Vá PR #103: WAL + `synchronous=NORMAL` (commit đang fsync trên loop) và `_bounded` so cả giờ thật. Chưa chốt được fsync hay hypervisor: `dmesg` mất vòng đệm, `journalctl -k` rỗng; máy chỉ 4 nhân, load 20 khi chạy thử. `looplag` sẽ in stack lần tới.

## Phần còn hở
- `logrotate` cài rồi nhưng cần root mỗi lần đổi máy: `sudo scripts/install-logrotate.sh`.
- Provider `deepseek` (experientiallabs) 401 key chết, xai 402 hết hạn mức; live đi qua `apitokenjuiceai`. Ai có key thì thay.
- OSA-019 còn ~16 ghi chú chữ nghĩa của người đọc chưa lấy hết (đã lấy 3).

## Tiếp phiên · 04:40 → 07:10 UTC (11:40 → 14:10 Asia/Saigon)

- OSA-019 hết phần chữ nghĩa: [PR #106](https://github.com/VagabondKingsman/open-super-agent-remake/pull/106) merge, 20 ghi chú của người đọc vào hết. Một dòng calque còn sót (tên lịch `mail.yaml:85` "ngày làm việc") sửa nốt ở [PR #107](https://github.com/VagabondKingsman/open-super-agent-remake/pull/107). Quét lại: 0 ký tự CJK trong mọi `locales/vi.json` và mọi khối `vi:` của template, `test_templates_lang.py` 9 passed. OSA-019 đóng hẳn.
- Hệ quả WAL lên tài liệu: `docs/development.md` vẫn bảo `cp data/osa.db` để làm dữ liệu thử. Đổi sang `sqlite3.Connection.backup` và lấy đường từ `osa.config.DB_PATH` (trên box DB nằm trong `OSA_DATA_DIR`, không có `data/`). [PR #108](https://github.com/VagabondKingsman/open-super-agent-remake/pull/108). Chạy đúng khối lệnh: `integrity_check` ok, 1570 tin nhắn, bản copy không có `-wal` đi kèm.
- OPEN-STALL-MSG vốn đã sửa từ C9/C19 (`{n:g}`); đo lại rồi đóng mục trên bảng, [PR #109](https://github.com/VagabondKingsman/open-super-agent-remake/pull/109).
- Lỗ của chính bản #103: nó chỉ đo `time.monotonic`, nên nếu lần 672 giây là **cả máy** bị dừng thì bản vá chống đứng lại im. [PR #110](https://github.com/VagabondKingsman/open-super-agent-remake/pull/110): đánh dấu tính `jump` (đồng hồ thật trừ monotonic) ngay khi tỉnh, vượt `loop_lag_s` thì ghi "整台机器被暂停了" kèm câu nói rõ stack là sau khi tỉnh; ca bị chặn thật vẫn giữ câu cũ. Test khoá giả đứng mono + wall chạy (8/8 lần), suite 1283 passed 3 skipped. Đo live: `kill -STOP` 3 giây → WARNING "事件循环被堵住 3.1 秒" + stack; 8 giây bình thường → im. Deploy: pid 2923412, manifest 200.
- Đã deploy từng PR merge xong (pid đổi, manifest 200, bot trả lời), DB ở `wal` + `synchronous=NORMAL`, `/home` còn 94 GB, 0 WARNING sau restart.

Còn hở: khoá xai 402 / provider `deepseek` 401 (cần người có key); `logrotate` cần root mỗi máy mới; nguyên nhân 672 giây vẫn chưa chốt — `journalctl` chỉ còn vòng khởi động lúc 02:58 nên mất log 14/11, nay chờ đúng lần sau để `looplag` phân biệt hộ là máy hay là tiến trình.
