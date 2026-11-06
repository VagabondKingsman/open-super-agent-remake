# Hướng dẫn tiếng Việt — Open Super Agent remake

> Dành cho bộ cài tại `/workspace/open-super-agent`, nhánh `i18n-vi`, nền OSA **0.5.0**. Đối chiếu mã nguồn và báo cáo vá ngày **06/11/2026 — Asia/Saigon (UTC+7)**. Đây là hướng dẫn cho bản remake, không phải cam kết mọi tính năng đã được kiểm thử với dịch vụ thật.

- **Repo riêng:** <https://github.com/VagabondKingsman/open-super-agent-remake>
- **Repo tác giả:** <https://github.com/kadaliao/open-super-agent>
- **Tài liệu cập nhật/build riêng:** [Push code, nhận cập nhật upstream và tự build](cap-nhat-tu-upstream.md).

## Mục lục

1. [OSA là gì, bản remake có gì khác?](#1-osa-là-gì-bản-remake-có-gì-khác)
2. [Bộ cài hiện tại và dữ liệu](#2-bộ-cài-hiện-tại-và-dữ-liệu)
3. [Cài phụ thuộc, build và chạy](#3-cài-phụ-thuộc-build-và-chạy)
4. [Làm quen giao diện](#4-làm-quen-giao-diện)
5. [Mô hình, xAI và chi phí](#5-mô-hình-xai-và-chi-phí)
6. [Ứng dụng MCP, kho khóa và xác nhận](#6-ứng-dụng-mcp-kho-khóa-và-xác-nhận)
7. [Lịch tự động và webhook](#7-lịch-tự-động-và-webhook)
8. [Máy tính, trình duyệt và dạy tác vụ](#8-máy-tính-trình-duyệt-và-dạy-tác-vụ)
9. [Kết nối ứng dụng chat](#9-kết-nối-ứng-dụng-chat)
10. [Bộ nhớ, thư viện và sao lưu](#10-bộ-nhớ-thư-viện-và-sao-lưu)
11. [Tiếng Việt và các bản vá remake](#11-tiếng-việt-và-các-bản-vá-remake)
12. [Kiểm tra, xử lý lỗi và giới hạn](#12-kiểm-tra-xử-lý-lỗi-và-giới-hạn)
13. [Vận hành an toàn và tài liệu gốc](#13-vận-hành-an-toàn-và-tài-liệu-gốc)

## 1. OSA là gì, bản remake có gì khác?

Open Super Agent (OSA) là ứng dụng trợ lý AI tự lưu trữ: một máy chủ FastAPI, giao diện React, dữ liệu SQLite, các Bot có vai trò riêng, tác vụ nền và khả năng kết nối công cụ qua MCP. Bạn tự chọn nhà cung cấp mô hình và tự thanh toán API; cài OSA không đồng nghĩa được cấp sẵn model, credit hay tài khoản dịch vụ.

Ba vai trò chính trong kiến trúc:

- **Router:** nói chuyện với bạn, trả lời nhanh, chọn công cụ hoặc giao việc.
- **Worker:** thực hiện việc nhiều bước ở nền; bạn vẫn tiếp tục trò chuyện. **Heavy** cho nhiều Worker nghiên cứu rồi dùng reviewer tổng hợp, nên có thể tốn nhiều token hơn.
- **Watchdog:** kiểm tra thời gian, tiến độ và ngân sách; hủy tác vụ quá hạn, lặp hoặc vượt giới hạn.

Kết quả công việc, phê duyệt và tiến độ được đẩy về giao diện qua WebSocket. Mỗi Bot có hội thoại và bộ nhớ riêng; một số dữ liệu như thông tin cơ bản về người dùng, thư viện, kết nối và máy tính được dùng chung.

**Bản remake đang dùng** giữ nền upstream và bổ sung:

- Giao diện, prompt hệ thống, lỗi API, schema công cụ, catalog ứng dụng và mẫu Bot có gói **VI/EN/ZH**, mặc định VI và dự phòng EN.
- Thiếu Docker không còn làm danh sách tệp và trạng thái Computer văng lỗi 500: trả trạng thái `unavailable`, hiển thị giải thích tiếng Việt.
- Vá validation lịch sai cấu trúc/ngày và race dispatch webhook đồng thời; cải thiện hiển thị nhãn task cũ mà không viết lại nội dung người dùng.
- Script chạy/dừng local và bộ kiểm thử hồi quy i18n/cron.

Đây vẫn là phần mềm alpha; **dịch nhãn không có nghĩa tính năng bên dưới đã được cung cấp hay được kiểm thử đầu-cuối**. OSA là dự án tự lưu trữ, không tự có toàn bộ hạ tầng của dịch vụ Grok Bot.

## 2. Bộ cài hiện tại và dữ liệu

| Thành phần | Vị trí/ý nghĩa |
|---|---|
| Source local | `/workspace/open-super-agent` |
| Nhánh local | `i18n-vi` |
| Web/API local | `http://127.0.0.1:8765` |
| Backend | `osa/server.py`, ứng dụng `osa.server:app` |
| Web source | `web/src/` |
| Web production | `osa/static/dist/`, tạo bởi Vite, **không đưa vào Git** |
| Cấu hình mặc định | `config.yaml`; đổi đường dẫn qua `OSA_CONFIG` |
| Biến môi trường local | `.env`; script start nạp bằng Bash |
| Dữ liệu mặc định | `data/osa.db`, cấu hình lưu từ UI, dữ liệu Bot/hội thoại/lịch/trang |
| Log/PID local | `logs/osa.log`, `logs/osa.pid` |
| Computer local | Backend Docker; trên máy này chưa có Docker |
| Git `origin` | `https://github.com/VagabondKingsman/open-super-agent-remake.git` |
| Git `upstream` | `https://github.com/kadaliao/open-super-agent.git`, chỉ dùng để đọc/fetch |

**Source và dữ liệu không phải một:** push Git không sao lưu hội thoại, key hay trạng thái đăng nhập trình duyệt. `.env`, `data/`, `logs/`, `.venv/`, `web/node_modules/` và `osa/static/dist/` nằm trong `.gitignore`.

Cấu hình có hai lớp: giá trị gốc trong `config.yaml`, sau đó các thay đổi từ **Cài đặt** lưu trong database sẽ ghi đè. Chỉnh YAML rồi restart không nhất thiết thay đổi giá trị đã được UI ghi đè. Riêng `mcp_servers` và `triggers` cũ chỉ được nhập lần đầu; sau đó quản lý qua UI.

## 3. Cài phụ thuộc, build và chạy

### 3.1. Yêu cầu

- Python **từ 3.11**, `uv`; Node phải khớp engines Vite/plugin-react trong lockfile hiện tại: **`^20.19.0 || >=22.12.0`** (20.19+ trong dòng 20, hoặc từ 22.12). Không dùng Node 20.0 chỉ vì README gốc ghi “Node ≥ 20”.
- Bộ cài được đối chiếu đang có Python 3.13.5, uv 0.13.6, Node 24.22.1, npm 11.21.1; đây là thông tin máy lúc viết, không phải phiên bản bắt buộc cố định.
- Truy cập mạng để tải dependency, gọi model và dùng app bên ngoài.
- **Không cần Docker để mở UI/API và dùng tác vụ không cần desktop.** Muốn Computer local thực sự hoạt động thì cần Docker daemon và image máy tính; hoặc cấu hình Instabox.

Kiểm tra công cụ:

```bash
cd /workspace/open-super-agent
python3 --version
uv --version
node --version
npm --version
```

Không ghi đè `.env` hiện có:

```bash
test -f .env || cp .env.example .env
uv sync
(cd web && npm ci && npm run build)
```

Build chạy `tsc --noEmit` rồi Vite, xuất vào `osa/static/dist/`. `npm run dev` là máy chủ phát triển riêng, **không thay thế build production** mà FastAPI đang phục vụ.

### 3.2. Biến môi trường cần hiểu

Chỉnh `.env` bằng trình soạn thảo; không dán key vào tài liệu/chat/commit. Chỉ thêm hoặc chỉnh những mục cần thiết, tránh khai báo trùng:

```dotenv
OSA_LOCALE=vi
TZ=Asia/Ho_Chi_Minh
```

`Asia/Ho_Chi_Minh` là tên timezone hệ thống tương ứng **Asia/Saigon (UTC+7)**. **Locale không đặt timezone.** Scheduler dùng giờ của tiến trình máy chủ; script start hiện chỉ mặc định `OSA_LOCALE=vi`, không tự đặt `TZ`. Vì vậy cần đặt `TZ` rõ ràng nếu muốn lịch chạy đúng giờ Việt Nam, rồi kiểm tra lại lần chạy kế tiếp. Giờ ngày trên UI còn phụ thuộc timezone của thiết bị xem.

| Biến | Công dụng |
|---|---|
| `OSA_LOCALE` | `vi`, `en` hoặc `zh`; mặc định backend là `vi` |
| `OSA_CONFIG` | Đường dẫn file YAML thay `config.yaml` |
| `DEEPSEEK_API_KEY` | Key cho provider mặc định nếu không nhập qua UI; không bắt buộc dùng DeepSeek |
| `OSA_PASSWORD` | Bật đăng nhập; bắt buộc trước khi cho người khác/mạng công cộng truy cập |
| `OSA_WEBHOOK_TOKEN` | Yêu cầu header `X-OSA-Token` cho webhook |
| `INSTABOX_API_KEY` | Chọn máy tính cloud khi backend là `auto` |
| `OSA_VAULT_KEY` | Master key vault; không tự ý thay trên dữ liệu đã có |
| `OSA_BACKUP_PASSPHRASE` | Mật khẩu cho backup CLI, nếu không nhập tương tác |
| `HTTPS_PROXY` | Proxy khi cần truy cập provider/kênh chat |

Script `source .env` như mã Bash: chỉ nạp file do bạn kiểm soát, viết giá trị hợp lệ với shell, đặt comment trên dòng riêng. `osa/config.py` cũng gọi `load_dotenv` cho `.env` ở root khi chạy trực tiếp/CLI, nhưng không ghi đè biến đã có trong môi trường. Ngược lại, script start dùng Bash source nên giá trị trong file có thể ghi đè biến đã truyền từ shell. Nạp/export rõ ràng trước khi chạy foreground giúp khớp môi trường script, đặc biệt timezone phải có từ lúc tiến trình Python bắt đầu.

### 3.3. Chạy bằng script local — cách thông thường

```bash
cd /workspace/open-super-agent
bash scripts/osa-start.sh
```

Mở <http://127.0.0.1:8765>. Script tạo `logs/` và `data/`, nạp `.env`, dùng `nohup uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765`, lưu PID và log.

**Dòng “started” chỉ cho biết đã tạo tiến trình nền**, không chứng minh API sẵn sàng. Kiểm tra tiếp:

```bash
curl --fail --silent --show-error http://127.0.0.1:8765/api/status
```

Nếu đã bật mật khẩu, kiểm tra bằng trình duyệt sau đăng nhập thay vì kỳ vọng curl chưa xác thực trả 200. Xem `logs/osa.log` bằng trình soạn thảo hoặc `less +F logs/osa.log`; không công khai nguyên log nếu có nội dung nhạy cảm.

Dừng hoặc khởi động lại:

```bash
bash scripts/osa-stop.sh
bash scripts/osa-start.sh
```

Chờ công việc quan trọng xong trước khi dừng; tác vụ đang chạy và chuỗi Bot chờ nhau có thể bị gián đoạn. Script stop dùng PID nếu có; khi mất PID file, nó dùng `pkill -f 'uvicorn osa.server:app'`, có thể khớp cả instance OSA khác trên cùng host. Không dùng cách này để quản lý nhiều bản triển khai độc lập.

### 3.4. Chạy foreground để chẩn đoán

Dừng instance nền trước, không chạy hai server dùng cùng dữ liệu:

```bash
cd /workspace/open-super-agent
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
export OSA_LOCALE="${OSA_LOCALE:-vi}"
export TZ="${TZ:-Asia/Ho_Chi_Minh}"
uv run uvicorn osa.server:app --host 127.0.0.1 --port 8765
```

Dừng foreground bằng `Ctrl+C`. Không thêm nhiều `--workers` để tăng tốc: scheduler, trạng thái webhook đang chạy và kết nối chat của bản này có trạng thái trong bộ nhớ; nhiều tiến trình có nguy cơ chạy lịch/gửi trả lời trùng.

Khi sửa frontend: build lại, restart nếu đồng thời sửa backend, rồi **Ctrl+Shift+R** để tab nạp bundle mới. Không cần xóa database hoặc đăng nhập trình duyệt để “xóa cache”.

### 3.5. Nếu sau này chuyển sang Docker Compose

Đây là phương án triển khai khác, **chưa phải cách máy hiện tại đang chạy**. Cần Docker và Compose từ 2.24 theo tài liệu gốc. Dừng server local trước để tránh trùng port và dùng cùng database hai lần.

```bash
cd /workspace/open-super-agent
docker compose up -d --build
```

Đặt `OSA_LOCALE=vi` và `TZ=Asia/Ho_Chi_Minh` trong `.env`; Compose có mặc định timezone `Asia/Shanghai` nếu không ghi đè. Sau khi sửa `.env`, dùng `docker compose up -d` để tạo lại cấu hình container; `docker compose restart` không nạp giá trị `.env` mới. Xem [hướng dẫn Docker gốc](docker.md) cho HTTPS, volumes và Instabox. Không chạy lệnh xóa volume/container chỉ để thử giao diện.

## 4. Làm quen giao diện

### 4.1. Bot và hội thoại riêng

1. Dùng nút **+ → Tạo Bot** ở sidebar; tạo trống hoặc chọn mẫu.
2. Điền tên, avatar, trách nhiệm và yêu cầu, chẳng hạn “trả lời tiếng Việt, đính kèm nguồn, thao tác ghi phải xin xác nhận”.
3. Chọn Bot để nhắn riêng; gửi yêu cầu rõ kết quả cần đạt, phạm vi và điều không được làm.
4. Theo dõi câu trả lời streaming và thẻ tác vụ. Việc nhiều bước có thể chạy ở nền; xem chi tiết ở panel **Task/tác vụ**.
5. Dùng dừng/hủy đúng tác vụ nếu cần; hủy không hoàn tác thao tác đã thực hiện trên dịch vụ ngoài.

**Chủ đề mới** chỉ ngắt ngữ cảnh hội thoại đang dùng, không xóa ký ức dài hạn hay lịch sử lưu trữ. Xóa Bot là thao tác dữ liệu khác, cần cân nhắc và backup.

### 4.2. Nhóm nhiều Bot

Tạo nhóm từ **2–6 Bot**, chọn Bot điều phối. `@TênBot` gọi đích danh; `@everyone` gọi các thành viên; không @ thì Bot điều phối xử lý và phân việc. Có thể giao kiểu “@Nghiên cứu tìm nguồn; xong chuyển @Biên tập viết báo cáo”.

- Tác vụ trả kết quả về đúng hội thoại đã giao; phần handoff cho Bot tiếp theo chỉ xảy ra khi tác vụ hoàn tất phù hợp.
- **Xác nhận thao tác nằm trong chat riêng của Bot thực hiện**; nhóm hiển thị chỉ dẫn đi xử lý.
- Mỗi lượt tối đa 8 phát biểu, tối đa 50 nhóm theo giới hạn hiện tại.
- Kỹ năng, lịch và bộ nhớ thuộc Bot, không thuộc nhóm; gọi `/kỹ-năng` trong chat riêng, không dựa vào parser kỹ năng trong nhóm.

Không cần nhóm để nhờ Bot khác hỗ trợ: Bot có thể nhắn riêng cho nhau và tự đưa kết quả về nơi ban đầu. Chuỗi này có giới hạn độ sâu 5; trạng thái chờ phản hồi không được khôi phục đầy đủ qua restart.

### 4.3. Panel của Bot

| Panel | Dùng để làm gì |
|---|---|
| Chi tiết | Sửa tên, trách nhiệm; xuất Bot thành template |
| Task/tác vụ | Xem tiến độ, bước công cụ, kết quả và hủy công việc |
| Máy tính | Xem desktop, trạng thái backend, tiếp quản/trả quyền |
| Kỹ năng | Quy trình tái sử dụng, gọi bằng `/tên`; nhập/xuất/chỉnh sửa |
| Lịch / routine | Tạo lịch, tạm dừng, bật lại, chạy thử, xem lịch sử |
| Bộ nhớ | Xem, sửa, xóa hoặc nhập ký ức của Bot |

### 4.4. Mẫu Bot, ứng dụng và thư viện

Bốn mẫu tích hợp có nội dung VI/EN: tin tức (`news`), email (`mail`), theo dõi dự án GitHub (`github-watch`) và chuyến đi (`trip`). **Xem trước toàn bộ** vai trò, kỹ năng, lịch và app cần dùng rồi mới cài; nên chọn tạm dừng lịch trước để kiểm tra cấu hình cá nhân.

Template không chứa hội thoại, ký ức, trang thư viện hay key. Cài mẫu **không tự cấp tài khoản/kết nối app**. Trước khi chia sẻ mẫu đã tùy chỉnh, xóa địa chỉ riêng, tên repo nội bộ và thông tin nhạy cảm khỏi nội dung. Xem [định dạng template gốc](templates.md).

Sidebar **Ứng dụng** là catalog/kết nối MCP; **Thư viện** chứa trang và tệp; **Cài đặt** quản lý model, chi phí, giới hạn, quy tắc xác nhận, Kho khóa, Ứng dụng chat, thông báo, lịch toàn bộ Bot, backup và ngôn ngữ.

## 5. Mô hình, xAI và chi phí

### 5.1. Thêm provider và phân vai trò

Vào **Cài đặt → Mô hình**:

1. Thêm nhà cung cấp có sẵn: DeepSeek, OpenAI, OpenRouter, SiliconFlow, DashScope, Zhipu, Kimi, Ollama; hoặc **Khác** với endpoint tương thích OpenAI.
2. Nhập base URL và API key qua form; bấm kiểm tra kết nối, xem danh sách model tài khoản có quyền dùng.
3. Chọn model cho từng vai trò; có thể tìm hoặc nhập đúng model ID.
4. Bấm thử model. Đây là **API call thật**, có thể tính phí; kiểm tra có nhận hình hay chỉ nhận chữ.

| Role | Công việc |
|---|---|
| `router` | Hội thoại, điều phối và thao tác ngắn |
| `worker` | Thực thi tác vụ nền |
| `reviewer` | Tổng hợp trong Heavy |
| `filter` | Lọc webhook bằng LLM và một số thao tác nhập bộ nhớ |

Mô hình cho Router/Worker cần hỗ trợ tool calling và, khi dùng desktop/screenshots, hỗ trợ ảnh. Không phải provider nào cũng nhận `reasoning_effort` hoặc `thinking`; sau khi chỉnh phải thử lại. Embedding là cấu hình riêng để tìm kiếm ngữ nghĩa; không bật vẫn có tìm kiếm từ khóa.

UI lưu key mã hóa trong vault (dạng tên `LLM_KEY_<provider>`). Key UI được ưu tiên trước biến `api_key_env` trong YAML. Đừng chỉ thêm một biến môi trường rồi nghĩ provider mới sẽ tự xuất hiện: provider vẫn phải được khai báo qua UI hoặc YAML.

### 5.2. Dùng xAI/Grok qua mục Khác

Bản này **chưa có preset xAI riêng**. Đường tích hợp đã có là OpenAI-compatible Chat Completions (`osa/providers.py`, `osa/config.py`), không phải SDK hay toàn bộ bộ công cụ hosted của xAI.

1. Trong **Thêm provider → Khác**, đặt tên dễ nhận biết, ví dụ `xAI`.
2. Base URL: `https://api.x.ai/v1`.
3. Nhập API key của tài khoản xAI trong form bảo mật; chọn model ID từ danh sách/quyền truy cập thực tế, không đoán tên phiên bản.
4. Gán cho role cần dùng và kiểm tra văn bản, tool calling, ảnh tùy nhu cầu. Nên bắt đầu bằng tác vụ nhỏ, không tác động dịch vụ ngoài.

URL đã đối chiếu với [tài liệu Chat Completions chính thức](https://docs.x.ai/developers/model-capabilities/legacy/chat-completions) ngày 06/11/2026 — Asia/Saigon. Tài liệu xAI coi Chat Completions là đường legacy; tính năng chỉ có ở Responses API không tự xuất hiện trong OSA hiện tại. Chưa thực hiện gọi xAI trả phí trong audit này, nên khả năng tương thích từng model vẫn phải kiểm thử.

Có thể khai báo provider YAML với `api_key_env: XAI_API_KEY`, nhưng tên biến đó **không được tự đọc** nếu chưa cấu hình provider tương ứng. Không ghi key thật vào YAML.

### 5.3. Ngân sách không phải hóa đơn

- Trang chi phí theo dõi token/ước tính theo vai trò, ngày và tác vụ; giá tự tải từ models.dev, có thể dùng bản cache hoặc override YAML.
- Cấu hình gốc còn dùng **`¥`**, tỷ giá `pricing.usd_rate: 7.1`; bản Việt hóa **không tự chuyển thành VND**. Chỉ đổi ký hiệu tiền không làm các con số được quy đổi đúng.
- Giá không tìm được có thể tính 0; model nội bộ cũng thường tính 0. Không hiểu 0 là “provider chắc chắn miễn phí”. Đối chiếu hóa đơn nhà cung cấp.
- Giới hạn mặc định YAML: 2.000.000 token/ngày, 30 bước Worker, timeout tác vụ 600 giây, chờ phê duyệt nền 1.800 giây, Watchdog mỗi 15 giây; Heavy 3 Worker. UI có thể đã ghi đè các số này.
- Vào **Giới hạn & ngân sách** để giảm phù hợp trước khi bật lịch/Heavy. Đây là chốt bảo vệ của ứng dụng, không thay thế hạn mức cứng ở provider.

## 6. Ứng dụng MCP, kho khóa và xác nhận

### 6.1. Kết nối công cụ

Ứng dụng MCP mở rộng thao tác như đọc repo, email, ghi chú, tệp và tìm kiếm. Một số app đăng nhập OAuth; một số cần token/password ứng dụng; một số chạy lệnh local qua `npx`/`uvx`; một số là endpoint từ xa. Chỉ kết nối app đáng tin và cấp quyền tối thiểu.

- Mở **Ứng dụng**, tìm app, đọc hướng dẫn và quyền, hoàn tất form/đăng nhập.
- Nhắc `@app` trong yêu cầu để chỉ rõ công cụ cần dùng. App chưa kết nối/đang lỗi không tự hoạt động chỉ vì được nhắc.
- Không có trong catalog: thêm MCP tùy chỉnh bằng URL hoặc command/args/env hợp lệ. Cấu hình thực tế nằm trong database.
- OAuth callback bám theo địa chỉ đang mở UI (`/oauth/callback`); đổi host/domain có thể cần đăng nhập lại. Một số dịch vụ chỉ nhận HTTPS hoặc localhost.
- Catalog cho người dùng bổ sung đặt ở `data/apps/`; catalog source ở `osa/catalog/apps/`. Xem [hướng dẫn app gốc](apps.md).

Email trong catalog gốc có thể dùng IMAP/SMTP và password ứng dụng, không mặc nhiên là OAuth Gmail. Không trao mật khẩu chính cho app không tin cậy.

### 6.2. Kho khóa (vault)

Vault dùng Fernet để mã hóa secret trong SQLite. Master key lấy từ `OSA_VAULT_KEY`; không cấu hình thì tạo `data/vault.key` với quyền 600.

- Nhập secret qua UI tương ứng; tránh đưa vào tin nhắn, prompt, Markdown hoặc source.
- Không mở/in file key để kiểm tra trạng thái; quản lý tên/mục khóa qua UI.
- Mất/thay master key có thể khiến secret cũ không giải mã được. Không xóa `data/vault.key` để “reset lỗi”.
- Bản backup `.osabak` có secret, được bảo vệ bằng mật khẩu backup; giữ file và mật khẩu ở nơi an toàn riêng.

Vault bảo vệ dữ liệu lưu trữ, **không biến kết nối ngoài thành không có rủi ro**: app cần quyền sử dụng credential của nó; model/provider có thể nhận nội dung bạn gửi hoặc dữ liệu công cụ cần xử lý.

### 6.3. Thẻ xác nhận

Thao tác ghi theo chính sách MCP thường yêu cầu **Cho phép một lần / Từ chối / Luôn cho phép**. Có loại thẻ nhờ bạn hỗ trợ đăng nhập, xác minh hoặc tiếp quản desktop.

- Đọc đúng công cụ, đối tượng, tham số và nội dung trước khi cho phép; chỉ “luôn cho phép” với phạm vi bạn hiểu rõ.
- **Cài đặt → quy tắc xác nhận:** khớp tên công cụ đầy đủ, có wildcard như `filesystem__*`. Quy tắc “hỏi trước” được ưu tiên trước tự cho phép.
- Nếu không khớp quy tắc, dùng `confirm` của app (`auto`, `all`, `none` hoặc danh sách từ khóa); `auto` là heuristic, không phải biên bảo mật tuyệt đối.
- Task do lịch/webhook tạo hết thời gian chờ thì bị từ chối; task hội thoại có thể tiếp tục đợi bạn.
- Không chọn `confirm: none` đại trà. Gửi tin, xóa dữ liệu, thanh toán hoặc cấp quyền vẫn cần kiểm tra mục tiêu và hậu quả.

## 7. Lịch tự động và webhook

### 7.1. Tạo và quản lý routine

Lịch thuộc **một Bot**, quản lý ở panel **Lịch / routine**, hoặc yêu cầu bằng lời rồi kiểm tra bản cấu hình được tạo. Ví dụ: “Mỗi ngày 09:00 giờ Việt Nam, tổng hợp tin có nguồn; chỉ lưu báo cáo, không gửi ra ngoài”.

Có ba kiểu trigger:

- **Hằng ngày/theo thứ:** một hoặc nhiều `HH:MM`; thứ 2–CN tương ứng số 1–7; danh sách ngày rỗng là mỗi ngày.
- **Theo khoảng:** ít nhất 5 phút.
- **Webhook:** nhận sự kiện vào tên hook và lọc trước khi giao Worker.

Chọn prompt hoặc kỹ năng cần chạy, kiểm tra app/model/budget, múi giờ và **lần chạy kế tiếp** rồi bật. **Chạy thử là thực thi thật**, có thể gọi model, công cụ hoặc dịch vụ; không bấm thử một lịch gửi email/xóa tệp để kiểm tra nhãn.

Giới hạn hiện tại: tối đa 50 lịch/Bot; lưu 20 lần chạy gần nhất mỗi lịch; lần trước chưa xong thì lượt sau bị bỏ qua. Khi server tắt, lịch không chạy; bật lại chỉ bù một lần thay vì phát lại tất cả thời điểm đã lỡ. Xem trạng thái/kết quả chạy để phân biệt bị lọc, bị bỏ qua, đang chạy, thất bại hoặc hoàn tất.

Lịch không phải tính năng cron-expression tổng quát của Linux. Không mặc định rằng có thể nhập bất kỳ biểu thức `*/5 * * * *` nào. Hãy dùng đúng ba loại trigger hiện có.

### 7.2. Webhook

Endpoint có thật trong source: **`POST /hooks/<tên>`**. Tên phải khớp một routine webhook đang bật. Các bước:

1. Tạo hook ở Bot đúng mục đích; đặt bộ lọc include/exclude và nếu cần câu luật cho role `filter`.
2. Cấu hình `OSA_WEBHOOK_TOKEN`, restart dịch vụ và đặt cùng token ở phía gửi.
3. Keyword filter chạy trước; LLM filter có thể phát sinh phí; sự kiện vượt lọc mới giao Worker.
4. Xem lịch sử chạy của routine thay vì chỉ dựa vào HTTP 200: request được nhận không đồng nghĩa tác vụ đã hoàn tất.

Ví dụ **chỉ chạy sau khi bạn đã tạo hook thử nghiệm an toàn**; thay `audit-demo` bằng tên hook thực, dùng biến môi trường đã nạp thay vì chép token vào câu lệnh:

```bash
curl --fail --silent --show-error \
  -X POST http://127.0.0.1:8765/hooks/audit-demo \
  -H 'Content-Type: application/json' \
  -H "X-OSA-Token: $OSA_WEBHOOK_TOKEN" \
  -d '{"kind":"manual-test","message":"Kiểm tra hook chỉ đọc"}'
```

Không đặt token thì chỉ nhận request local trực tiếp; request qua proxy dù trông như từ localhost vẫn bị coi là bên ngoài. Không bỏ token để khắc phục lỗi 401/403. Không nhầm webhook nhận sự kiện với quyền push vào GitHub.

Bản vá chống dispatch trùng bảo vệ đua đồng thời trong **một runtime**, không phải cam kết exactly-once cho mọi hệ thống phân tán/sự kiện retry. Tránh chạy hai bản OSA dùng cùng Bot/kênh/lịch và không bật nhiều Uvicorn workers tùy tiện.

## 8. Máy tính, trình duyệt và dạy tác vụ

### 8.1. Trạng thái hiện tại: thiếu Docker

Backend `auto` chọn Instabox khi có `INSTABOX_API_KEY`, nếu không dùng Docker local. Máy đang được hướng dẫn **chưa có Docker**, nên panel có thể hiển thị:

- **Không dùng được** (`state: unavailable`).
- **Docker trên máy này**, kèm lý do tiếng Việt.
- Không có desktop/VNC/CDP hoạt động; đây không phải lỗi dịch hay lỗi HTTP 500 cần che đi.

`GET /api/files` và trạng thái Computer vẫn trả phản hồi hợp lệ. Nhưng **upload/download/duyệt tệp của Computer, thao tác browser/terminal và dạy tác vụ** không trở thành dùng được nhờ bản vá graceful fallback. Trang báo cáo lưu trong SQLite và hội thoại không phụ thuộc vào desktop theo cùng cách đó.

Muốn bật Computer thật: cài/cấp quyền Docker daemon rồi build image từ `osa/computer/image`, hoặc đăng ký/cấu hình Instabox phù hợp. Đọc [Docker](docker.md) và [cấu hình Computer](configuration.md) trước; chưa cài Docker/đăng ký dịch vụ/khởi tạo máy cloud trong lượt viết tài liệu.

### 8.2. Khi có backend hoạt động

Trong **OSA**, mọi Bot dùng chung một Computer và trạng thái đăng nhập browser. Task chiếm máy cho đến khi xong/hủy/thất bại; task khác xếp hàng. Heavy không tạo ra một desktop độc lập cho mỗi Worker.

- Dùng panel Máy tính để xem màn hình và **Tiếp quản**, xử lý bước riêng tư, rồi trả quyền cho Bot. Khi người điều khiển, Bot chờ.
- Web ưu tiên thao tác phần tử qua CDP; desktop/screenshot dùng cho phần không phù hợp với trình duyệt.
- CAPTCHA, QR, mật khẩu, OTP phải để người dùng xử lý, không tìm cách vượt xác minh.
- Workspace tệp trong Computer là **`/data/workspace`**, tệp đính kèm dưới `uploads/`; đừng nhầm với source host `/workspace/open-super-agent`.
- Backend local mặc định giữ dữ liệu máy tính ở `data/computers/shared`; khi triển khai Compose dùng volume `osa-computer-data`. Backup ứng dụng không chứa toàn bộ dữ liệu đó.

Không mở public VNC/DevTools. Không chạy trực tiếp `osa/computer/cdp_helper.py` trên host để “thử browser”: helper dành cho Computer, có đường bootstrap có thể restart Chromium. Dùng panel/backend đúng nơi.

### 8.3. Kỹ năng và “Dạy một tác vụ”

Kỹ năng là quy trình Markdown có tên, mô tả và các bước; gọi trong chat riêng bằng `/tên`. Có thể tự viết, nhờ Bot soạn, nhập `SKILL.md` hoặc file/link chia sẻ. **Đọc nội dung trước khi lưu**: kỹ năng là chỉ dẫn cho Bot, có thể chứa yêu cầu gửi dữ liệu hoặc thao tác nguy hiểm.

“Dạy một tác vụ” ghi thao tác **trong trình duyệt**, tối đa 10 phút, rồi dùng model chuyển thành **bản nháp** để duyệt. Không phải ghi mọi ứng dụng trên desktop. Cần Computer đang chạy; hiện chưa kiểm thử đầu-cuối do thiếu Docker.

Password/OTP/card-field được cố gắng che theo loại/tên input, không bảo đảm phát hiện bí mật nhập vào ô văn bản thường. Không thao tác dữ liệu nhạy cảm trong lúc ghi demo; kiểm tra/xóa dữ liệu riêng khỏi bản nháp trước khi xuất/chia sẻ.

## 9. Kết nối ứng dụng chat

**Ứng dụng MCP** là công cụ Bot sử dụng; **Ứng dụng chat** là nơi bạn nhắn với Bot. Hai loại kết nối khác nhau. Bản hiện tại hỗ trợ Telegram, Feishu/Lark, DingTalk, WeCom và Discord; không khẳng định có Zalo hoặc mọi nền tảng khác.

Vào **Cài đặt → Ứng dụng chat**, chọn nền tảng, điền credential trong form, chọn hội thoại OSA cần gắn, kết nối và ghép đôi theo mã. Nguồn credential do bạn tự tạo ở nền tảng tương ứng:

| Nền tảng | Các bước chính |
|---|---|
| Telegram | Tạo bot với BotFather, lấy token, kết nối rồi mở bot/gửi mã ghép đôi; dùng long polling |
| Feishu/Lark | Tạo ứng dụng có Bot; quyền đọc tin nhắn riêng/gửi tin/tệp; điền App ID/Secret; đăng ký sự kiện nhận tin và callback thẻ qua long connection; phát hành app |
| DingTalk | App nội bộ có robot; chọn Stream; cấp quyền gửi tin robot; dùng Client ID/Secret rồi phát hành |
| WeCom | Intelligent bot ở API mode, long connection; điền Bot ID/Secret |
| Discord | Developer Portal tạo application/bot; token; thêm bot vào server bạn tham gia rồi DM và ghép đôi; adapter chỉ dùng DM |

Giới hạn vận hành:

- Nền tảng nhận **tin nhắn riêng** từ tài khoản đã ghép đôi; gắn vào “nhóm” OSA không có nghĩa bot nhận tin trong group/channel thật của Telegram/Discord.
- Web và app chat dùng cùng một hội thoại. Bot trả lời/kết quả lịch được gửi qua kênh; không phải mọi tin bạn gửi từ web hay mọi token streaming đều được mirror.
- Lệnh `/new`, `/stop`, `/help` và `/kỹ-năng` dùng trong hội thoại phù hợp. Thẻ xác nhận có nút hoặc hướng dẫn trả lời theo nền tảng.
- Telegram dùng polling, các adapter còn lại long connection nên không cần địa chỉ public để nhận tin. Tuy vậy link “mở web/tiếp quản” phải trỏ đến URL thiết bị của bạn truy cập được, tốt nhất HTTPS.
- Mã ghép đôi có hiệu lực 30 phút, tối đa 10 lần sai theo bản hiện tại. Token/secret lưu trong vault; không đăng mã/key công khai.
- Chỉ dùng mỗi bot/token ở một nơi: có nền tảng ngắt instance cũ, có nền tảng gửi đến nhiều instance và gây trả lời trùng.
- Gửi tệp/ảnh cần Computer để lưu; voice được adapter hỗ trợ với DingTalk/WeCom, không mặc định Telegram/Discord/Feishu có chuyển âm thanh.
- Tin nhắn đi qua máy chủ của nền tảng; cân nhắc dữ liệu riêng tư.

Tên quyền và các bước theo từng nền tảng trong [tài liệu channels gốc](channels.md). Chưa gửi tin/ghép đôi bằng tài khoản thật trong đợt audit, nên cần kiểm thử có kiểm soát sau khi cấu hình.

## 10. Bộ nhớ, thư viện và sao lưu

### 10.1. Các loại dữ liệu

- **Ngữ cảnh hội thoại:** các tin đang dùng để model trả lời; mặc định giữ 20 tin gần theo YAML, có cơ chế đọc lại phần cũ.
- **Bộ nhớ dài hạn:** nhờ Bot “hãy nhớ…”, hoặc chỉnh trong panel; còn sau khi tạo chủ đề mới. Ghi nhớ riêng của Bot A không mặc định được chia sẻ cho B.
- **Thông tin người dùng chung:** tên, timezone và thông tin cơ bản dùng giữa các Bot; không dùng bộ nhớ này để lưu API key.
- **Thư viện Pages:** báo cáo/trang có thể tìm, ghim, mở và tạo link chia sẻ. Ai có link chia sẻ có thể truy cập theo cơ chế link, không nên coi là quyền truy cập riêng theo tài khoản.
- **Tệp:** nằm trong workspace Computer, không phải database Pages; thiếu Docker thì phần tệp bị hạn chế.

Giới hạn hiện tại theo tài liệu/mã: 200 ký ức riêng/Bot, mỗi mục tối đa 500 ký tự; 50 thông tin người dùng chung; 1.000 trang, tối đa 500.000 ký tự/trang; upload 20 MB/tệp. Lịch sử bước tác vụ mặc định giữ 90 ngày; kết quả trong chat không bị xóa theo thời hạn bước tác vụ đó.

Có tìm kiếm từ khóa sẵn; embedding bổ sung tìm theo nghĩa, có thể tốn phí. Import bộ nhớ dùng model `filter` để tách thông tin, cần duyệt nội dung. Đổi model embedding có thể khiến vector được tính lại.

### 10.2. Sao lưu/khôi phục

Trước nâng cấp hoặc đổi máy, vào **Cài đặt → Sao lưu & di chuyển**, xuất `.osabak` bằng mật khẩu từ 8 ký tự. File chứa Bot, hội thoại, bộ nhớ, kỹ năng, lịch, trang, cấu hình app/model, quy tắc, kênh chat, chi phí **và secret** trong gói mã hóa. Không đưa `.osabak` vào Git.

CLI có thật (chạy từ root, cùng `OSA_CONFIG` và môi trường vault như server):

```bash
uv run python -m osa.backup export -o /workspace/osa-backups
# Khôi phục: thay đường dẫn bằng file đã xuất thật; không chạy chỉ để thử
# uv run python -m osa.backup restore /workspace/osa-backups/<ten-file>.osabak
```

CLI đi qua cấu hình OSA cũng nạp `.env` bằng python-dotenv; vẫn nên dùng đúng môi trường đã export của server như mục chạy foreground, vì giá trị môi trường có sẵn được ưu tiên và script Bash có thứ tự ghi đè khác. Export dùng snapshot SQLite nên không cần tự copy database đang ghi. Backup không bao gồm Computer/browser login, `session.key`, log hoặc toàn bộ `.env`; có kế hoạch riêng cho các phần này.

Khôi phục UI cho xem nội dung trước; xác nhận mới thay database và restart. Bản cũ được lưu tên `data/osa.db.before-restore-<thời điểm>`. Vault được mã hóa lại theo master key của máy mới; kết nối chat khôi phục sẽ tắt trước để tránh hai máy dùng cùng token. **Lịch cũng có thể chạy trùng nếu máy cũ vẫn hoạt động**: dừng/tắt bản cũ trước khi bật bản mới. Đừng tự đổi DB khi server còn chạy.

### 10.3. Điện thoại, giọng nói và thông báo

Có thể mở web trên điện thoại và thêm ra màn hình chính như PWA. Voice input dùng nhận dạng có sẵn của browser, không phải cuộc gọi thoại trực tiếp với Bot; Chrome có thể cần kết nối dịch vụ giọng nói Google, browser không hỗ trợ thì không hiện mic.

Bật thông báo ở **Cài đặt → Thông báo** trên từng thiết bị; push/PWA/voice cần ngữ cảnh an toàn HTTPS hoặc localhost phù hợp. iPhone/iPad cần thêm vào màn hình chính từ Safari rồi bật thông báo (iOS từ 16.4 theo tài liệu gốc). Địa chỉ `127.0.0.1` trên điện thoại là chính điện thoại, không phải máy chạy OSA: phải có URL truy cập riêng an toàn qua HTTPS/VPN.

Push thông báo phê duyệt/kết quả khi không có tab đang được xem, không phải mọi token streaming; nội dung được mã hóa qua dịch vụ push của browser. Không thay đổi `OSA_BIND`/mở public chỉ để có thông báo. Nếu tính năng browser không ổn, kênh chat được cấu hình đúng là một lựa chọn nhận kết quả, với các giới hạn quyền riêng tư ở mục 9.

## 11. Tiếng Việt và các bản vá remake

### 11.1. Chọn ngôn ngữ

Vào **Cài đặt → Giao diện → Ngôn ngữ → Tiếng Việt**. UI lưu `localStorage.osa.locale` và đồng bộ lựa chọn về server/database; lựa chọn đã lưu ở Cài đặt được ưu tiên hơn mặc định `OSA_LOCALE`. Vì vậy đặt biến `vi` nhưng database vẫn chọn `zh` thì phải đổi lại qua UI.

Nguồn dịch:

| Phần | File/thư mục |
|---|---|
| UI | `web/src/locales/{vi,en,zh}/common.json`, `web/src/i18n.ts` |
| Prompt/chuỗi backend | `osa/locales/{vi,en,zh}/__init__.py`, `strings.json`, `osa/i18n.py` |
| Mô tả công cụ | `osa/locales/{vi,en,zh}/tools.json` |
| Catalog/provider | `catalog.json`, `providers.json` trong gói locale |
| Mẫu Bot đầy đủ | `osa/locales/vi/templates/`, `osa/locales/en/templates/`; bản ZH nguồn ở `osa/templates/` |

Hiện fallback VI/EN **không âm thầm trở về ZH**. Một số component dùng chuỗi tiếng Trung làm **khóa dịch**, còn YAML/comment/docs ZH và regex tương thích cũ được giữ nguyên. Có ký tự Hán trong source chưa đủ kết luận UI chưa dịch; phải kiểm tra đường hiển thị và giá trị locale thực.

### 11.2. Đã vá trên bản remake

Tổng hợp từ hai báo cáo local `china-leftover-audit.md` và `deep-fix-summary.md` trong `/workspace/osa-ui-shots/`; các báo cáo là bằng chứng tại máy, không phải file mặc định trong repo GitHub.

| Nhóm | Kết quả đã ghi nhận |
|---|---|
| Backend | Bổ sung 646 khóa VI/EN/ZH; dịch Router/Worker/Heavy, API, vault, backup, OAuth/login, memory, Computer và thông báo kênh chat |
| UI | Sửa 25 hằng nhãn bị giữ bản dịch lúc import; ngày/giờ, nhận giọng nói và dấu phân cách bám locale |
| Template/catalog | Đủ 4 template VI/EN gồm vai trò, kỹ năng, lịch; overlay catalog/category/schema trước khi hiển thị/đưa model |
| Cron validation | JSON trigger sai kiểu/ngày sai được báo lỗi thay vì 500 hoặc bị hiểu thành chạy mọi ngày |
| Webhook concurrency | Reservation trước lúc chờ LLM filter để ngăn dispatch đồng thời trùng; dọn reservation khi runtime khởi tạo lỗi |
| Lịch và task | `describe`, `goal_for`, nhãn `[Lịch …]` tiếng Việt; reader hiểu wrapper VI/EN/ZH và chuyển chrome legacy được nhận diện |
| Docker thiếu | `/api/files` và Computer API phản hồi bình thường với `unavailable`; panel dùng nhãn VI, hiển thị detail và không gợi khởi động khi backend thiếu |
| Mục nhỏ khác | Dấu phân cách tiêu đề nhóm, nhãn kết nối chat và prompt thử model được chỉnh phù hợp locale |
| Web/PWA | Manifest/offline VI; index `Cache-Control: no-cache`; thiếu dist thì trang yêu cầu build đã dịch, không quay về UI legacy Trung |

Báo cáo audit ghi **17/17 kiểm thử hồi quy PASS**, compile Python, typecheck/build web PASS và smoke HTTP các endpoint chính 200; template preview sạch nhãn Hán, trigger hỏng 400, ID không có 404 với thông báo VI. Đây là **kết quả đợt audit đã ghi nhận**, không phải khẳng định vừa chạy lại mọi luồng khi viết tài liệu.

### 11.3. Những gì không tự dịch/không thay đổi

- Tin nhắn AI đã lưu, nội dung người dùng, website/app bên ngoài không bị dịch hoặc ghi đè hàng loạt.
- Chỉ prompt/filter mặc định upstream khớp chính xác mới được chuyển ở lớp đọc; yêu cầu người dùng tự chỉnh vẫn được giữ nguyên.
- Prompt VI hướng dẫn model trả lời VI, nhưng model/dịch vụ ngoài vẫn có thể trả khác; đó không luôn là lỗi UI.
- Docs/comment/source ZH, alias cũ, regex nhận diện password/OTP và bộ locale ZH còn tồn tại có chủ ý.
- Bản vá Docker là xử lý thiếu dependency, **không phải đã cài Docker hay hoàn tất desktop**.

## 12. Kiểm tra, xử lý lỗi và giới hạn

### 12.1. Smoke không tạo dữ liệu

Sau build/restart, xem UI và các GET đã có trong source:

```bash
curl --fail --silent --show-error http://127.0.0.1:8765/api/settings
curl --fail --silent --show-error http://127.0.0.1:8765/api/templates
curl --fail --silent --show-error http://127.0.0.1:8765/api/files
```

Có thể xem `/api/bootstrap`, `/api/tasks`, `/api/status` qua phiên đã đăng nhập. Với Computer/routine, lấy **ID Bot thực** từ UI/bootstrap rồi dùng `/api/bots/<id>/computer` và `/api/bots/<id>/routines`; không giả định luôn có Bot số 1. Không chia sẻ nguyên response chứa hội thoại/dữ liệu cá nhân.

Kỳ vọng: locale `vi`; template VI; không 500; khi thiếu Docker, file/Computer báo chưa dùng được. API 200 chỉ chứng minh phản hồi trạng thái, không chứng minh desktop hoạt động.

Kiểm thử source dùng script có sẵn `scripts/osa-i18n-audit.py`; xem [checklist cập nhật](cap-nhat-tu-upstream.md) để chạy cùng build trong môi trường dữ liệu thử, không dùng webhook/tin nhắn thật làm smoke mặc định.

### 12.2. Lỗi thường gặp

| Hiện tượng | Kiểm tra/xử lý |
|---|---|
| UI vẫn có nhãn cũ sau vá | Build `web`, kiểm tra server đúng port/root, Ctrl+Shift+R, chọn VI trong Cài đặt; không xóa DB |
| Trang yêu cầu build frontend | Chạy `(cd web && npm ci && npm run build)` từ repo đúng; xác nhận có `osa/static/dist/` |
| Đã `OSA_LOCALE=vi` vẫn ZH | UI/database có locale override; đổi Cài đặt → Ngôn ngữ và tải lại |
| Computer “Không dùng được” | Thiếu Docker/daemon hoặc Instabox chưa cấu hình; không phải đã có desktop chỉ vì API 200 |
| Tệp/ảnh không upload | Cần Computer; kiểm tra backend và giới hạn 20 MB, quyền app chat, reverse proxy |
| Model không trả lời | Provider/key/model ID, credit/rate limit, mạng/proxy, role được gán, log; thử model có thể tốn phí |
| Model không nhận ảnh/tool | Chọn model có khả năng tương ứng; text test thành công không đủ cho Computer |
| Lịch chạy lệch giờ | `TZ` tiến trình và timezone thiết bị; đặt Asia/Ho_Chi_Minh, restart, kiểm tra next-run; locale/bộ nhớ timezone không tự đổi scheduler |
| Lịch không chạy | Server tắt, routine pause, task trước chưa xong, ngân sách, filter hoặc đang đợi xác nhận |
| Webhook 401/403/404 | Token/header sai, request qua proxy khi chưa token, hook không có hoặc đang tắt |
| Bot chat trả lời trùng | Hai instance dùng cùng token/lịch hoặc nhiều workers; dừng bản thừa có kiểm soát |
| Port 8765 đã dùng | Đừng start instance thứ hai; kiểm tra PID/log và đúng dịch vụ trước khi dừng |
| Sửa YAML không hiệu lực | UI/database ghi đè; MCP/triggers chỉ import lần đầu |
| Giá vẫn `¥`/0 | Cấu hình giá chưa đổi/không có dữ liệu; không đồng nghĩa VND/miễn phí |
| Push bị non-fast-forward | Dừng, không force; local và GitHub có thể khác lịch sử. Xem hướng dẫn Git riêng |

### 12.3. Phần còn hạn chế

Chưa kiểm thử desktop/VNC/CDP thật vì thiếu Docker; chưa gọi LLM trả phí hay gửi tin kênh thật trong audit; không có kiểm thử trực quan ảnh UI cho lượt audit cuối. Bundle khoảng 1,29 MB có cảnh báo chunk trên 500 kB nhưng build vẫn thành công. Mở tab từ trước build cần tải lại một lần.

Bản này không có hệ thống nhiều người dùng/phân quyền độc lập. Tất cả Bot của OSA chia sẻ Computer và các browser login; app/MCP có thể có quyền rộng. Chỉ dùng trong phạm vi bạn kiểm soát.

## 13. Vận hành an toàn và tài liệu gốc

### Checklist trước khi giao việc tự động

- [ ] Model đúng role, đã thử khả năng cần thiết và có ngân sách.
- [ ] Trách nhiệm/kỹ năng/lịch được đọc lại; không chứa key hay yêu cầu gửi/xóa tùy tiện.
- [ ] Timezone Asia/Saigon (UTC+7), lần chạy kế tiếp hợp lý.
- [ ] Chỉ một instance nhận sự kiện/kênh chat; không bật lịch giống nhau trên máy cũ.
- [ ] App có quyền tối thiểu, confirm/rule đúng phạm vi.
- [ ] Có backup ứng dụng, kế hoạch riêng cho Computer và thông tin môi trường.

Script hiện bind localhost. **Không mở `0.0.0.0`/public trước khi bật `OSA_PASSWORD`, HTTPS và kiểm tra reverse proxy/WebSocket.** Tailscale/HTTPS nội bộ là lựa chọn truy cập từ thiết bị riêng; giữ mật khẩu khi có người khác truy cập. Các link chia sẻ trang/kỹ năng/template là đường công khai theo token, cần thu hồi khi không dùng.

Không expose VNC/CDP, không công khai vault/log/backup. Mount Docker socket có thể tương đương quyền root trên host; cân nhắc kỹ với MCP bên thứ ba. Restore hoặc xóa dữ liệu phải làm có kiểm soát, không xem như thao tác sửa giao diện thông thường.

Tài liệu đối chiếu, phần lớn là tiếng Trung trừ README tiếng Anh:

- [README tiếng Anh](../README.en.md), [README gốc](../README.md), [Changelog](../CHANGELOG.md).
- [Cấu hình](configuration.md): overrides, model, chi phí, vault, limits, backup và truy cập từ xa.
- [Kênh chat](channels.md): quyền và thiết lập từng nền tảng.
- [Docker](docker.md): Compose, Computer, volume, HTTPS, Instabox.
- [Kiến trúc](architecture.md): Router/Worker/Watchdog, groups, DM, dữ liệu và Computer chung.
- [Phát triển](development.md): dev/build/test; lưu ý dữ liệu thật và máy tính chung.
- [Ứng dụng](apps.md), [Template](templates.md), [i18n](i18n.md), [Bảo mật](../SECURITY.md).

Khi upstream thay đổi, tài liệu gốc có thể mô tả bản khác với remake. Luôn đối chiếu source/lockfile thực tế, chạy hồi quy và bổ sung bản dịch trước khi coi việc cập nhật là hoàn tất.
