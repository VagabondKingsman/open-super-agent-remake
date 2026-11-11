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
| D | C6 ✅ (mỗi lượt chỉ ghi công cụ của nó) · C7 ✅ (ngưỡng cost_guard theo trung vị) · C8 ✅ (chặn kết quả tool cũ trong worker) · C18–C21 ✅ (cache của worker, đo rồi sửa hai lần) | 2 lỗi thật tìm từ dữ liệu live; chi phí worker là chỗ tốn nhất |

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

| Chỉ số | Hiện (đo 2026-11-11) | Mục tiêu vòng A | Vòng B |
|---|---|---|---|
| ttft turn thường | 0,66–1,8 s (đo 11/11 sau C14/C15; trước đó 2,27 s) | ≤ 1,8 s | ≤ 1,2 s |
| Chữ đầu turn `17*23` | 11,4 s (2 tool, đáp 391) | ≤ 4 s | ≤ 3 s |
| Frame tool trên `/ws` | có, 1–2 mỗi lượt gọi tool | ≥ 2/turn có tool | đủ bước + approval |
| Chi phí/turn | trong `meta.usage`; tuần này 242 lượt = $6,93. Sau C14/C15: $0,010–0,012 mỗi lượt router (trước: $0,026) | có trong `meta` | dashboard |
| Test | 1 129 | ≥ 938 | ≥ 1 000 |
| Op computer (snapshot) | 0,44 s | giữ | ≤ 0,4 s |
| Lỗi gọi model / 7 ngày | 5 | 0 | 0 |

Đọc bảng này cho đúng: đơn vị đang chạy **không phải** cấu hình trong `config.yaml`. Phần `overrides` trong bảng
`settings` của DB đặt `roles.router = grok-4.7, thinking: true, reasoning_effort: high` (và worker/reviewer như vậy),
nên mọi lượt đều chạy bằng model đắt + suy luận sâu: 6,92 $ trong tuần gần như toàn bộ rơi vào grok-4.7, và "chữ đầu"
là chữ đầu của phần suy luận, không phải của câu trả lời. Muốn so với mục tiêu ttft thì hạ `reasoning_effort` hoặc
bỏ thinking cho router rồi đo lại; chưa làm vì đó là lựa chọn của operator.

### C13–C15: cache của nhà cung cấp (đo 11/11)

Cache không phải “tiền tố giống nhau là trúng”: nó phục vụ khi **request này là phần mở rộng nguyên văn của một
request đã gửi**. Đo trực tiếp (`scripts/cache_probe.py`): sửa một chữ ở đầu → 1152/7584 token; sửa ở cuối → 7552/7584.
Vì thế mỗi lượt trước đây trả tiền gần như cả 17–18k token đầu vào: lần gọi đầu mỗi lượt trúng 5–8%.

Đã sửa: khối “Earlier turns were removed…” (lớn thêm mỗi lượt) dời vào khối trạng thái ở cuối; trạng thái đã gửi
được lưu nguyên văn vào chính tin nhắn đó (`memory.remember_state`); các vòng gọi tool (assistant `tool_calls` +
kết quả `tool`) cũng được lưu và gửi lại đúng thứ tự (`memory.keep_tail`). Hai test giữ tính chất “body sau là phần
mở rộng của body trước”, kể cả lượt có tool. Đo lại trên chat thật: các body nối tiếp nhau 100%; lần gọi trong cùng
lượt trúng 99–100%; lần gọi đầu lượt trúng 95–100% ở phần lớn lượt (đo sau C16: 4/5 lượt, ttft 0,6–2,2 s,
0,013–0,014 $ mỗi lượt router; lượt còn lại 5% — thỉnh thoảng vẫn trượt dù body nối tiếp đúng, chưa rõ lý do — đo ra ở dưới). Prompt lớn dần vì mỗi lượt mang theo state (~440 ký tự) và các vòng tool của
lượt trước; cửa sổ `memory.inline_messages` vẫn cắt đều nên có chặn trên.

**5% còn lại là cửa sổ trượt, không phải lỗi nhà cung cấp (C17).** `memory.context` chỉ dời mốc cắt một lần mỗi
`n = memory.inline_messages` = 20 tin (`cut = (len-n)//n*n`), nên phần lớn lượt là phần mở rộng của lượt trước;
lượt đúng lúc mốc nhảy thì tin đầu tiên đổi, phần sau system prompt trượt hết — vì thế mọi lần trượt đều báo
trúng đúng 1152 token, bằng riêng system prompt. Giá: ~0,02 $ mỗi lần nhảy (đọc lại body ở giá miss 2,02 $/Mtok
thay vì 0,50 $/Mtok — hai giá này suy ra từ hai lần gọi đã đo), khoảng 1 lần mỗi 10 lượt.
Mô phỏng lại 76 lượt của chat 1 (giá thật ở trên, token ước theo ký tự) cho n = 6…24 và vài chính sách cắt theo
ngân sách: $/lượt giảm khi cửa sổ nhỏ (n=6: 0,0010 $; n=16: 0,0015 $; n=20: 0,0015 $; n=24: 0,0017 $) nhưng cửa sổ
nhỏ thì bot thấy ít lịch sử hơn, và mọi chính sách cắt theo ngân sách đều đắt hơn. n=20 đã nằm trên đoạn phẳng của
đường cong → giữ nguyên: đây là chỗ đã tối ưu, không phải chỗ còn nợ.
Cách đo lần sau (đừng đoán): `printf '<thư mục>' > $OSA_DATA_DIR/prompt-dump` bật ghi nguyên văn từng body, chạy
một lượt có tool, rồi so từng cặp body liền nhau — tìm ra đúng tin đầu tiên khác nhau.

### C18: worker cũng phải giữ được cache (đo 11/11)

Trong cùng một task, worker gọi model 5–30 lần, mỗi lần gửi lại toàn bộ lịch sử. Đo trên DB: 135 lần gọi
worker đã tiêu 4,02 $ (hơn cả router), trong đó **1,03M token là miss (25%)**; riêng 21 lần gọi giữa task
chỉ trúng 1152 token — 559k token miss, ~0,85 $ (21% tiền worker) trả cho việc đọc lại một body vừa gửi xong.

Nguyên nhân: `_compact_tools` (C8) và `prune_images` cắt bớt lịch sử cũ, nhưng cắt *mỗi bước một ít*:
- `_compact_tools` tính tổng chỉ trên các kết quả dài, mà bản đã cắt (1500 ký tự + dòng ghi chú) vẫn “dài”, nên
  sau khi cắt xong tổng vẫn quanh ngưỡng 60k → bước sau lại vượt, lại cắt đúng một tin (cô lập “3 tin cuối” trượt
  từng bước) → **bước nào cũng đổi tiền tố**.
- `prune_images(keep=2)` thay ảnh cũ ngay khi có ảnh thứ 3 → mỗi ảnh mới là một lần đổi tiền tố.

Đã sửa: cắt một lần cho tới khi tổng ≤ `worker_compact_to_chars` (mới, 20k) — một lần cắt đổi lấy nhiều bước
trúng; ảnh chỉ thay khi đã có `keep + 4` tấm; thêm `worker_result_chars` (8000) thành cấu hình thay cho số 8000
viết cứng. Test: một lần cắt phải để tổng dưới ngưỡng và hai bước sau không được đụng vào lịch sử; ảnh phải
được thay theo lô; bản đã cắt không bị cắt hai lần.
Đo lại sau khi có ~20 task mới: `select role, cache_hit, cache_miss from llm_calls where role='worker'` —
mong đợi miss% của worker giảm từ 25% xuống dưới 15%, và không còn dãy lần gọi nào chỉ trúng 1152.

### C19: một task chết mà không gọi model lần nào (đo 11/11)

Task #212: router giao việc xong, 3 phút sau Watchdog hủy (“không có tiến triển”), `task_steps` chỉ có đúng dòng hủy,
`llm_calls` không có lấy một dòng của worker. Truy ra: `_reply_once` chờ `create_chat` — tức là chờ kết nối và
response header — mà client của openai mặc định chờ **600 giây**, dài hơn Watchdog (180 s) và dài hơn cả mọi
giới hạn khác trong `limits`. Kết nối bị treo thì không có lỗi, không có dòng nào được ghi, `last_progress` đứng yên,
và Watchdog hủy task trước khi bất cứ thứ gì kịp xảy ra. `stream_idle_s`/`stream_first_chunk_s` chỉ áp cho
*stream đã mở*, không áp cho giai đoạn kết nối.

Đã sửa: `limits.provider_head_s` (mới, 120) — request stream phải có response header trong 120 s, quá thì ném
`StreamStalled` (đúng loại “đáng gọi lại”): worker gọi lại một lần rồi chuyển sang model dự phòng; router cũng gọi lại như khi stream bị treo.
Request không stream thì không áp (cả câu trả lời vốn dài). Test: client giả treo → `StreamStalled` trong
khoảng 0,05 s (không treo), `retry_midstream` = True; `_reply` gọi lại lần hai và trả lời được.
Chỗ này trước đó cũng không có test nào — “kết nối treo” là lỗ hổng cuối cùng của đường ổn định (A1–A7).

### C18: đo lại trên task thật (11/11, sau khi lên bản chạy)

Đo bằng body ghi nguyên văn (`printf '<thư mục>' > $OSA_DATA_DIR/prompt-dump`) rồi so từng cặp
body liền nhau trong cùng task — không đoán qua cache_hit. Sáu task thật (#234, #235, #236, #243,
#247, #251):

- Bốn task ngắn (#234–#236 hai lần gọi, #243 năm lần): body sau là phần mở rộng nguyên văn của body
trước, 0 lần đứt do code. Riêng lần gọi cuối của #243 nhà cung cấp vẫn tính là miss (trúng 1152
token) dù body nối tiếp — “trượt” không phải lúc nào cũng do ta. Probe riêng (`scripts/cache_extend_probe.py`,
8 bước nối tiếp, không có app nào ở giữa): bước 3 trượt, 7 bước còn lại trúng 66–88%.
- #247 (9 lần gọi): 7 lần nối tiếp, đúng 1 lần đứt ở chỗ nén (body 65 526 → 41 438 ký tự),
giá $0,048 = 23 459 token miss. Đó là giá của một lần nén.
- #251 (20 bước, kết quả ~8k ký tự): 17 lần nối tiếp, 5 lần đứt, cả 5 đều là nén; sau mỗi lần
nén body vẫn còn 47 897 ký tự — 3 kết quả mới nhất cộng 10 bản đã cắt 1500 vẫn trên ngưỡng, nên
5 bước sau lại nén (xem C21).
- So với trước C18: 22/120 lần gọi giữa task (18%) chỉ trúng 1152 token; sau C18: 7/37 (19%).
Tỉ lệ **không giảm**, vì cái đắt nhất chính là lần nén — C18 chỉ đổi nhịp nén, không bỏ được nó.
- Đo lại bất cứ lúc nào: `.venv/bin/python scripts/worker_cache.py [--since TS]` (cột `1152-only`
là số lần cả body bị đọc lại) và `--bodies <thư mục>` (chỗ đứt đầu tiên, kèm hai tin để so).

### C20: một task chết trong im lặng — lần thứ hai

Task #247 sau lần gọi thứ 8: x.ai trả header 200 lúc 11:36:17, rồi **189 giây không một khối nào**.
`task_steps` không có dòng nào, `llm_calls` cũng không, sau 3 phút Watchdog hủy vì “3 phút không có tiến triển”.
Đúng cái đã gặp ở #212 (C19), nhưng lần này có bằng chứng: mọi giới hạn (header 120, khối đầu 170
giây) đều **đã** nằm trong khoảng 189 giây đó mà không cái nào nổ.

Lý do: `guard_stream` bọc từng khối bằng `asyncio.wait_for`. Khi hết giờ, `wait_for` hủy task rồi
**chờ task đó kết thúc thật sự**; một stream còn giữ kết nối mà nuốt luôn `CancelledError` thì không
bao giờ kết thúc — giới hạn thành vô nghĩa. Thử trực tiếp: stream nuốt `CancelledError` → code cũ
treo vô hạn, code mới nổ đúng ở 0,05 giây.

Đã sửa: `providers._bounded()` dùng `asyncio.wait` — hết giờ là đi tiếp, task bị bỏ lại tự kết thúc
(loại hết warning). Dùng cho cả giai đoạn kết nối (C19) và từng khối của stream. Thêm
`limits.no_progress_s = 300` (trước là 180 viết cứng trong watchdog): mọi giới hạn của stream phải
ngắn hơn nó và còn dư địa, và mỗi lần thử gọi model đều tính lại mốc tiến triển.
Test: 2 test mới (stream nuốt `CancelledError`, client treo ở create); suite 1141 passed / 3 skipped,
evals 35/35. Trên bản chạy thật, #251 gặp đúng một lần kết nối treo 121 giây → `StreamStalled`,
thử lại, chạy tiếp tới hết (hai dòng 0/0 token rồi body nối tiếp) — không còn cảnh cả task bị hủy.

### C21: nén hai tầng (mô phỏng trước, sửa sau)

C18 cắt một lần cho tới `worker_compact_to_chars` = 20000 — nhưng goal tính trên tổng kết quả tool, mà
**3 kết quả mới nhất** đã 24 000 ký tự (kết quả 5–8k rất phổ biến: 163/364 dòng `task_steps`), nên
sau khi cắt hết mức body vẫn trên ngưỡng: mỗi bước chỉ cắt được cái mới đến → một bước một điểm đứt.

Mô phỏng (`scripts/compact_sim.py`, phân bố độ dài lấy từ `task_steps`, giá thật hit 0,50 /
miss 2,02 $/Mtok, 30 bước/task):

| kết quả mỗi bước | C8 cũ | C18 | hai tầng (C21) |
|---|---|---|---|
| 8000 ký tự | 14,0 lần đứt, $0,4215 | 14,0, $0,4215 | **5,0, $0,3122** |
| 3000 ký tự | 2,0, $0,2382 | 2,0, $0,2382 | **1,0, $0,2056** |
| Phân bố thật | 1,8, $0,2429 | 1,9, $0,2375 | **1,5, $0,2156** |

Tức C18 một mình gần như không đổi; cái ăn tiền là tầng thứ hai: đã cắt 1500 mà vẫn trên goal
thì bản cũ nhất thu còn `worker_tiny_tool_chars` (200) + một dòng. Test: history 13×5000 ký tự →
tổng sau khi nén ≤ goal, và ba bước sau không đổi một chữ.

Đo lại trên bản chạy thật (task #257, cùng hình dạng với #251 — mỗi bước một kết quả ~8k ký tự):
body 65 323 → 34 640 ký tự khi nén (trước C21: 65 567 → 47 897), **3 lần đứt trong 22 bước**
(trước: 5 trong 20), phần trả cho những lần đứt 77 079 token = $0,144, tức 30% tiền của task
(trước: 75k token, 37%). Sàn của tầng hai là `keep × kết quả` = 3 × 8000 = 24 000 ký tự, vẫn
cao hơn goal 20 000 — muốn xuống nữa phải giảm `worker_keep_full_tools`, đổi lại model mất mấy
kết quả gần nhất; chưa làm vì 3 bước gần nhất là thứ model hay dùng nhất. Task cũng chạy hết
22 bước và trả lời, không bị hủy — C20 giữ đúng.

### C22: cắt ở lúc thêm vào, không sửa lại lịch sử

C21 còn 3 điểm đứt mỗi 22 bước, và một bảng quét cho thấy cái núm tôi định vặn không phải là núm ăn tiền:
trong mô phỏng, `worker_keep_full_tools` từ 1 đến 5 cho cùng 1,5 điểm đứt/task ($0,2155 → $0,2196),
vì sàn của tầng hai là `keep × kết quả` nên đổi keep gần như không đổi tổng. Cái quyết định là **điểm đứt**:
mỗi lần sửa một tin đã gửi thì từ tin đó trở đi cả body bị đọc lại (giá miss gấp 4 lần hit).

Vậy thử luật ngược lại: **chỉ cắt tin vừa mới về, không bao giờ sửa tin đã gửi** — body luôn là phần mở rộng
nguyên văn của lần trước, nhà cung cấp phục vụ cả body từ cache, 0 điểm đứt. Mô phỏng (`compact_sim.py`,
22 bước/task, phân bố độ dài thật, giá thật):

| chính sách | điểm đứt/task | token miss | $/task |
|---|---|---|---|
| C21 hai tầng (hiện tại) | 0,9 | 25 520 | $0,1499 |
| C22 cắt 2000 | 0 | 11 387 | **$0,0946** |
| C22 cắt 3000 | 0 | 14 612 | **$0,1180** |
| C22 cắt 4000 | 0 | 17 368 | $0,1381 |
| C22 cắt 6000 | 0 | 21 735 | $0,1699 |

Đã lấy cắt 3000 (`worker_result_chars`), vì đây là chỗ đánh đổi năng lực: model mất phần giữa của kết quả
dài, đổi lại rẻ hơn 21% và mỗi kết quả còn thấy được cả **đuôi** — trước đây cắt 8000 chỉ giữ đầu, nên lỗi
in ở cuối output (traceback) bị cắt mất và model phải chạy lại lệnh. Marker ghi rõ “cắt bao nhiêu ký tự ở giữa,
cần thì gọi lại tool hoặc thu hẹp lệnh”. Tầng hai của C21 vẫn còn làm lưới an toàn cho task rất dài.

Đo trên bản chạy thật: task #261 (6 lần gọi, thao tác máy ảo) và #265 (4 lần gọi, `run_code`), cả hai **không có
lần nào chỉ hit 1152** ngoài lần đầu — body mỗi lần là phần mở rộng của lần trước, `cache_miss` đúng bằng
kết quả mới (527, 1 172, 585 token).

Rõ nhất là task #269 (bảo worker in 60 dòng mỗi bước, kết quả ~9,9k ký tự/bước, 9 lần gọi):
cache_hit = 1 152, 7 424, 9 728, 10 368, 11 008, 11 648, 12 288, 12 928, 13 568 — **mỗi bước đúng +640 token**,
tức đúng phần 3000 ký tự vừa cắt; cache_miss mỗi bước 718–733 token, đúng bằng kết quả mới, không có lần nào
tụt về 1 152. Cả task 9 lần gọi hết $0,0764 và trả lời đúng (đủ 8 bước × 60 dòng). Test `tests/test_result_cap.py`: cắt giữ đầu + đuôi, đếm đúng số ký tự
đã cắt, và tính chất cache (thêm một kết quả đã cắt không đổi một tin nào phía trước).

Một phát hiện phụ khi chạy thật: `run_code` chạy trong sandbox nên **không thấy** `/home/boxes/osa` (chỉ có thư mục
làm việc và hệ thống). Task bảo worker đọc repo sẽ trả lời “file not found” — đúng thiết kế cách ly, nhưng cần
biết khi giao việc cho worker về chính repo này.

### C23: một dòng meta hỏng làm cả đoạn hội thoại câm

11/11 16:54, `logs/osa.log`: “对话 1 出错” bốn lần liền, mỗi lần cùng một chỗ —
`memory.context` đọc `meta.get("state")` mà `meta` là một **chuỗi** (`'str' object has no attribute 'get'`).
Hậu quả: người dùng gửi bốn câu, không câu nào có trả lời; lượt nào cũng chết trước khi gọi model.

Vì sao chuỗi: `meta` lấy từ cột `messages.meta` rồi `json.loads`, mà cột đó không có ràng buộc gì —
một dòng cũ/hand-edit để giá trị JSON không phải object (ví dụ `"chỉ là một chuỗi"`) là đủ.

Sửa: một chỗ duy nhất `memory._meta(raw)` — parse hỏng hay không phải object thì trả `{}`; dùng ở
`context`, `page`, `update_meta`, và chỗ đọc `usage` trong báo cáo chi phí. Test: một dòng meta là chuỗi →
`context` vẫn dựng xong, `page` trả meta object.

### C24: 120 秒的静默上限，先用数去量

7 天内 6 次“模型 120 秒没有输出新内容”（1 次 router、5 次 worker），每次都要 120 秒 + 重来一次的代价。
重来的那次往往十几秒就完事（任务 #90：卡 121,8 秒，重来 17,0 秒），所以卡住的那条流不是“在慢慢想”，
是真的断了——但这件事只看 ms 和 ttft 分不出来：llm_calls 记了整次用时和第一个块的时间，没记中间安静了多久。

所以先量（31e0b1d）：`providers.guard_stream` 把这次流里最长的一段静默填进 `stats["silence"]`
（首块之前的等待，或两块之间最宽的空档），worker 与 router 把它写进 `llm_calls.silence_ms`，
成功、取消、出错都写（出错那次记的就是等满的那个上限）。`scripts/silence_stats.py` 按角色打出分布与最接近上限的几次。
**上限本身这一轮没有动**：等一天的数出来，再由分布决定 120 是放宽还是收紧。

同时量到的一件事（同一批数据，未改代码）：聊天的每一轮第一次调用都是冷的（cache_hit 1152，miss 22–24k，$0,045/轮），
同一轮里第二次调用（1 秒后）整份正文都命中。把两次真实请求的 body 存下来逐字比对：第二次是第一次的**逐字延长**；
再把这两份 body 按顺序重放给服务商，第二份命中 23936 —— 说明 body 没问题，掉的是服务商那边的缓存（几分钟内过期）。
所以“每轮省 $0,035”只能靠把冷的那一份变小：router 的请求里 35% 是 45 个工具的 schema（29,7k 字符 ≈ 8,1k token），
系统提示词 26,6%（其中 86% 是 Bot 自己的指令，19,3k 字符），对话历史 38,3%。
两轮的 system 逐字相同（比过），所以不是“有块每轮都变”，而是冷的那一份本身太大：
下一步是让冷的那份变小（先从 45 个工具 schema 与 Bot 指令的排版下手），而不是再猜缓存。

实测（同一份 body）：同一进程里紧接着重发，第二次就全命中（26496）。跨轮就冷：同一份 body 在线上发出约 2 分钟后
重放仍命中（23936），约 4 分钟后重放是冷的（1152）；这中间我自己还发过别的请求，所以这只是量到的两个点，
不是精确的 TTL。聊天是按人手的节奏一轮一轮来的，指望不上。
**测 cache 时的一个坑**：重放旧 body 证明不了什么——它可能正是线上那次发送留下的缓存。要先发一次新的、再立刻重发同一份。

## Rủi ro & lối thoát

- Sửa prompt (A2) có thể đổi "tính cách" bot → giữ song song 1 turn mẫu trước/sau, so 5 câu trả lời.
- Frame mới trên `/ws` (A3) làm client cũ bỏ qua field lạ → an toàn; nếu vỡ, client kiểm `type` đã có default.
- `_wake_retry` (A1) có thể che lỗi thật: chỉ retry đúng chuỗi `machine_not_running`, mọi lỗi khác ném nguyên.
- Rollback: mỗi vòng một commit riêng; `git revert` là đủ, không đụng dữ liệu người dùng.

## Việc cần operator quyết

1. Duyệt vòng A (A2–A7) — tôi chạy tuần tự, báo sau mỗi mục.
2. Có bật `xvfb` trong lệnh suite mặc định không (thêm 27 test, +5 s)?
3. Telemetry A4 ghi token/$ vào `meta` message: chấp nhận được chứ (dữ liệu chỉ nằm trong DB của bạn)?
