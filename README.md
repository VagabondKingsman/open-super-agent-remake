# Open Super Agent remake · v0.6.0

[Tiếng Việt](README.md) · [English](README.en.md) · [中文](README.zh.md)

Bản Việt hóa của [kadaliao/open-super-agent](https://github.com/kadaliao/open-super-agent), chạy trên máy chủ của bạn. Tự chọn model, kết nối ứng dụng qua MCP, giao tác vụ nền cho Bot và xem Computer khi Bot làm việc. API model tính phí theo nhà cung cấp; dự án không cấp sẵn credit.

Repo remake: <https://github.com/VagabondKingsman/open-super-agent-remake>. Giấy phép [MIT](LICENSE), tác giả upstream Kada Liao.

## Cộng sự và bàn giao giữa các bot

Bot mới bắt đầu tại [.agents/README.md](.agents/README.md); [AGENTS.md](AGENTS.md) là entry point ở root. Thư mục có phong cách làm việc, Skill Flow, quy tắc, kiến trúc, STATE/BOARD, log phiên và templates. [Prompt khởi động](.agents/PROMPT.md) dành cho tài khoản/máy mới; không chia sẻ credential hay tự cấp quyền phát hành.

## Thay đổi trong v0.6.0

- Nhiều tác vụ dùng Computer đồng thời, mỗi tác vụ có cửa sổ trình duyệt riêng. Các Bot vẫn dùng chung máy, tệp và phiên đăng nhập. Số tác vụ vượt giới hạn sẽ xếp hàng.
- Lịch tự động không có nội dung mới thì không gửi tin hay push. Bấm chạy thử vẫn hiển thị kết quả.
- `fetch_url` chặn localhost và mạng nội bộ để giảm rủi ro SSRF. Nội dung từ công cụ và webhook nằm trong ranh giới dữ liệu không tin cậy, không được coi là chỉ dẫn hệ thống.
- Bot không phát lại thao tác bấm/nhập đã chờ từ trước khi bạn tiếp quản Computer. Router cũng cải thiện cấu trúc prompt để tận dụng cache.
- Giao diện có Tiếng Việt / English / 中文. Mặc định Tiếng Việt, dùng hệ khóa tiếng Trung của upstream, không ghép lại kiến trúc i18next cũ.
- Giữ bản vá remake khi thiếu Docker, kiểm tra cấu trúc lịch và ngăn webhook đồng thời giao tác vụ trùng trong một runtime.

## Các chức năng chính

Bot có tên, vai trò, bộ nhớ và chat riêng; nhóm có 2–6 Bot để phân công và bàn giao. Worker xử lý việc dài ở nền; Heavy cho nhiều Worker làm rồi tổng hợp. Watchdog theo dõi thời gian và ngân sách.

Kho ứng dụng hỗ trợ MCP, kỹ năng `/tên`, dạy thao tác trình duyệt thành bản nháp kỹ năng, mẫu Bot, thư viện trang/tệp, lịch và webhook. Có kết nối Telegram, Feishu/Lark, DingTalk, WeCom, Discord; PWA, nhập giọng nói và thông báo đẩy tùy trình duyệt. Thao tác ghi có thẻ xác nhận; khóa lưu mã hóa trong vault.

## Build và chạy local

Cần Python từ 3.11, `uv`, Node phù hợp với Vite trong lockfile (`^20.19.0 || >=22.12.0`). Computer local cần Docker; không có Docker vẫn dùng được UI/API và công việc không cần desktop.

```bash
git clone https://github.com/VagabondKingsman/open-super-agent-remake.git
cd open-super-agent-remake
test -f .env || cp .env.example .env
uv sync
(cd web && npm ci && npm test && npm run build)
bash scripts/osa-start.sh
```

Mở <http://127.0.0.1:8765>. Thêm model trong Cài đặt; API Key chỉ nhập qua form, không ghi vào source. Đặt `TZ=Asia/Ho_Chi_Minh` trong môi trường nếu cần lịch theo giờ Việt Nam. Ngôn ngữ chọn trong UI lưu ở server; `OSA_LOCALE` của bản cũ không còn điều khiển ngôn ngữ.

Docker Compose là cách triển khai khác: xem [Docker](docs/docker.md). Không chạy hai instance dùng chung dữ liệu/kết nối Bot.

## Kiểm tra trước khi dùng

```bash
uv run python -m osa.i18n
uv run pytest -q
(cd web && npm test && npm run build)
curl --fail http://127.0.0.1:8765/api/settings
```

Tiếng Việt bao phủ nhãn UI, thông báo và lỗi API. Nội dung ứng dụng/mẫu Bot chưa có bản VI sẽ dùng bản English upstream. Prompt nội bộ vẫn theo upstream tiếng Trung và có hướng dẫn trả lời tiếng Việt; tin nhắn cũ và nội dung bên ngoài không bị viết lại.

Chưa có Docker thì Computer trả `unavailable` / `docker_missing`, không phải desktop đã hoạt động. Kiểm thử dùng model giả, không chứng minh các dịch vụ thật đã kết nối.

## An toàn và tài liệu

Mặc định chỉ bind localhost. Trước khi mở mạng công cộng, bật `OSA_PASSWORD` và HTTPS; đọc [SECURITY.md](SECURITY.md). Không công khai VNC/CDP, `.env`, vault, database hoặc backup. Giới hạn SSRF và ranh giới dữ liệu không thay thế việc kiểm tra quyền công cụ và thẻ xác nhận.

- [Hướng dẫn tiếng Việt](docs/huong-dan-vi.md)
- [Nhận cập nhật upstream, build và công bố remake](docs/cap-nhat-tu-upstream.md)
- [Kiến trúc dịch VI/EN/ZH](docs/i18n.md)
- [Changelog upstream](CHANGELOG.md), [kiến trúc](docs/architecture.md), [cấu hình](docs/configuration.md), [kênh chat](docs/channels.md)

Git chỉ giữ source. Sao lưu dữ liệu ứng dụng và Computer riêng trước khi nâng cấp. Lịch sử remake trên GitHub có thể khác dòng local; không force-push để chữa non-fast-forward.
