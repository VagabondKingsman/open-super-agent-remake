# Open Super Agent remake · v0.17.0

[Tiếng Việt](README.md) · [English](README.en.md) · [中文](README.zh.md)

Bản tiếng Việt của [kadaliao/open-super-agent](https://github.com/kadaliao/open-super-agent) v0.17.0 (`ec02547`), chạy trên máy của bạn. Bạn chọn model, nối ứng dụng qua MCP, giao việc nền cho Bot và xem Computer khi Bot làm. Tiền API do nhà cung cấp tính. Dự án không cấp credit.

Repo: <https://github.com/VagabondKingsman/open-super-agent-remake>. Giấy phép [MIT](LICENSE). Tác giả upstream: Kada Liao. Nhánh làm việc: `i18n-vi`, tip `8c108c9` (merge PR #39, 10/11/2026). Nhánh mặc định `main` trên GitHub là bản cũ, đừng dùng.

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

## Sửa sau đợt E2E Computer ngày 10/11/2026

Các mục dưới đây có trong code remake, không có ở upstream. Bằng chứng live nằm trong `.agents/log/`.

- `reasoning_effort` của từng role chỉ nhận rỗng, `low`, `medium`, `high`, `xhigh`, `max`. Giá trị khác bị từ chối với lỗi 400. Khi provider trả 400 cho một mức effort, OSA gọi lại một lần không kèm effort và ghi model đó vào khóa `effort_rejects` trong bảng `settings`. Lần sau OSA không gửi lại mức đó. Nút Thử ở Cài đặt → Mô hình báo mức bị từ chối.
- Router nói đã giao task #N mà lượt đó không gọi `dispatch` và #N không tồn tại thì OSA cho thêm một lượt có tool để giao thật. Lượt đó vẫn không giao thì câu trả lời có thêm dòng đính chính. Tin này mang `fabricated_task_ids` và được đưa lại vào ngữ cảnh như một thông báo hệ thống.
- Reviewer của Heavy không có tool. Câu hỏi gửi reviewer bỏ các dòng yêu cầu `load_skill`, `verify_facts`, Skill Flow. Bản gộp dưới 400 ký tự và ngắn hơn một phần tư bản nháp ngắn nhất (bản nháp từ 200 ký tự) thì OSA hỏi lại một lần. Vẫn ngắn thì OSA trả bản nháp dài nhất, task ở trạng thái `partial`.
- Trong nhóm, Bot có thể đặt `handoff_to` là chính mình khi `dispatch`. Task xong thì Bot đó được gọi lại để tổng hợp. Chuỗi bàn giao theo kết quả task dừng ở `MAX_TURNS` (8) và hiện thông báo.
- Trên Docker và Instabox, `computer_screenshot` có `screen: true` để chụp cả màn hình. Ảnh này chỉ để nhìn. Tọa độ click vẫn theo ảnh trang. Chrome trên máy này không có tham số đó.
- Cửa sổ trình duyệt của task nhỏ hơn 90% kích thước `computer.width` × `computer.height` (mặc định 1280 × 800, không vượt màn hình) thì được phóng lên kích thước đó mỗi lần task dùng cửa sổ. Cửa sổ phóng to hết cỡ hoặc toàn màn hình giữ nguyên. Trên Instabox, ảnh trang trước khi sửa chỉ 500 × 136, sau khi sửa là 1270 × 669.
- `backend: auto` chọn Instabox khi có `INSTABOX_API_KEY` trong vault hoặc môi trường và server không chạy trong app desktop.
- Stream của model im quá `limits.stream_idle_s` giây (mặc định 120, ngắn hơn 3 phút của Watchdog) thì OSA đóng stream và gọi lại cùng lượt, tối đa `limits.stream_retries` lần (mặc định 1). Rớt kết nối, 5xx hay lỗi "at capacity" giữa stream cũng được gọi lại. Lỗi hết quota thì không. Router chỉ gọi lại khi UI chưa nhận chữ nào. Đây là bản sửa cho task Nova #253 bị Watchdog hủy (PR #37).
- CI chạy thật 3 test sandbox (cài `bubblewrap`, `OSA_REQUIRE_SANDBOX=1`) và `test_real_chrome` với Chrome thật dưới `xvfb-run` (PR #38, #39). Chỉ còn `test_real_desktop` bị skip vì cần macOS.

Code `desktop/` và `mobile/` có trong cây vì đi theo upstream. Remake không build và không phát hành hai app này. Workflow đóng gói app Mac của upstream không có trong repo.

## Chạy trên máy

Hướng dẫn đầy đủ, gồm gói hệ thống, Computer, Docker Compose, nâng cấp và lỗi thường gặp, nằm ở [Cài OSA remake trên máy mới](docs/vi/cai-dat-may-moi.md). Bản ngắn:

Cần Python từ 3.11, `uv`, Node khớp Vite trong lockfile (`^20.19.0 || >=22.12.0`), `git`. Linux cần thêm `bubblewrap` cho sandbox chạy code. Computer Docker cần Docker. Không có Docker vẫn dùng UI, API và việc không cần desktop.

```bash
git clone -b i18n-vi https://github.com/VagabondKingsman/open-super-agent-remake.git
cd open-super-agent-remake
test -f .env || cp .env.example .env
uv sync --locked
(cd web && npm ci && npm test && npm run build)
bash scripts/osa-start.sh
```

Mở <http://127.0.0.1:8765>. Thêm model trong Cài đặt. API key chỉ nhập qua form. `TZ=Asia/Ho_Chi_Minh` nếu lịch phải theo giờ Việt Nam. Ngôn ngữ chọn trong UI, lưu trên server. `OSA_LOCALE` của bản cũ không còn tác dụng.

Docker Compose là cách chạy khác: [Docker](docs/docker.md). Clone từ repo remake, không từ upstream. Không chạy hai process trên cùng database.

## Kiểm tra

Chạy giống CI (Linux, cần `bubblewrap`, `xvfb` và Chrome):

```bash
uv run python -m osa.i18n
env -u DISPLAY CI=1 OSA_REQUIRE_SANDBOX=1 OSA_TEST_CHROME=1 xvfb-run -a uv run pytest -q -rs
(cd web && npm ci && npm test && npm run build)
curl --fail http://127.0.0.1:8765/api/settings
```

Trên `8c108c9`, pytest được 828 passed, 1 skipped (`test_real_desktop`, chỉ macOS). CI push trên `8c108c9` (run `42826978455`) xanh backend, frontend và docker. `uv run pytest -q` trơn vẫn chạy được trên máy thiếu sandbox hay màn hình, khi đó test cần chúng sẽ SKIP. Pytest dùng database tạm và model giả. Test đó không chứng minh Docker Computer, app Mac, điện thoại, hay kênh chat thật đã chạy.

## An toàn

Mặc định chỉ nghe localhost. Mở ra mạng thì bật `OSA_PASSWORD` và HTTPS. Đọc [SECURITY.md](SECURITY.md). Không public VNC, CDP, `.env`, vault, database, backup. Gắn `docker.sock` gần như cấp quyền root trên máy host.

## Tài liệu

- [Cài trên máy mới](docs/vi/cai-dat-may-moi.md)
- [Hướng dẫn tiếng Việt](docs/huong-dan-vi.md)
- [Nhận bản upstream](docs/cap-nhat-tu-upstream.md)
- [VI / EN / ZH](docs/i18n.md)
- [Cấu hình](docs/configuration.md), [kênh chat](docs/channels.md), [kiến trúc](docs/architecture.md)
- [Changelog](CHANGELOG.md)

Git chỉ giữ source. Sao lưu database và volume Computer trước khi nâng cấp. Không force-push `i18n-vi`.

Bot mới đọc [.agents/README.md](.agents/README.md). [AGENTS.md](AGENTS.md) là cửa vào ở root.
