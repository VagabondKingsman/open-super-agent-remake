# OSA-011 live smoke · 07/11/2026 Asia/Saigon (UTC+7)

PARTIAL — kiểm tra ngôn ngữ thành công ở 4 mẫu; không phải phê duyệt merge.
Skill Flow: osa-dev → ai-work-method → vibecode-kit (+ unslop-vi).

## TIP / phạm vi
Approval pt37u: restart 8765 trên PR #13, Experiential free, tối đa 6 lượt. Không sửa source, commit, push, merge; không tác động tailscaled.
AC: build, authenticated SPA/WS, UI vi, chit-chat VI/EN đều trả VI, worker single/heavy trả VI không CJK, đúng một heavy task.

## Runtime
Head f83e3cb486b82a036d54303c6cba437840f49f18. Worktree là checkout trên box cho PR #13. Đường dẫn máy không ghi vào git.
uv wrapper và uvicorn là process của phiên đó. tailscaled giữ nguyên. Số pid không ghi vào git.
uv sync / npm ci / npm run build exit 0; npm audit 0 vulnerabilities, build cảnh báo bundle >500 kB.
HTTP root 303 trước auth, settings 401, login page 200, login POST 303, authenticated root 200; SPA index-EeqJurSD.js. Settings language=vi. WS Origin=Host, authenticated cookie không ghi vào artifact.

## Kết quả quan sát
- vi: PASS, 2.01 giây, CJK=0. Evidence raw/vi.json.
- en: PASS, 2.01 giây, CJK=0. Evidence raw/en.json.
- single: PASS, 29.19 giây, CJK=0. Evidence raw/single.json.
- heavy: PASS, 124 giây, CJK=0. Evidence raw/heavy-final.json.

Single task #75 mode single status done; heavy task #79 mode heavy status done, 3 worker perspectives + reviewer, đúng một task heavy được tạo trong bot kiểm thử. Kết quả final không có 方案 hay CJK. Thuật ngữ kỹ thuật EN còn được giữ; câu văn là VI. Không dùng lời model tự nhận PASS làm bằng chứng kiểm đếm; CJK do harness đếm lại.

## Usage / lỗi / deviations
14 usage rows, 116,236 tokens (cache_hit + cache_miss + output), cost recorded 0; toàn bộ models :free. Heavy task tự ghi 57.942 tokens. Chi tiết raw/usage-final.json.
4 lượt chat; không chạy routine test vì chi phí token thực tế đã vượt mục tiêu xấp xỉ 100k (116.236). Không gọi thêm model sau đó. Guard token ban đầu cộng nhầm cột input thay vì cache_hit+cache_miss; phải sửa harness trước đợt sau. Đây là lệch cap, không giấu thành PASS toàn bộ.
Harness dừng thu WS sớm do regex 402 khớp số offset at=14025, KHÔNG phải quota error. Chỉ quan sát HTTP task đang chạy tới done, không gửi thêm turn, không retry provider. Giữ nguyên raw heavy.json (status running tại thời điểm harness dừng) và bổ sung heavy-final.json; latency final =124 giây theo server, không dùng 60,38 giây partial làm latency final.
Log từ lúc server process của phiên đó start: không thấy Error/Exception/Traceback/402/429/quota. Evidence raw/log-errors.json. Không thấy quota/provider error thực tế.

## NOT_CHECKED
Routine describe/list; rendered browser/mobile screenshot; điện thoại/tailnet end-to-end; CI PR13 ở phiên này; hồi quy unit đầy đủ; provider filter live; QA deep/Retro gate. Không coi HTTP/build là rendered UI PASS.
STATE/BOARD/log repo chưa sửa vì scope cấm code/commit/publish; parent có thể dùng báo cáo này làm handoff CloudAgent sau.

## Rollback (chưa chạy)
Tắt pid uvicorn và pid wrapper của phiên đó. Số pid không ghi vào git.
Khởi động lại từ worktree bản trước trên box: bỏ `DEEPSEEK_API_KEY`, `OSA_VAULT_KEY`, `OSA_WEBHOOK_TOKEN`, `INSTABOX_API_KEY`. `OSA_CONFIG` và `OSA_DATA_DIR` lấy trong thư mục runtime. Đợi port 8765 rảnh. Không đụng tailscaled. Secret chỉ từ env, không ghi ra file.

## Bản trong repo

Tin Tin yêu cầu đưa báo cáo này vào PR #16. Thư mục `raw/` không có trong git. `results.json` là lúc harness dừng: heavy còn `running`, 60,38 giây, `stop` true. `summary.json` ghi heavy PASS 124 giây, CJK 0. Hai script là bản tham chiếu, mật khẩu đọc từ `OSA_PASSWORD`, đường dẫn trong script là máy đã chạy.
