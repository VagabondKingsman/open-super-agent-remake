# Chạy bằng Docker Compose

Image đã có sẵn Node và uv cho server, frontend và ứng dụng (MCP). Bạn không phải cài Python, Node hay tự build frontend.

> Bản này là bản tiếng Việt của remake. Bản upstream tiếng Trung clone `kadaliao/open-super-agent`. Remake dùng repo `VagabondKingsman/open-super-agent-remake`, nhánh làm việc `i18n-vi` (nhánh mặc định `main` trên GitHub đang cũ). Cài không dùng Docker thì xem [cai-dat-may-moi.md](vi/cai-dat-may-moi.md).

## Bắt đầu nhanh

Cần Docker và Compose v2.24 trở lên (Docker Desktop, OrbStack hay Docker Engine trên Linux đều được).

```bash
git clone -b i18n-vi https://github.com/VagabondKingsman/open-super-agent-remake.git open-super-agent && cd open-super-agent
cp .env.example .env     # có thể điền DEEPSEEK_API_KEY luôn, hoặc mở web rồi điền ở Cài đặt → Model
docker compose up -d     # lần đầu phải build image, khoảng 5–10 phút
```

Mở http://127.0.0.1:8765 .

`compose.yaml` mặc định chỉ có server và không mount `docker.sock`, nên Bot không dùng được máy tính local (desktop và trình duyệt trong Docker). Bảng Máy tính sẽ báo "không kết nối được Docker".
Muốn dùng máy tính local thì thêm dòng này vào `.env`, rồi chạy lại `docker compose up -d`:

```bash
COMPOSE_FILE=compose.yaml:compose.computer.yaml
```

`compose.computer.yaml` mount `docker.sock` của máy chủ vào server và build image máy tính local (`osa-computer:1`). Mount `docker.sock` tức là cho server quyền root trên máy chủ, xem mục [Bảo mật](#bảo-mật).
Máy tính không khởi động ngay. Lần đầu Bot cần dùng, OSA mới tạo container `osa-computer`. Để không 15 phút thì nó tự tạm dừng.

| Việc | Lệnh |
|---|---|
| Xem log | `docker compose logs -f osa` |
| Đã sửa `config.yaml` | `docker compose restart osa` |
| Đã sửa `.env` | `docker compose up -d` (`restart` không đọc lại `.env`) |
| Cập nhật bản mới | `git pull && docker compose up -d --build` |
| Dừng | `docker compose down`. Container máy tính không do compose quản lý, muốn dừng thì `docker stop osa-computer` |

## Dữ liệu nằm ở đâu

| Nội dung | Vị trí |
|---|---|
| Database, khóa chính của kho bí mật, khóa đăng nhập, danh sách ứng dụng của máy, thư mục của ứng dụng kiểu thư mục | `data/` trong thư mục dự án, cùng một bản với khi chạy không dùng Docker |
| File và trạng thái đăng nhập trình duyệt trong máy tính (`/data` trong máy tính) | volume `osa-computer-data` |
| Ứng dụng tải bằng npx / uvx | volume `osa_cache`, xóa đi thì chỉ phải tải lại |

Sao lưu: vào Cài đặt → **Sao lưu và chuyển máy** để xuất một file đã mã hóa, hoặc dùng dòng lệnh (mật khẩu sao lưu cũng có thể đặt ở `OSA_BACKUP_PASSPHRASE` trong `.env`):

```bash
docker compose exec osa python -m osa.backup export -o /app/data    # file sao lưu nằm trong data/ của máy chủ, quyền 0600
```

Khôi phục thì tải file lên trên web, server tự khởi động lại (`restart: unless-stopped`). Chi tiết ở [Sao lưu và chuyển máy](configuration.md#备份与迁移).
File sao lưu không chứa file trong máy tính. Muốn gói file trong máy tính thì chạy:

```bash
docker run --rm -v osa-computer-data:/data -v "$PWD":/backup osa-computer:1 tar czf /backup/computer-data.tgz -C /data .
```

Chép thẳng thư mục `data/` cũng được (chạy `docker compose down` trước). `vault.key` và `session.key` trong `data/` là khóa bí mật, cất ở nơi an toàn.

## Đưa lên Internet (HTTPS tự động)

Trỏ tên miền về server, để trống cổng 80 và 443, rồi ghi vào `.env`:

```bash
OSA_PASSWORD=một-mật-khẩu-ngẫu-nhiên-đủ-dài
OSA_DOMAIN=osa.example.com
```

```bash
docker compose --profile https up -d
```

Caddy đi kèm tự xin chứng chỉ, bạn vào https://osa.example.com . Bản thân server vẫn chỉ nghe ở cổng 8765 của máy.

Nếu server đã có Caddy hoặc nginx thì không cần profile này, chỉ cần reverse proxy tên miền về `127.0.0.1:8765`. Cách viết ở [Cấu hình → Triển khai lên server công khai](configuration.md#部署到公网服务器).

## Máy tính dùng Instabox

Server ít RAM, không muốn chạy desktop và trình duyệt trên đó thì cho máy tính dùng máy ảo Instabox:

1. Đặt `INSTABOX_API_KEY` trong `.env` (`computer.backend` để `auto` là sẽ dùng nó, hoặc ghi hẳn `instabox` trong `config.yaml`).
2. Khởi động bằng `compose.yaml` mặc định (không thêm `compose.computer.yaml`). Server không mount `docker.sock` và không build image máy tính local.

## Tùy chọn

Các biến sau trong `.env` chỉ dành cho compose (các biến môi trường khác xem [Cấu hình → Biến môi trường](configuration.md#环境变量)):

| Biến | Mặc định | Dùng để |
|---|---|---|
| `OSA_PORT` | `8765` | Cổng trên máy chủ |
| `OSA_BIND` | `127.0.0.1` | Địa chỉ lắng nghe. Muốn truy cập thẳng trong mạng LAN thì đổi thành `0.0.0.0`, và đặt `OSA_PASSWORD` trước |
| `TZ` | `Asia/Ho_Chi_Minh` | Múi giờ, tác vụ định kỳ tính theo múi này |
| `OSA_DOMAIN` | | Tên miền cho `--profile https` |
| `FORWARDED_ALLOW_IPS` | `*` | Tin IP thật (`X-Forwarded-For`) từ những nguồn nào. Mặc định chỉ máy này kết nối được nên tin tất cả. Khi `OSA_BIND=0.0.0.0` mở thẳng ra ngoài thì đổi thành `127.0.0.1`, nếu không người khác có thể giả IP để né giới hạn đăng nhập |
| `APT_MIRROR`, `NPM_REGISTRY`, `PYPI_INDEX` | | Nguồn phần mềm khi build image, xem bên dưới |

Chú thích trong `.env` phải nằm trên dòng riêng. Chú thích viết sau giá trị có thể bị coi là một phần của giá trị.

Khi `OSA_BIND` không phải `127.0.0.1` (server mở ra ngoài) mà chưa đặt `OSA_PASSWORD`, server từ chối khởi động. Chỉ đặt `OSA_ALLOW_NO_PASSWORD=1` khi bạn thật sự cần chạy như vậy trong mạng nội bộ tin cậy. Chạy thẳng `docker run -p 8765:8765` không qua compose cũng thế: hoặc đặt mật khẩu, hoặc viết `-p 127.0.0.1:8765:8765 -e OSA_BIND=127.0.0.1`.

## Mạng chậm hoặc bị chặn (ví dụ ở Trung Quốc đại lục)

- Không kéo được image từ Docker Hub thì cấu hình mirror cho Docker (`registry-mirrors`).
- Muốn build bằng nguồn phần mềm gần hơn thì ghi vào `.env`, rồi chạy `docker compose build`:

  ```bash
  APT_MIRROR=mirrors.ustc.edu.cn
  NPM_REGISTRY=https://registry.npmmirror.com
  PYPI_INDEX=https://mirrors.ustc.edu.cn/pypi/simple
  ```

  `NPM_REGISTRY` và `PYPI_INDEX` cũng được ghi vào image, nên khi chạy, npx / uvx tải ứng dụng cũng đi qua chúng.
- Dùng Telegram mà mạng chặn thì đặt proxy. Proxy trên máy chủ ghi là `HTTPS_PROXY=http://host.docker.internal:7890`, và proxy phải cho phép kết nối từ LAN (ví dụ "Allow LAN" của Clash).

## Lỗi thường gặp

| Hiện tượng | Nguyên nhân và cách xử lý |
|---|---|
| Bảng Máy tính báo "không kết nối được Docker", hoặc dùng máy tính thì báo `Cannot connect to the Docker daemon` | Chưa thêm `compose.computer.yaml` (xem Bắt đầu nhanh). Hoặc socket của Docker không ở `/var/run/docker.sock` (Docker rootless nằm ở `$XDG_RUNTIME_DIR/docker.sock`): sửa dòng đó trong `compose.computer.yaml` |
| Nâng cấp từ bản cũ xong thì máy tính không dùng được | Trước đây `compose.yaml` có sẵn `docker.sock`, giờ chuyển sang `compose.computer.yaml`. Thêm `COMPOSE_FILE=compose.yaml:compose.computer.yaml` vào `.env` rồi `docker compose up -d` |
| Sửa image máy tính mà không có tác dụng | Container cũ vẫn còn: `docker compose build computer && docker rm -f osa-computer`, lần sau dùng máy tính sẽ tạo theo image mới |
| Image bị build ra amd64, hoặc máy tính khởi động báo sai nền tảng | Môi trường có đặt `DOCKER_DEFAULT_PLATFORM`. `unset` nó rồi build lại |
| Ứng dụng kiểu thư mục cần truy cập thư mục trên máy chủ | Ứng dụng chạy trong container của server, chỉ thấy đường dẫn trong container. Mount thư mục vào ở `volumes` của `compose.yaml` (ví dụ `- ~/Documents:/mnt/docs`), khi thêm ứng dụng thì điền `/mnt/docs` |
| Kết nối Ollama trên máy chủ | Cài đặt → Model → Thêm → Ollama, đổi địa chỉ thành `http://host.docker.internal:11434/v1` |
| Đơn giá trong Cài đặt luôn là "chưa có đơn giá" | Container không kết nối được models.dev: đặt `HTTPS_PROXY` trong `.env`, hoặc ghi đơn giá vào `pricing.models` trong `config.yaml` |

## Bảo mật

- Chỉ khi thêm `compose.computer.yaml` thì mới mount `docker.sock`. Nó cho server tạo và điều khiển container trên máy chủ, tương đương quyền root trên máy chủ. Server chạy ứng dụng (MCP) của bên thứ ba, nên chỉ thêm ứng dụng bạn tin. Không dùng máy tính local thì đừng thêm file này.
- VNC của máy tính không có mật khẩu, nên chỉ nghe ở 127.0.0.1 trong container máy tính, không map ra cổng của máy chủ. Server chuyển tiếp nó lên web qua `docker exec`.
- Các điểm khác xem [SECURITY.md](../SECURITY.md).
