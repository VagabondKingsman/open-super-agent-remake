# Kế hoạch: từ OSA hôm nay → "super bot" (2026-11-11)

Nguồn: deep audit 4 nhánh (test-suite · bản đồ tính năng · computer-use · live E2E) trên chính
bản đang chạy ở `boxes.dev` (86 module / 27 202 dòng / 150 route / 909 test).

**Nguyên tắc bất biến**

1. Mỗi thay đổi đi kèm test hồi quy + một scenario trong `tests/evals` nếu nó đổi hành vi.
2. Đo trước / đo sau, ghi số vào commit message (ttft, số frame, token, $, ms).
3. Không sửa quá 1 subsystem mỗi vòng; suite phải xanh (`pytest -q`) trước khi chuyển vòng.
4. Không thêm phụ thuộc mới nếu thư viện chuẩn làm được.


**Tiến độ (2026-11-11)**

| vòng | xong | ghi chú |
|---|---|---|
| A | A0–A7 ✅ | suite 1 051 → 1 099 test |
| B | B1–B9 ✅ | test kênh 92, nhóm 13, teach 13, memory 8; 3 bug thật (xem commit B8/B9) |
| C | C1, C2, C4, C5, C6, C7 ✅ · C3 đã có sẵn (`verification_repair_attempts`) | 32 scenario (thêm e28–e32) |
| D | C6 ✅ (mỗi lượt chỉ ghi công cụ của nó) · C7 ✅ (ngưỡng cost_guard theo trung vị) · C8 ✅ (chặn kết quả tool cũ trong worker) | 2 lỗi thật tìm từ dữ liệu live; chi phí worker là chỗ tốn nhất |

Chi phí tuần (báo cáo đầu tiên): 5,97 $ · 191 lần gọi · 5 lỗi · ttft 2 336 ms · cache 66 %.

---

## Vòng A — Ổn định & quan sát được (mục tiêu: 1 ngày)

| # | Việc | Neo | Cách làm | Nghiệm thu | ~giờ |
|---|---|---|---|---|---|
| A0 | ✅ `/api/*` lạ trả JSON 404 | `server.py:1988` | đã làm | 3/3 path 404 JSON, test `test_audit_p0.py` | 0,2 |
| A1 | ✅ VM ngủ → tự đánh thức | `computer/instabox.py:192` | `_wake_retry` cho `exec`/`read_bytes` | 409 không còn tới model; 4 test | 0,5 |
| A2 | ✅ Prompt hết tự mâu thuẫn | `router.py` system prompt | bỏ câu cấm tool khi đã khuyến khích `quick_code`; một quy tắc duy nhất "trả lời trực tiếp nếu không cần máy" | turn `17*23`: thinking < 1,5 s, ttft < 4 s (đo lại 5 turn) | 1 |
| A3 | ✅ `/ws` phát `tool` frame | `router.py:_tool`, `web/src/toolRun.ts` | frame `{type:"tool", name, state:"run|ok|err", brief, ms}`; chip `.tool-run` cập nhật tại chỗ | turn có tool: 2 frame; DOM có `quick_code 48 ms` (đo bằng Chrome headless); `web/tests/tool-run.cjs` | 2 |
| A4 | ✅ Telemetry từng turn | `router.py:_count_usage/_usage_meta`, `web/src/Chat.tsx` | `meta.usage{in,out,cache,cost,ttft,sec,tools[{n,ms,b}]}`; dưới mỗi câu trả lời một dòng `↑in ↓out · $cost · thời gian`, hover xem cache/ttft; chip tool đã chạy giữ lại sau reload | `/api/chats/{id}/messages` có đủ khoá; 1 lượt 2 vòng = 2 dòng `llm_calls`, in/out/cost khớp tuyệt đối | 1,5 |
| A5 | ✅ `osa-smoke.sh` thành test | `tests/test_fastsrv.py` | ASGI app gọi thẳng: gzip round-trip, immutable + etag, 304, Range/`..` rơi xuống StaticFiles, JSON tự nén | 10 test, không cần server thật (0,1 s) | 0,5 |
| A6 | ✅ Suite tự bật display | `scripts/test.sh`, `tests/test_host_computer.py:326` | `scripts/test.sh` bọc `xvfb-run -a` khi không có `DISPLAY`; sửa gate: `OSA_TEST_CHROME` chưa đặt không còn bị coi là “tắt” | **+13 test** (930 pass / 1 skip, 93 s) | 0,3 |
| A7 | ✅ Log về một chỗ | `server.py:LOG_FORMAT`, `scripts/osa-start.sh` | log app có `thời gian M logger: nội dung`; mỗi lần khởi động một dòng `osa <version> starting, data=…`; `osa-start.sh` ghi nối tiếp và chuyển `osa.log` > 20 MB thành `osa.log.1` | `logs/osa.log` có dòng khởi động + dòng app có giờ; `tests/test_logging.py` (7 test) | 0,3 |

**Cổng ra vòng A:** suite ≥ 938 test xanh · 5 turn live có số ttft/tool · không còn 5xx trong 30 phút.

---

## Vòng B — Năng lực & an toàn (2–3 ngày)

| # | Việc | Neo | Nghiệm thu |
|---|---|---|---|
| B1 ✅ | `computer_shell` qua xác nhận trên mọi backend | `computer/tools.py` | VM: lệnh đầu mỗi task hỏi; `tasklog` ghi cmd + exit code; test giả lập |
| B2 ✅ | VNC bền | `computer/instabox.py:open_vnc`, `down()` | `ping_interval=20`; rơi → `close(1011)`, client hiện "mất hình" < 2 s |
| B3 ✅ | Không treo im lặng | `base.wait_for_control` | phát `notify_progress` + `ComputerError` sau 120 s (cấu hình được) |
| B4 ✅ | Cách ly theo task | `computer.get(bot_id)` | mỗi task một profile Chromium; test 2 task không đọc được cookie của nhau |
| B5 ✅ | Failover nhiều máy | `instabox.py` | 2 machine: máy chính chết → chuyển trong < 10 s, ghi `metadata.role` |
| B6 ✅ | i18n cho snapshot | `cdp_helper.py:97` | chuỗi `(cuộn 0/10306, cao 669)`, 3 locale, test so khớp |
| B7 ✅ | `ls()` nhanh | `instabox.py` | < 800 ms (hiện 3,5 s) |
| B8 ✅ | Test 5 adapter kênh | `channels/*.py` (1 583 dòng, 0 test) | `FakeHTTP` phủ: pair, dedupe, gửi media, retry/rate-limit; ≥ 20 test |
| B9 ✅ | Test nhóm/teach/memory-merge | `groups.py`, `teach.py`, `memory.py` | mỗi cái ≥ 5 test; scenario eval "2 bot chuyển việc cho nhau" |

---

## Vòng C — Vòng tự cải thiện (liên tục)

1. ✅ **Cổng eval bắt buộc:** `tests/evals` (27 scenario) chạy trong mọi lần sửa; thêm 1 scenario cho mỗi lỗi thật đã sửa (bắt đầu từ A2–A4).
2. ✅ **Sinh scenario từ log:** `scripts/scenario_from_log.py` (5 test) —  script đọc `osa.log` + `tasklog` → đề xuất scenario mới cho lỗi lặp ≥ 2 lần.
3. ✅ **Self-check trước khi trả lời:** C3 — số mà câu trả lời nêu ra (“8 lần”, “150 dòng”, “3 steps”) chỉ được coi là có thật khi nó xuất hiện trong kết quả tool của lượt này hoặc trong ngữ cảnh lượt đó đọc được; không khớp thì cho model một lượt sửa theo kết quả tool, vẫn không khớp thì ghi `meta.self_check`. C12 đặt giờ thật vào khối trạng thái mỗi lượt để câu “mấy giờ” không còn bịa.
4. ✅ **Ngân sách & hồi quy chi phí:** `memory.turn_cost_cap` + `router` dừng gọi tool khi một lượt > 3× **trung vị** 7 ngày (`limits.turn_cost_guard`, 5 test);  theo dõi `$/turn` từ A4.
   C7 (sau khi đọc số thật): trung vị thay trung bình — một lượt chạy lố tự nó đẩy trung bình lên
   (một lượt $2 trong 12 lượt $0,04 làm trung bình từ $0,04 lên $0,20) nên ngưỡng 2× trung bình
   tự nới đúng lúc cần siết; trung vị đứng yên. Số đo 2026-11-11 (14 lượt): trung vị $0,0418,
   p90 $0,138, cao nhất $0,179 → ngưỡng $0,125, chỉ mở khi thật sự lệch.
5. ✅ **Báo cáo tuần:** `scripts/weekly_report.py` (5 test) —  1 trang từ `/api/observe` + eval: ttft, tok/s, success, $, lỗi mới.

6. ✅ **Mỗi lượt chỉ ghi tool của lượt đó:** C6 — `_turn_tool_ms` được làm mới đầu lượt; trước đó mỗi lượt lại
   mang theo danh sách tool của lượt trước, dài dần (thấy trong `meta` của bản chạy thật).
7. ✅ **Task dài không gửi lại mọi tool result:** C8 — `worker._compact_tools` nén các bước cũ, giữ bước gần nhất đầy đủ.
8. ✅ **Model treo thì đổi sang model dự phòng:** C9 — `roles.<role>.fallback`; stream đứt hai lần liền thì lượt đó
   chạy tiếp trên model dự phòng thay vì báo lỗi (một lần cho mỗi lượt, ghi vào log).
9. ✅ **“Đã giao worker rồi” mà không gọi dispatch:** C10 — bắt được cả khi câu không kèm `#N`, dựa trên chính
   hai lượt thật ở chat 1 (#118, #120); sửa một lượt, vẫn không giao thì nối câu đính chính + `meta.claimed_dispatch`.
10. ✅ **Lượt sửa phải thật sự gọi dispatch:** C11 — vòng sửa gửi `tool_choice` buộc gọi `dispatch` (chỉ request
    đầu của vòng; service không nhận `tool_choice` thì lùi về vòng thường). Chat 1 (94 tin) trước đó trả lời bằng lời
    ba lần liền; sau C11 giao ngay lượt đầu.
11. ✅ **Giờ thật trong lượt:** C12 — khối trạng thái mỗi lượt mở bằng giờ server (UTC). Trước đó hỏi “mấy giờ”
    thì bot bịa 12:20 UTC trong khi máy đang 08:11, và còn nói đã gọi `quick_code` mà không gọi.


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
