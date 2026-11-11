# Kế hoạch: từ OSA hôm nay → "super bot" (2026-11-11)

Nguồn: deep audit 4 nhánh (test-suite · bản đồ tính năng · computer-use · live E2E) trên chính
bản đang chạy ở `boxes.dev` (86 module / 27 202 dòng / 150 route / 909 test).

**Nguyên tắc bất biến**

1. Mỗi thay đổi đi kèm test hồi quy + một scenario trong `tests/evals` nếu nó đổi hành vi.
2. Đo trước / đo sau, ghi số vào commit message (ttft, số frame, token, $, ms).
3. Không sửa quá 1 subsystem mỗi vòng; suite phải xanh (`pytest -q`) trước khi chuyển vòng.
4. Không thêm phụ thuộc mới nếu thư viện chuẩn làm được.

---

## Vòng A — Ổn định & quan sát được (mục tiêu: 1 ngày)

| # | Việc | Neo | Cách làm | Nghiệm thu | ~giờ |
|---|---|---|---|---|---|
| A0 | ✅ `/api/*` lạ trả JSON 404 | `server.py:1988` | đã làm | 3/3 path 404 JSON, test `test_audit_p0.py` | 0,2 |
| A1 | ✅ VM ngủ → tự đánh thức | `computer/instabox.py:192` | `_wake_retry` cho `exec`/`read_bytes` | 409 không còn tới model; 4 test | 0,5 |
| A2 | Prompt hết tự mâu thuẫn | `router.py` system prompt | bỏ câu cấm tool khi đã khuyến khích `quick_code`; một quy tắc duy nhất "trả lời trực tiếp nếu không cần máy" | turn `17*23`: thinking < 1,5 s, ttft < 4 s (đo lại 5 turn) | 1 |
| A3 | `/ws` phát `tool` + `approval` frame | `router.py` (emit), `web/src/store` | frame `{type:"tool", id, name, args_brief, state:"run|ok|err"}`; frontend hiện chip trạng thái | turn có tool: ≥2 frame, UI thấy bước đang chạy; test ở `tests/test_ws_frames.py` | 2 |
| A4 | Telemetry từng turn | `router.py` meta, `observe.py` | ghi `usage{tokens_in,out,cache}`, `cost_usd`, `ttft_ms`, `tool_ms[]` vào `meta` message | `/api/chats/1/messages` có đủ khoá; tổng khớp `/api/observe` ±1% | 1,5 |
| A5 | `osa-smoke.sh` thành test | `scripts/`, `tests/` | `tests/test_fastsrv.py`: gzip round-trip + immutable + 304 | test chạy trong suite, không cần server thật | 0,5 |
| A6 | CI bật display | `tests/test_host_computer.py:344` | thêm `xvfb-run -a` vào lệnh suite; sửa reason của gate `darwin` | **+27 test**, suite ~92 s | 0,3 |
| A7 | Log về một chỗ | `server.py` logging | thêm handler ghi `osa.log` + `journalctl` thấy dòng app | `journalctl --user -u osa` có ≥1 dòng/request | 0,3 |

**Cổng ra vòng A:** suite ≥ 938 test xanh · 5 turn live có số ttft/tool · không còn 5xx trong 30 phút.

---

## Vòng B — Năng lực & an toàn (2–3 ngày)

| # | Việc | Neo | Nghiệm thu |
|---|---|---|---|
| B1 | `computer_shell` qua xác nhận trên mọi backend | `computer/tools.py` | VM: lệnh đầu mỗi task hỏi; `tasklog` ghi cmd + exit code; test giả lập |
| B2 | VNC bền | `computer/instabox.py:open_vnc`, `down()` | `ping_interval=20`; rơi → `close(1011)`, client hiện "mất hình" < 2 s |
| B3 | Không treo im lặng | `base.wait_for_control` | phát `notify_progress` + `ComputerError` sau 120 s (cấu hình được) |
| B4 | Cách ly theo task | `computer.get(bot_id)` | mỗi task một profile Chromium; test 2 task không đọc được cookie của nhau |
| B5 | Failover nhiều máy | `instabox.py` | 2 machine: máy chính chết → chuyển trong < 10 s, ghi `metadata.role` |
| B6 | i18n cho snapshot | `cdp_helper.py:97` | chuỗi `(cuộn 0/10306, cao 669)`, 3 locale, test so khớp |
| B7 | `ls()` nhanh | `instabox.py` | < 800 ms (hiện 3,5 s) |
| B8 | Test 5 adapter kênh | `channels/*.py` (1 583 dòng, 0 test) | `FakeHTTP` phủ: pair, dedupe, gửi media, retry/rate-limit; ≥ 20 test |
| B9 | Test nhóm/teach/memory-merge | `groups.py`, `teach.py`, `memory.py` | mỗi cái ≥ 5 test; scenario eval "2 bot chuyển việc cho nhau" |

---

## Vòng C — Vòng tự cải thiện (liên tục)

1. **Cổng eval bắt buộc:** `tests/evals` (27 scenario) chạy trong mọi lần sửa; thêm 1 scenario cho mỗi lỗi thật đã sửa (bắt đầu từ A2–A4).
2. **Sinh scenario từ log:** script đọc `osa.log` + `tasklog` → đề xuất scenario mới cho lỗi lặp ≥ 2 lần.
3. **Self-check trước khi trả lời:** dùng `verification.py` cho turn có số liệu/đường dẫn; sai → tự sửa 1 lần (đã có `verification_repair_attempts`).
4. **Ngân sách & hồi quy chi phí:** theo dõi `$/turn` từ A4; chặn khi vượt 2× trung bình 7 ngày.
5. **Báo cáo tuần:** 1 trang từ `/api/observe` + eval: ttft, tok/s, success, $, lỗi mới.

---

## KPI (đo được, hiện tại → mục tiêu)

| Chỉ số | Hiện | Mục tiêu vòng A | Vòng B |
|---|---|---|---|
| ttft turn thường | 2,49 s (7 ngày) | ≤ 1,8 s | ≤ 1,2 s |
| Chữ đầu turn `17*23` | 7,10 s | ≤ 4 s | ≤ 3 s |
| Frame tool trên `/ws` | 0 | ≥ 2/turn có tool | đủ bước + approval |
| Chi phí/turn | không đo được | có trong `meta` | dashboard |
| Test | 911 | ≥ 938 | ≥ 1 000 |
| Op computer (snapshot) | 0,44 s | giữ | ≤ 0,4 s |
| Lỗi 5xx / 7 ngày | 1 | 0 | 0 |

## Rủi ro & lối thoát

- Sửa prompt (A2) có thể đổi "tính cách" bot → giữ song song 1 turn mẫu trước/sau, so 5 câu trả lời.
- Frame mới trên `/ws` (A3) làm client cũ bỏ qua field lạ → an toàn; nếu vỡ, client kiểm `type` đã có default.
- `_wake_retry` (A1) có thể che lỗi thật: chỉ retry đúng chuỗi `machine_not_running`, mọi lỗi khác ném nguyên.
- Rollback: mỗi vòng một commit riêng; `git revert` là đủ, không đụng dữ liệu người dùng.

## Việc cần operator quyết

1. Duyệt vòng A (A2–A7) — tôi chạy tuần tự, báo sau mỗi mục.
2. Có bật `xvfb` trong lệnh suite mặc định không (thêm 27 test, +5 s)?
3. Telemetry A4 ghi token/$ vào `meta` message: chấp nhận được chứ (dữ liệu chỉ nằm trong DB của bạn)?
