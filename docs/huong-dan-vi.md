# Hướng dẫn tiếng Việt · Open Super Agent remake v0.17.0

Cập nhật 10/11/2026, Asia/Saigon (UTC+7). Nền là upstream v0.17.0 (`ec02547`). Remake `i18n-vi` tại `aa1ab7e`. Giữ tiếng Việt mặc định, khóa dịch tiếng Trung, prompt tiếng Anh, chi phí USD, gói AI Native, và các sửa bảo mật đã merge tới PR #25. Không build app Mac hay iPhone dù code `desktop/` và `mobile/` có trong cây.

- [Repo remake](https://github.com/VagabondKingsman/open-super-agent-remake)
- [Repo tác giả](https://github.com/kadaliao/open-super-agent)
- [Cập nhật và công bố source](cap-nhat-tu-upstream.md), [hướng dẫn dịch](i18n.md)

## Bộ cài và dữ liệu

| Thành phần | Vị trí |
|---|---|
| Checkout trên box | `/workspace/open-super-agent` |
| Nhánh triển khai local | `i18n-vi` |
| Web/API | `http://127.0.0.1:8765` |
| Backend | `osa/server.py`, ứng dụng `osa.server:app` |
| Web source / production | `web/src/` / `osa/static/dist/` |
| Database mặc định | `data/osa.db`; cấu hình khác qua `OSA_CONFIG`. `OSA_DATA_DIR` chuyển DB, khóa, apps, workspace và dữ liệu Computer ra khỏi checkout |
| Log / PID | `logs/osa.log` / `logs/osa.pid`. Khi có `OSA_DATA_DIR`, script start/stop dùng `$OSA_DATA_DIR/logs/` |
| Workspace trong Computer | `/data/workspace`, khác thư mục source trên host |

Git chỉ lưu source. `.env`, `data/`, log, khóa, `.venv/`, node_modules, bundle và backup không được commit. Đổi nhánh không sao lưu hội thoại hay đăng nhập trình duyệt.

`config.yaml` là lớp mặc định; giá trị đã chỉnh qua UI nằm trong database và ghi đè YAML. MCP/triggers legacy chỉ nhập lần đầu. Chỉnh YAML rồi restart không luôn thay giá trị đã lưu từ UI.

## Cài, build và chạy

Cần Python từ 3.11, uv và Node khớp Vite trong lockfile (`^20.19.0 || >=22.12.0`). Không cần Docker để mở UI/API, nhưng Computer local cần Docker daemon và image.

```bash
cd /workspace/open-super-agent
test -f .env || cp .env.example .env
uv sync --locked
(cd web && npm ci && npm test && npm run build)
bash scripts/osa-start.sh
```

Script start nạp `.env` bằng Bash rồi bind `127.0.0.1:8765`. Chỉ nạp file do bạn kiểm soát. Dòng “started” chưa chứng minh API sẵn sàng; kiểm tra UI hoặc GET `/api/settings`. Không in toàn bộ log/response nếu có dữ liệu riêng.

```bash
bash scripts/osa-stop.sh
# Xác nhận instance cũ đã dừng trước khi chạy lại:
bash scripts/osa-start.sh
```

Chờ tác vụ quan trọng hoàn tất trước restart. Không dùng nhiều Uvicorn workers hoặc hai instance chung database/token: scheduler, kết nối chat và reservation nằm trong bộ nhớ tiến trình.

Chạy foreground để xem lỗi:

```bash
# Dừng bản nền trước. Nạp môi trường tin cậy như script start nếu cần.
uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765
```

Chạy trực tiếp bằng uvicorn không tự nạp `.env`. Script start nạp `.env`; khi dùng CLI hoặc foreground, export biến cần thiết từ môi trường tin cậy trước. Không chép khóa vào lệnh lưu lịch sử shell.

| Biến | Công dụng |
|---|---|
| `OSA_CONFIG` | Đường dẫn YAML khác |
| `TZ=Asia/Ho_Chi_Minh` | Giờ Việt Nam cho tiến trình/scheduler |
| `DEEPSEEK_API_KEY` | Provider mặc định, hoặc nhập key qua UI |
| `OSA_PASSWORD` | Bật đăng nhập; phải có trước khi mở public |
| `OSA_ALLOWED_HOSTS` | Khi chưa có mật khẩu, thêm host được phép, cách nhau bởi dấu phẩy. `localhost`, IP, `*.local`, `*.ts.net` đã được nhận |
| `OSA_DATA_DIR` | Thư mục dữ liệu, nên là đường dẫn tuyệt đối ngoài checkout. DB, `session.key`, `vault.key`, apps tự thêm, workspace, dữ liệu Computer nằm ở đây. `memory.db` tương đối chỉ lấy tên file. Đường dẫn tuyệt đối trong YAML giữ nguyên. Log/PID của script start cũng nằm trong `$OSA_DATA_DIR/logs` |
| `OSA_WEBHOOK_TOKEN` | Token cho header `X-OSA-Token` của địa chỉ webhook cũ. Đã đặt `OSA_PASSWORD` thì địa chỉ cũ bắt buộc phải có token |
| `OSA_ALLOW_NO_PASSWORD` | Đặt `1` để vẫn chạy khi nghe ngoài `127.0.0.1` mà chưa có `OSA_PASSWORD`. Mặc định là từ chối khởi động |
| `INSTABOX_API_KEY` | Computer cloud khi dùng backend phù hợp |
| `OSA_VAULT_KEY` | Master key; không tự đổi trên dữ liệu hiện có |
| `OSA_BACKUP_PASSPHRASE` | Mật khẩu backup CLI |
| `HTTPS_PROXY` | Proxy cho dịch vụ/kênh chat khi cần |

`OSA_LOCALE` của v0.5 không còn điều khiển ngôn ngữ. Chọn trong UI. Locale không tự đổi timezone; giờ hiển thị còn phụ thuộc thiết bị xem.

## Đăng nhập và trang web khác

Chưa đặt `OSA_PASSWORD` thì không cần đăng nhập. Chỉ dùng trên máy mình hoặc mạng nội bộ, và đặt mật khẩu trước khi mở ra ngoài.

WebSocket và request ghi, kể cả webhook, bị từ chối khi Origin khác trang này. Trình duyệt gửi Origin của trang đang mở, nên một trang khác không nối được `ws://127.0.0.1:8765/ws` để nhắn Bot hoặc bấm thẻ xác nhận. curl và webhook thật không gửi Origin.

Chưa có mật khẩu thì Host chỉ được là `localhost`, địa chỉ IP, tên kết thúc bằng `.local` hoặc `.ts.net`, hoặc tên trong `server.allowed_hosts` / `OSA_ALLOWED_HOSTS`. Danh sách này chặn DNS rebinding. Tên miền của người khác trỏ về `127.0.0.1`, rồi mượn trình duyệt của bạn để đọc dịch vụ trên máy. Đặt `OSA_PASSWORD` thì mục Host này không còn bị kiểm. Webhook đã có `OSA_WEBHOOK_TOKEN` vẫn bị chặn nếu Origin lạ. Token nằm ở header mà trang khác không gửi được, nên host bên ngoài vẫn gọi được khi biết token.

## Ngôn ngữ

Chọn Tiếng Việt / English / 中文 trong Cài đặt hoặc onboarding. Mặc định khi chưa có lựa chọn là VI. Frontend ưu tiên `osa.lang`; `osa.locale` cũ hợp lệ được chuyển một lần. Server dùng `settings.language`, có chuyển `overrides.locale` cũ một lần; lựa chọn server đã lưu là chuẩn chung cho các thiết bị.

Dịch frontend ở `web/src/locales/vi.json`, backend ở `osa/locales/vi.json`, cùng khóa tiếng Trung với en.json. Placeholder dùng `{name}`, không dùng `{{name}}`. UI dùng `vi-VN` cho ngày/giờ và nhận giọng nói. Xem [i18n](i18n.md).

Nhãn, lỗi và thông báo có bản VI. Mẫu Bot có khối `vi:`. Metadata ứng dụng chưa có bản VI thì hiện bản English. Prompt gửi model là tiếng Anh, có câu yêu cầu trả lời theo ngôn ngữ giao diện. Không viết lại tin nhắn cũ hay trang ngoài.

Giao diện sáng, tối, hoặc theo hệ thống chọn trong Cài đặt. Giá trị nằm ở `localStorage` khóa `osa.theme` trên máy này. Không gửi lên server. Máy khác không theo lựa chọn này.

## Bot, công việc và công cụ

Bot có chat, vai trò và bộ nhớ riêng. Nhóm gồm 2–6 Bot; `@TênBot` gọi đích danh, `@everyone` gọi mọi thành viên. Bot điều phối nhận tin không @. Khi `dispatch` trong nhóm, Bot có thể đặt `handoff_to` là tên mình để được gọi lại lúc task xong. Chuỗi bàn giao theo kết quả task dừng sau 8 lượt (`MAX_TURNS`). Thẻ phê duyệt vẫn nằm trong chat riêng của Bot thực hiện, không ở nhóm.

Worker chạy tác vụ dài ở nền. Heavy cho nhiều Worker làm riêng rồi reviewer tổng hợp, có thể tốn nhiều token hơn. Reviewer không có tool, nên câu hỏi gửi reviewer bỏ các dòng yêu cầu `load_skill`, `verify_facts`, Skill Flow. Bản gộp quá ngắn so với bản nháp thì OSA hỏi lại một lần, vẫn ngắn thì trả bản nháp dài nhất với trạng thái `partial`. Watchdog hủy việc quá hạn/lặp/vượt ngân sách. Bắt đầu chủ đề mới chỉ bỏ ngữ cảnh cũ, không xóa lịch sử hay bộ nhớ dài hạn.

Thêm model ở Cài đặt → Mô hình, chọn riêng cho Router, Worker, reviewer, filter và embedding. Muốn dùng Computer phải chọn model đọc được ảnh và tool calling. Kiểm tra model là API call thật, có thể tính phí. Mức suy nghĩ có thể là mặc định, `low`, `medium`, `high`, `xhigh`, `max`, hoặc tắt. Provider trả 400 cho một mức thì OSA gọi lại không kèm mức đó, nhớ theo model trong `settings.effort_rejects`, và nút Thử báo mức bị từ chối. Ngày 10/11/2026, xAI `grok-4.7` không nhận `max`, `grok-4.20-0309-reasoning` không nhận mức nào. xAI có thể đi qua mục Khác với endpoint tương thích OpenAI; không đồng nghĩa có toàn bộ hosted tools của dịch vụ ngoài.

Đơn giá là USD trên một triệu token, lấy từ models.dev. Không nhân tỷ giá, không đổi sang VND. Không còn trang Chi phí. Đơn giá ở Cài đặt → Mô hình. Số token và USD đã ghi nhận ở trang Quan sát. Model thiếu đơn giá có thể tính 0. Đó không phải cam kết miễn phí. Database cũ được đổi từ CNY sang USD một lần, đánh dấu `settings.cost_unit`.

Ứng dụng là MCP server, khác kênh chat. Dùng quyền tối thiểu. Đọc thẻ xác nhận trước khi gửi, xóa, hoặc trả tiền. Quy tắc “hỏi trước” ưu tiên hơn tự cho phép. Vault mã hóa secret. Không có plugin nhà phát triển từ v0.15.0. Thư mục `data/plugins` cũ không bị xóa và không được nạp.

Kỹ năng `/tên` là hướng dẫn Markdown. Mẫu Bot mang vai trò, kỹ năng và lịch, không mang key/hội thoại/bộ nhớ. Luôn xem trước nội dung trước khi cài/chia sẻ.

## Lịch, webhook và chế độ yên lặng

Lịch thuộc từng Bot: giờ cố định theo ngày/thứ, mỗi N phút (tối thiểu 5), hoặc webhook. Đây không phải cron-expression tổng quát. Chọn đúng timezone, kiểm tra next-run và trạng thái bật trước khi dùng.

Lịch so kết quả với lần trước. Không có gì mới thì lưu trạng thái `quiet`, không đăng kết quả hay push. Bấm chạy thử luôn hiện kết quả. Marker nội bộ `[无新内容]` giữ như upstream. Parser cũng hiểu `nothing new` và `Không có nội dung mới`.

Webhook nhận tại `POST /hooks/<tên>`. Khi đặt `OSA_WEBHOOK_TOKEN`, header `X-OSA-Token` phải khớp. Không đặt token thì: đã bật `OSA_PASSWORD` là từ chối, chưa bật thì chỉ nhận request local trực tiếp. Địa chỉ riêng của sự kiện `/hooks/<khóa ngẫu nhiên>` không cần token. Không dùng webhook gửi tin thật làm smoke mặc định. Bộ lọc keyword chạy trước, LLM filter có thể tính phí. Remake giữ reservation trước khi chờ filter để ngăn dispatch trùng đồng thời trong một runtime, không bảo đảm exactly-once trên hệ thống phân tán.

## Computer và dạy tác vụ

Các Bot dùng chung một Computer. Nhiều tác vụ mở cửa sổ trình duyệt riêng, dùng chung tệp và đăng nhập. Giới hạn mặc định 3 (`computer.parallel`), phần dư xếp hàng. Không phải mỗi Bot một máy.

Panel chọn Docker trên máy này, Chrome trên máy này, hoặc Instabox. `computer.choices` giới hạn danh sách. Khóa Instabox nhập trên panel, được thử rồi mã hóa vào vault. `INSTABOX_API_KEY` trong môi trường vẫn dùng được.

Terminal trên Chrome của máy này là `computer.host_shell`, mặc định tắt. Terminal trên Mac đang cho server mượn là `computer.linked_shell`, cũng mặc định tắt, bật được từ panel của thiết bị khác. Mỗi lệnh phải xác nhận. App Mac cũ không chạy lệnh và báo cần cập nhật. Khóa server không chặn công tắc `linked_shell`. Chế độ demo thì không bật được.

Trên Docker và Instabox, Worker gọi `computer_screenshot` với `screen: true` để chụp cả màn hình. Ảnh đó chỉ để nhìn, tọa độ click vẫn theo ảnh trang. Cửa sổ trình duyệt của task nhỏ hơn 90% `computer.width` × `computer.height` (mặc định 1280 × 800, không vượt màn hình) được phóng lên kích thước đó. Cửa sổ phóng to hết cỡ giữ nguyên.

Bạn xem màn hình, tiếp quản, rồi trả quyền. Bot không phát lại cú bấm hoặc cú gõ đã chờ trước lúc tiếp quản. Dạy thao tác ghi lại việc trong trình duyệt, tối đa 10 phút, thành bản nháp kỹ năng. Không ghi mọi app desktop.

Máy chưa có Docker: Computer và `/api/files` trả `unavailable`, `reason: docker_missing`, có câu giải thích, không trả 500. Nút khởi động bị khóa. HTTP 200 trên `/api/settings` không phải desktop đã chạy.

Không mở VNC/CDP ra public, không chạy `cdp_helper.py` trực tiếp trên host. CAPTCHA, QR, OTP và mật khẩu phải do người dùng xử lý. Không ghi trình diễn với dữ liệu nhạy cảm; bộ che input không bảo đảm phát hiện mọi secret.

## Kênh chat, thư viện và backup

Telegram, Feishu/Lark, DingTalk, WeCom, Discord dùng cùng hội thoại web. Kênh hỗ trợ chat riêng từ tài khoản ghép đôi; nhóm OSA không tự là group/channel thật ở nền tảng ngoài. Chỉ để một instance nhận tin với cùng token. Đọc [channels](channels.md) để cấp quyền đúng.

Thư viện chứa Pages trong database; tệp ở Computer riêng. Embedding giúp tìm theo nghĩa nhưng có thể tính phí. Push/PWA/voice tùy trình duyệt, thường cần HTTPS hoặc localhost. `127.0.0.1` trên điện thoại là điện thoại, không phải máy chạy OSA.

Xuất backup qua Cài đặt → Sao lưu & di chuyển, hoặc CLI cùng môi trường tin cậy:

```bash
uv run python -m osa.backup export -o /workspace/osa-backups
```

Backup chứa secret nên cần mật khẩu riêng. Không chứa đầy đủ Computer/browser login, `.env`, session key hay log. Không thay database khi server đang chạy. Git rollback không hạ schema DB; restore cần chốt tác động tới dữ liệu mới trước.

## Kiểm tra không phát sinh hành động ngoài

```bash
uv run python -m osa.i18n
uv run pytest -q
(cd web && npm test && npm run build)
curl --fail http://127.0.0.1:8765/api/settings
curl --fail http://127.0.0.1:8765/api/files
```

Pytest dùng database tạm, model giả và không cần Computer thật. Lấy ID Bot thực từ bootstrap/UI trước khi GET `/api/bots/<id>/computer`. Nếu bật auth, dùng phiên UI đã đăng nhập; 401 không tự là lỗi và không nên tắt mật khẩu để smoke.

Sau build, tải lại tab cũ. Entry JS đã tách trang, khoảng 69 kB lúc OSA-022. Việc desktop thật, model trả phí, kênh chat và image Computer chưa được chứng minh chỉ bằng unit test hoặc HTTP 200.

Trước mở public cần mật khẩu, HTTPS và review reverse proxy/WebSocket. Đừng công khai log, vault, backup hoặc link chứa dữ liệu riêng. Mount Docker socket có thể cấp quyền tương đương root trên host; chỉ dùng app/code bạn tin cậy. Xem [SECURITY.md](../SECURITY.md).
