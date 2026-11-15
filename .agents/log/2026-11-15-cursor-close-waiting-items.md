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

## Tiếp phiên · 09:30 → 11:40 UTC (16:30 → 18:40 Asia/Saigon)

- **Nguyên nhân 672 giây ngày 14/11 đã chốt**: không phải fsync, không phải tiến trình — **cả máy bị host treo**. Bản `looplag` của #110 ghi được 10 lần trong một buổi, dài 50,7″ / 116″ / 210″ / 232″ / 235″ / 598″ / 1191″ / 1942″ / 2321″ (log `osa.log`, 14:42–17:21 giờ máy). `CLOCK_BOOTTIME` ≈ `monotonic` nên không phải suspend ACPI; host (boxes.dev) đóng băng microVM rồi chỉnh lại giờ thật khi tỉnh. `journalctl` chỉ còn vòng khởi động 02:58 nên 14/11 không tra lại được.
- Hệ quả nặng: mọi timeout tính bằng `time.time()`, nên mỗi lần tỉnh dậy Watchdog thấy “300 giây không tiến triển” với mọi task đang chạy và **giết sạch**; `task_timeout_s` cũng vậy. Đây là lý do các task “model didn't produce an answer” giữa phiên.
- Vá [PR #116](https://github.com/VagabondKingsman/open-super-agent-remake/pull/116): `osa/clock.py` (`monotonic`, không âm), dùng cho `started`, `last_progress`, `paused_s`, hạn `granted`/`_vm_said`, cửa sổ 600″ của bảng nhóm; `time.time()` chỉ còn cho `ts` trong DB, hạn thẻ chờ duyệt. Test: đồng hồ thật nhảy 40 phút mà task chạy 2 giây vẫn sống; chạy thật 120 giây thì bị huỷ; 45 giây không tiến triển thì bị huỷ.
- [PR #115](https://github.com/VagabondKingsman/open-super-agent-remake/pull/115): đường “hứa dán kết quả thì đánh thức lại Bot” chưa bao giờ chạy — `_turn_block` lấy `woke["from"]` trước nhánh `own_task` nên mọi lần đánh thức đều `KeyError('from')` (`W osa.router: waking after task 1672 failed ('from')`). Đo lại sau khi deploy: task #1678 xong, Bot tự nói tiếp, không còn dòng cảnh báo.
- [PR #114](https://github.com/VagabondKingsman/open-super-agent-remake/pull/114): `dispatch` lấy id tin nhắn làm khoá `TASKS`; xoá Bot thì SQLite dùng lại id và đè lên task đang chạy. Nay trùng thì cấp số mới, số thật ghi vào meta, `update_meta`/`tasklog.detail` đọc theo đó. Thêm fixture dọn `TASKS` giữa các test. Đo: hai lần dispatch trên cùng một id, cả hai task còn nguyên, `#` đúng, meta `task_id` = `1672`/`1673`.
- [PR #113](https://github.com/VagabondKingsman/open-super-agent-remake/pull/113): `OSA_COMPUTER_MOUNTS` mount thêm thư mục vào máy của bot (mặc định `ro`). **Chưa dùng được trên box này**: backend là `instabox`, mà Instabox không ăn biến mount. Đo lại: Nova không thấy `/data/repo`. Lối tạm đã dùng: `computer.write_bytes` chép `BOARD.md`/`STATE.md` vào `/data/workspace/agents/`.
- [PR #112](https://github.com/VagabondKingsman/open-super-agent-remake/pull/112): test hết giờ tự dừng của `teach` đỏ khi đứng một mình (chờ trạng thái trước khi sự kiện tới) — chờ đúng sự kiện.

Còn hở: Instabox không mount được (cần cách khác nếu muốn bot đọc repo); máy bị treo thì vẫn treo, nay chỉ không còn giết task; khoá xai 402 / deepseek 401 vẫn chờ người.
