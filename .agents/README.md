# START HERE · Cộng sự OSA

Đây là kênh bàn giao giữa các bot ở tài khoản/máy khác nhau, chỉ dùng GitHub để trao đổi. Không cần bộ nhớ chat của bot trước. Đây là hướng dẫn làm việc, không phải bản sao model, quyền công cụ hay tài khoản đã đăng nhập.

File đọc đầu cho bot mới: [HANDOFF](HANDOFF.md). Repo duy nhất được công bố: **VagabondKingsman/open-super-agent-remake**. Base tích hợp: `i18n-vi`. Đọc [RULES](RULES.md) trước thao tác ghi. Tài liệu không cấp quyền gửi tin, chạy LLM trả phí, push hoặc merge.

## Onboarding khoảng 10 phút

1. Phút 0: đọc [HANDOFF](HANDOFF.md). Đối chiếu head với `git rev-parse` sau fetch. Snapshot trong HANDOFF không phải latest vĩnh viễn.
2. Phút 0–2: đọc [RULES](RULES.md), [PERSONA](PERSONA.md), [PROTOCOL](PROTOCOL.md). Xác nhận repo, quyền và môi trường. Không lấy credential của bot trước.
3. Phút 2–4: đọc [STATE](STATE.md), [BOARD](BOARD.md) và log mới nhất trong [log/](log/), bỏ qua `_TEMPLATE.md`. STATE là snapshot, không thay việc đọc ref/PR hiện tại trên GitHub.
4. Phút 4–7: đọc [SKILL-FLOW](SKILL-FLOW.md), cài/nạp bridge `osa-dev` cùng bảy skill theo hướng dẫn. Không gọi tên skill rồi coi như đã đọc.
5. Phút 7–10: đọc [ARCHITECTURE](ARCHITECTURE.md) và [OPS](OPS.md) nếu sắp chạy box, tra [DECISIONS](DECISIONS.md), chọn một việc chưa có owner. Lập [TIP](templates/TIP.md), kiểm quyền rồi claim theo BOARD.
6. Trước BUILD/VERIFY, mở reference đúng bước. Tra các [templates](templates/) khi cần. Không ép việc nhỏ thành báo cáo dài. `templates/HANDOFF.md` là mẫu một task, khác [HANDOFF](HANDOFF.md) của cả dự án.

Bot mới chưa có repo/quyền dùng [PROMPT](PROMPT.md). Clone phải phù hợp quyền người dùng và chính sách công cụ của tài khoản; ưu tiên CloudAgent cho sửa code khi nền tảng yêu cầu.

## Đầu mỗi phiên

- Ack ngắn với Tin Tin: mục tiêu, Skill Flow, việc kiểm trước; không hỏi lại điều đã rõ.
- Đọc Git status trước. Nếu cây sạch và không đang giữ việc dở, cập nhật nhánh tích hợp:

```bash
git status --short
git switch i18n-vi
git pull --ff-only origin i18n-vi
git rev-parse HEAD
```

- Nếu có thay đổi dở hoặc pull không fast-forward, giữ nguyên chúng, fetch/read remote rồi đối chiếu; không stash/reset/rebase mù quáng. Tạo safety trước reconcile rủi ro. Không ghi đè sửa của bot khác.
- Đọc lại STATE, BOARD, log mới nhất và các PR đang mở. GitHub/ref đã xác minh mới hơn snapshot được ưu tiên về trạng thái thực tế; chênh lệch cần ghi lại.
- Tạo branch `<bot>/<topic>` từ base đã cập nhật, ví dụ `build-bot/worker-live-eval`. Với CloudAgent, yêu cầu agent dùng base/branch tương ứng.
- Claim một task, lập TIP/AC và test plan. Không chạy scheduler/channel/LLM thật để “xem có chạy không”.

## Cuối mỗi phiên và mỗi PR

Cập nhật STATE + BOARD và thêm `log/YYYY-MM-DD-<bot>.md`; nhiều phiên cùng ngày dùng hậu tố hoặc append mục có giờ. Không sửa lịch sử log để che FAIL. Tất cả giờ dùng **Asia/Saigon (UTC+7)**.

Dùng [mẫu log](log/_TEMPLATE.md), [VERIFY REPORT](templates/VERIFY-REPORT.md), [PR](templates/PR.md) và [handoff](templates/HANDOFF.md). Ghi cả phần chưa làm, command/exit/test counts, base/branch/SHA và next step. Log đã commit là bộ nhớ chung; thư mục riêng trên máy không phải kênh liên lạc.

## Nơi lưu thông tin

| Nội dung | Nơi cập nhật |
|---|---|
| Cửa vào, đã làm, việc còn | HANDOFF |
| Cách nói | PERSONA |
| Cách làm với Tin Tin | PROTOCOL, RULES |
| Skill nào, lúc nào | SKILL-FLOW |
| Chạy và kiểm trên box | OPS |
| Cài trên máy mới | `docs/vi/cai-dat-may-moi.md` ở root |
| Hệ thống hiện tại | ARCHITECTURE |
| Snapshot, giới hạn | STATE |
| Owner, tiến độ | BOARD |
| Quyết định có lý do | DECISIONS, thêm ADR mới |
| Diễn biến mỗi phiên | log/ theo phiên |
| Source skill + helpers | `skills-pack/ai-native/` ở root, không nhân bản vào log |

Không dùng BOARD để lưu password, endpoint bí mật hay dữ liệu vận hành. Thay đổi quy tắc/quyền lớn cần Tin Tin duyệt, không tự hợp thức hóa bằng một ADR.
