# Cập nhật upstream và công bố Open Super Agent remake

Áp dụng cho `/workspace/open-super-agent`, nhánh triển khai `i18n-vi`. Cập nhật 07/11/2026, Asia/Saigon (UTC+7). Đây là hướng dẫn, không tự cấp quyền push hay đổi dữ liệu.

## Đích và giới hạn

- Remake: `VagabondKingsman/open-super-agent-remake` (`origin`).
- Upstream: `kadaliao/open-super-agent` (`upstream`), chỉ đọc/fetch. Không push/PR vào repo tác giả.
- Không force-push, không reset hard/rebase dòng đã công bố. Non-fast-forward là lý do dừng kiểm tra lịch sử, không phải thêm `--force`.
- Không đổi remotes chỉ để vượt lỗi auth. Connector/CloudAgent có quyền không có nghĩa Git CLI trên box có credential; không đọc token/session để tự xác thực.
- Source, database, vault và Computer phải được sao lưu riêng; Git không chứa dữ liệu vận hành.

## Lần chuyển v0.5 → v0.6

Nền cũ `907b9e2` nằm trên `safety/i18n-before-v0.6.0-20261107`. Upstream v0.6.0 là `9790ffafcd07c9a434bf7c5b2ff4b689c28f5c09`.

Merge thẳng tạo khoảng 64 conflict vì hai hệ i18n không tương thích. Lần cập nhật này đã abort merge, tạo `merge/v0.6.0-vi` từ upstream v0.6 rồi port VI theo Chinese-as-key. Không giữ lại conflict-marker tree.

Các thay đổi riêng được mang sang có chọn lọc:

- VI frontend/backend, lựa chọn ba ngôn ngữ, migration preference cũ và gợi ý model trả lời VI.
- Báo `docker_missing` thay vì 500, UI Computer/tệp giải thích và khóa nút không dùng được.
- Validation lịch và reservation webhook trước LLM filter; giữ logic quiet của upstream.
- Script local, tài liệu VI và bộ hồi quy mới. Các pack prompt/schema/catalog i18next cũ không còn được dùng.

Để giữ cả hai dòng local mà không reset, nhánh port nhận lịch sử nhánh cũ bằng merge chiến lược `ours` có chủ đích, giữ nguyên tree v0.6 đã test; sau đó `i18n-vi` fast-forward tới nhánh port. Đây là bước chuyển kiến trúc đã review, không phải mẫu cho mỗi lần nhận upstream. Safety tip không đổi.

## Rủi ro lịch sử remake trên GitHub

Remake ban đầu được công bố bằng snapshot trên lịch sử riêng. Đối chiếu cũ ghi nhận:

| Mốc | SHA |
|---|---|
| Local VI v0.5 | `80191801d29daf42d095bbf329a2f0d2fc1aa24c` |
| Snapshot GitHub VI | `4ad98e0e1bab9280535c4b7febac0efd322ac579` |
| Cùng tree tại thời điểm đó | `72eb43b83bbad342a3b89dd556dfc05fa158e996` |

Đó là mốc lịch sử, không phải lời khẳng định remote hiện vẫn ở SHA đó. Cùng tree không đồng nghĩa cùng ancestor. Local cũng có thể là shallow checkout. Trước công bố phải đọc trạng thái remote và ancestor trên môi trường có quyền, không đoán hoặc force-push.

CloudAgent công bố trên remake cần nhận patch/tree local đã test, áp lên nhánh dựa trên GitHub hiện tại, giữ nội dung remote mới nếu có rồi chạy lại build/test. Nếu commit SHA đổi sau cherry-pick/áp patch, báo cả SHA local và SHA công bố. Không tạo repo/lịch sử khởi tạo mới để upload lại tree, không đẩy vào upstream.

Các artifact local ngoài Git ở `/workspace/osa-ui-shots/` gồm báo cáo v0.6 và patch/bundle bàn giao nếu đã tạo. Chúng không chứa `.env`, database, key hoặc log vận hành. Báo cáo là nơi ghi SHA cuối và kết quả thực tế.

## Chuẩn bị cập nhật lần sau

```bash
cd /workspace/open-super-agent
git status --short
git branch --show-current
git log -5 --oneline --decorate
git rev-parse --is-shallow-repository
```

Giữ thay đổi chưa commit của người khác. Tạo safety branch tên mới và xuất backup ứng dụng với môi trường tin cậy trước khi đổi bản. Đợi tác vụ quan trọng xong, bảo đảm chỉ một instance dùng kênh chat/lịch.

Fetch có kiểm soát, chỉ khi được phép truy cập remote:

```bash
git fetch origin
git fetch upstream
git merge-base HEAD upstream/main
git log --oneline HEAD..upstream/main
git diff --stat HEAD...upstream/main
```

Nếu shallow thì cần đủ lịch sử trước khi kết luận unrelated. Nếu chưa có ancestor rõ ràng với remote remake, dừng và lên phương án áp patch; không dùng `--allow-unrelated-histories` đại trà.

Khi đã cùng lịch sử, tạo nhánh thử từ dòng remake đã xác minh rồi merge upstream để review. Với thay đổi kiến trúc lớn, ưu tiên nền mới + port có chọn lọc như lần v0.6 thay vì chữa conflict bằng cách chọn toàn bộ ours/theirs.

## Port v0.6.1 (07/11/2026)

Lịch sử remake và upstream không có merge-base. Ba commit `0897360`, `ec71362`, `3432671` được áp bằng patch thủ công lên `i18n-vi`, không merge và không lấy commit desktop/Tauri sau đó. Remote `upstream` chỉ fetch; push URL để `DISABLED`.

## Port v0.12.0 (09/11/2026, OSA-021)

Upstream đi từ v0.6.1 lên v0.12.0 trong ba ngày: 84 commit, khoảng 27.000 dòng ở `osa/`, `web/`, `tests/`. Phần riêng của remake chỉ khoảng 5.000 dòng. Vì vậy lần này dựng nền mới rồi port remake lên, giống lần v0.6.0, không áp từng commit upstream.

1. Safety branch tại tip cũ (`safety/i18n-vi-before-v0.12-20261109`).
2. Một commit forward lấy cây v0.12.0 cho `osa/`, `web/` (trừ `web/tests/`), `tests/`, `pyproject.toml`, `uv.lock`, `config.yaml`, `Dockerfile`, `compose.yaml`, `.env.example`, `.dockerignore`, `.gitignore`, `deploy/`, `desktop/`, `mobile/`. Giữ của remake: `.agents/`, `skills-pack/`, `docs/`, `scripts/`, README, `.github/` và file chỉ remake có.
3. Xuất diff remake `3432671..<tip cũ>` cho các file bị ghi đè rồi `git apply -3`. Blob của `3432671` có sẵn trong repo vì đã fetch upstream, nên git tự merge 3 chiều. Lần này 53 file sạch, 23 file xung đột.
4. `osa/router.py`, `osa/worker.py` merge 3 chiều bằng `git merge-file --diff3` (remake làm gốc). Giữ cấu trúc upstream (registry, dsml, botadmin, đo ms/ttft), áp lại hành vi remake (finish_reason, Heavy, quota, IncompleteAnswer, side_effects), viết prompt mới bằng tiếng Anh.
5. Tool riêng của remake đăng ký qua `osa/builtin.py` vào registry, không thêm nhánh `if` trong Router/Worker.
6. Catalog: `en.json` lấy upstream cộng khóa chỉ remake có, `vi.json` dịch khóa mới. `uv run python -m osa.i18n` phải ra thiếu 0, thừa 0.
7. Test upstream chạy với `i18n.set_lang("zh")` trong `tests/conftest.py`; test VI của remake tự đặt ngôn ngữ. Test upstream nào khẳng định câu chữ tiếng Trung gửi cho model thì sửa sang câu tiếng Anh mới, không xóa assertion.

Những chỗ dễ sót lần sau: chi phí USD ở bảng `llm_calls` (cột `estimated`, migration đổi tiền cho cả hai bảng), giá ảnh `pricing.images` theo USD, số lần retry 5xx (`limits.provider_transient_retries` bằng `providers.RETRIES`), tranh chấp webhook nay nằm ở `events.deliver`. Plugin trong `osa/catalog/plugins/` vẫn trả lời model bằng tiếng Trung, chưa có test chặn.

## Điểm phải review

- Router/Worker, approvals, auth và ranh giới dữ liệu không tin cậy.
- `fetch_url` SSRF, local Docker, CDP/VNC và xử lý lúc người dùng tiếp quản.
- Scheduler validation, webhook đồng thời, trạng thái `quiet` và timeout.
- `osa/i18n.py`, `web/src/i18n.ts`, bộ khóa en.json/vi.json; không đưa i18next cũ trở lại.
- Ngôn ngữ server và localStorage, placeholder `{name}`, metadata template/app còn chưa VI.
- Lockfile/dependency, schema DB, cấu hình và đường dẫn. Không sửa checksum lockfile bằng tay.

## Kiểm thử trước triển khai

```bash
uv sync --locked
uv run python -m compileall -q osa
uv run python -m osa.i18n
uv run pytest -q
(cd web && npm ci && npm test && npm run build)
git diff --check
```

Pytest đặt DB tạm, model giả và tắt Computer thật. Import server ngoài pytest có thể mở DB theo cấu hình môi trường; không thử migration hoặc scheduler bằng dữ liệu thật mà chưa có backup. Các lệnh CLI app/template checker có thể chạy bằng cấu hình thử phù hợp.

Build xuất `osa/static/dist/`, không commit bundle. Cài bản mới trên host phải build lại, push source không tự cập nhật UI.

## Restart và smoke

```bash
bash scripts/osa-stop.sh
# Kiểm tra instance cũ đã dừng trước khi start:
bash scripts/osa-start.sh
curl --fail http://127.0.0.1:8765/api/settings
curl --fail http://127.0.0.1:8765/api/files
```

Hard-refresh tab. Kiểm tra locale VI, picker đủ ba ngôn ngữ, `/api/bootstrap`, `/api/status`, `/api/tasks` và Computer với ID Bot thực. Auth bật thì 401 chưa đăng nhập là đúng; không tắt bảo vệ để smoke. Không gửi webhook/tin nhắn, gọi LLM trả phí hoặc tạo routine có tác động ngoài chỉ để thử.

Thiếu Docker phải thấy `unavailable` / `docker_missing`, không 500. API 200 và unit test không chứng minh desktop thật hoạt động. Dừng nếu build/test fail, có crash mới hoặc không xác định được dữ liệu đang dùng.

## Commit và công bố

Stage đúng đường dẫn đã review, không `git add .` mù quáng. Kiểm tra diff staged và tên file; không commit `.env`, key, database, backup, log hay browser profile.

Commit local không đồng nghĩa đã push. Công bố chỉ sau khi có yêu cầu cụ thể và xác định branch/remote. Parent CloudAgent xử lý push remake trong phiên có quyền; executor local không push, không đổi remote.

Sau công bố phải xác nhận ref/SHA remote và báo kết quả kiểm thử trên chính tree được công bố. Không tự cập nhật `main` chỉ vì đã được giao cập nhật `i18n-vi`.

## Quay lại bản ổn định

Giữ nhánh lỗi để điều tra. Tạo nhánh phục hồi từ safety đã kiểm thử, build lại dependency/web và restart có kiểm soát. Không reset hard để xóa công việc hoặc force sửa lịch sử đã công bố. Git rollback không hạ schema database; chỉ restore sau khi chốt tác động tới dữ liệu mới.

Nguồn: [hướng dẫn VI](huong-dan-vi.md), [i18n](i18n.md), [changelog](../CHANGELOG.md), [bảo mật](../SECURITY.md).
