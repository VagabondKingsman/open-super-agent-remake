# Open Super Agent remake · v0.17.0

[Tiếng Việt](README.md) · [English](README.en.md) · [中文](README.zh.md)

Bản tiếng Việt của [kadaliao/open-super-agent](https://github.com/kadaliao/open-super-agent) v0.17.0 (`ec02547`), chạy trên máy của bạn. Bạn chọn model, nối ứng dụng qua MCP, giao việc nền cho Bot và xem Computer khi Bot làm. Tiền API do nhà cung cấp tính. Dự án không cấp credit.

Repo: <https://github.com/VagabondKingsman/open-super-agent-remake>. Giấy phép [MIT](LICENSE). Tác giả upstream: Kada Liao. Nhánh làm việc: `i18n-vi`, tip `aa1ab7e` (10/11/2026).

## Bản này giữ gì so với upstream

- Giao diện mặc định tiếng Việt. English và 中文 vẫn chọn được. Khóa dịch là câu tiếng Trung gốc.
- Prompt gửi model viết bằng tiếng Anh và yêu cầu trả lời theo ngôn ngữ giao diện.
- Chi phí ghi và hiện bằng USD. Không còn trang Chi phí. Đơn giá ở Cài đặt → Mô hình. Số đã dùng ở trang Quan sát.
- Gói kỹ năng AI Native cài sẵn cho mọi Bot, tắt được bằng `skills.ai_native_defaults: false`.
- Không có plugin nhà phát triển. Upstream bỏ từ v0.15.0. File cũ trong `data/plugins` không bị xóa và cũng không được nạp.

## Có gì ở v0.17.0

- Computer chọn được: Docker trên máy này, Chrome trên máy này, hoặc máy Instabox. `computer.choices` trong `config.yaml` giới hạn danh sách.
- Khóa Instabox nhập trên panel, được thử rồi mã hóa vào vault. Không ghi vào source.
- Docker chưa cài hoặc không nối được thì panel báo `unavailable` / `docker_missing`. Không báo như desktop đã chạy.
- Tool chỉ đọc đứng cạnh nhau chạy cùng lúc. Lệnh ghi, thao tác Computer và bước cần xác nhận vẫn lần lượt.
- Giao diện theo hệ thống, sáng, hoặc tối. Lựa chọn nằm ở máy này (`localStorage` `osa.theme`), không ghi lên server.
- Mac đang cho server mượn có terminal khi bật `computer.linked_shell`. Mặc định tắt. Mỗi lệnh vẫn phải xác nhận. App Mac cũ không chạy được lệnh và báo cần cập nhật.

Code `desktop/` và `mobile/` có trong cây vì đi theo upstream. Remake không build và không phát hành hai app này. Workflow đóng gói app Mac của upstream không có trong repo.

## Chạy trên máy

Cần Python từ 3.11, `uv`, Node khớp Vite trong lockfile (`^20.19.0 || >=22.12.0`). Computer Docker cần Docker. Không có Docker vẫn dùng UI, API và việc không cần desktop.

```bash
git clone https://github.com/VagabondKingsman/open-super-agent-remake.git
cd open-super-agent-remake
git checkout i18n-vi
test -f .env || cp .env.example .env
uv sync --locked
(cd web && npm ci && npm test && npm run build)
bash scripts/osa-start.sh
```

Mở <http://127.0.0.1:8765>. Thêm model trong Cài đặt. API key chỉ nhập qua form. `TZ=Asia/Ho_Chi_Minh` nếu lịch phải theo giờ Việt Nam. Ngôn ngữ chọn trong UI, lưu trên server. `OSA_LOCALE` của bản cũ không còn tác dụng.

Docker Compose là cách chạy khác: [Docker](docs/docker.md). Clone từ repo remake, không từ upstream. Không chạy hai process trên cùng database.

## Kiểm tra

```bash
uv run python -m osa.i18n
uv run pytest -q
(cd web && npm test && npm run build)
curl --fail http://127.0.0.1:8765/api/settings
```

CI trên `aa1ab7e` (run `42766572535`) đã xanh backend, frontend và docker. Pytest dùng database tạm và model giả. Test đó không chứng minh Docker Computer, app Mac, điện thoại, hay kênh chat thật đã chạy.

## An toàn

Mặc định chỉ nghe localhost. Mở ra mạng thì bật `OSA_PASSWORD` và HTTPS. Đọc [SECURITY.md](SECURITY.md). Không public VNC, CDP, `.env`, vault, database, backup. Gắn `docker.sock` gần như cấp quyền root trên máy host.

## Tài liệu

- [Hướng dẫn tiếng Việt](docs/huong-dan-vi.md)
- [Nhận bản upstream](docs/cap-nhat-tu-upstream.md)
- [VI / EN / ZH](docs/i18n.md)
- [Cấu hình](docs/configuration.md), [kênh chat](docs/channels.md), [kiến trúc](docs/architecture.md)
- [Changelog](CHANGELOG.md)

Git chỉ giữ source. Sao lưu database và volume Computer trước khi nâng cấp. Không force-push `i18n-vi`.

Bot mới đọc [.agents/README.md](.agents/README.md). [AGENTS.md](AGENTS.md) là cửa vào ở root.
