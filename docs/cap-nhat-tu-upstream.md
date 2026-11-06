# Push lên remake, cập nhật upstream và tự build OSA

> Áp dụng cho `/workspace/open-super-agent`, nhánh sử dụng `i18n-vi`. Đối chiếu trạng thái ngày **06/11/2026 — Asia/Saigon (UTC+7)**. Các lệnh là hướng dẫn để người vận hành thực hiện có kiểm soát; việc thêm tài liệu này không tự fetch/merge/push hoặc đổi server.

Tài liệu sử dụng đầy đủ: [Hướng dẫn tiếng Việt](huong-dan-vi.md).

## 1. Nguyên tắc: nhận tính năng mới nhưng không bỏ bản vá riêng

```text
kadaliao/open-super-agent                 (upstream: nguồn tham khảo, chỉ kéo)
              │ fetch + merge trên nhánh thử
              ▼
nhánh riêng: i18n, hardening, sửa lỗi       (kiểm thử + build + smoke)
              │ push rõ đích origin
              ▼
VagabondKingsman/open-super-agent-remake   (origin: repo do bạn quản lý)
```

- **`origin`** = `https://github.com/VagabondKingsman/open-super-agent-remake.git`.
- **`upstream`** = `https://github.com/kadaliao/open-super-agent.git`.
- Chỉ push đến `origin`; không push hoặc tự mở PR lên repo tác giả. Fetch, diff và merge local **không sửa repo gốc**.
- Repo remake được tạo độc lập, không phải GitHub fork có sẵn quan hệ tổ tiên. Remote đúng tên chưa đủ để bảo đảm merge/push lần đầu hoạt động.
- Merge cố giữ thay đổi hai bên, nhưng không thể hứa “không ảnh hưởng” nếu chưa review conflict và test. Kể cả không có conflict văn bản, hành vi vẫn có thể hỏng.
- Ưu tiên **merge trên nhánh thử**, không rebase lịch sử đã push, không force-push, không `reset --hard`/`git clean` để dọn lỗi.
- Git lưu source. Backup database/vault/Computer là việc khác; xem [hướng dẫn vận hành](huong-dan-vi.md).

## 2. Điểm đặc biệt của bộ cài hiện tại — cần xử lý một lần

### 2.1. Hai commit có cùng nội dung nhưng khác lịch sử

Khi đối chiếu lần viết tài liệu:

| Đối tượng | Commit/đặc điểm |
|---|---|
| Local `i18n-vi` trước commit tài liệu | `80191801d29daf42d095bbf329a2f0d2fc1aa24c` |
| Parent local | `3afd5a9682768bd86003cfd2f4d9323f2eb70f4d`, nền upstream v0.5.0 |
| GitHub remake `i18n-vi` đã công bố | `4ad98e0e1bab9280535c4b7febac0efd322ac579` |
| Parent của commit GitHub | `3803988e5a86e18595f465b74b54ba562a8bf4a4`, commit khởi tạo độc lập, không có parent |
| Tree của cả local `8019180` và GitHub `4ad98e0` | `72eb43b83bbad342a3b89dd556dfc05fa158e996` |
| Checkout local | Shallow (`git rev-parse --is-shallow-repository` trả `true` lúc đối chiếu) |

**Hệ quả:** source đã đưa lên GitHub đúng tree, nhưng commit GitHub là snapshot trên lịch sử mới, không phải chính commit local. Sau khi viết thêm local, `git push origin i18n-vi` có thể bị **non-fast-forward**; từ checkout GitHub, `git merge upstream/main` có thể báo **unrelated histories**.

Không chữa bằng force-push. Không xem việc hai tree giống nhau là hai nhánh tự có chung tổ tiên. Các SHA ở bảng là mốc kiểm chứng, không phải HEAD cố định cho mọi lần cập nhật sau này.

### 2.2. Chọn đúng trường hợp

- **Local còn trên dòng `8019180`:** giữ branch an toàn; đưa các commit mới tự viết (ví dụ docs) sang nhánh bắt đầu từ `origin/i18n-vi` bằng cherry-pick có chọn lọc. Không cherry-pick lại toàn bộ commit i18n nếu tree đã có đủ bản vá.
- **Làm việc trên dòng GitHub `4ad98e0`:** cần thiết lập quan hệ với đúng nền upstream đã tích hợp, rồi mới dùng merge thông thường cho các bản mới.
- **Đã sửa quan hệ lịch sử trước đó:** kiểm tra `git merge-base`/ancestor; bỏ qua bước cầu nối nếu nền đã là tổ tiên.

Bước cầu nối ở mục 5 **chưa được chạy khi viết tài liệu**. Cần review và thực hiện riêng, không lẫn với một lần “push docs” thông thường.

## 3. Chuẩn bị và backup trước mọi lần thay đổi

### 3.1. Kiểm tra phạm vi

```bash
cd /workspace/open-super-agent
git status --short
git branch --show-current
git log -5 --oneline --decorate
git remote -v
git rev-parse --is-shallow-repository
```

Đọc thay đổi chưa commit; không ghi đè hoặc gộp công việc của người khác. Nếu chỉ commit bộ docs này, stage đúng file:

```bash
git add docs/huong-dan-vi.md docs/cap-nhat-tu-upstream.md docs/i18n.md
git diff --cached --check
git diff --cached --stat
git commit -m "docs: hướng dẫn tiếng Việt và cập nhật upstream"
```

Nếu Git yêu cầu danh tính, cấu hình name/email Git của bạn theo chính sách riêng; không bịa người ký, không tự đổi cấu hình toàn cục. Chưa commit được thì giữ patch và xử lý danh tính/quyền truy cập trước.

Với code khác, stage từng đường dẫn đã review, không `git add .` một cách mù quáng. Đặc biệt không đưa `.env`, database, key, log, file backup và browser profile vào commit. `.gitignore` không loại trừ tệp nhạy cảm đã được track từ trước.

### 3.2. Giữ mốc source và backup dữ liệu

Tạo branch an toàn có tên chưa tồn tại (đổi ngày/hậu tố mỗi lần):

```bash
git branch safety/i18n-before-update-20261106 HEAD
```

Nhánh này chỉ giữ source. Xuất backup ứng dụng qua UI hoặc CLI với cùng môi trường như server:

```bash
# Nạp môi trường tin cậy trước nếu server đang lấy cấu hình/key từ .env
uv run python -m osa.backup export -o /workspace/osa-backups
```

Xác nhận file xuất đã có, lưu mật khẩu riêng. Không copy SQLite đang ghi bằng lệnh copy thông thường để thay cho snapshot backup. Backup Computer/browser login, file cấu hình môi trường và custom dữ liệu ngoài ứng dụng theo kế hoạch riêng; `.osabak` không chứa tất cả chúng.

Chờ task quan trọng kết thúc; tạm dừng lịch/kết nối có tác động bên ngoài nếu cần. Không bật bản test cùng database hoặc cùng token với production. Chỉ chạy một instance phục vụ dữ liệu hiện tại.

## 4. Xác minh remotes và đồng bộ tham chiếu

### 4.1. Nếu remotes đã đúng thì không sửa lại

```bash
git remote get-url origin
git remote get-url upstream
```

Nếu thiếu remote, thêm đúng một lần; nếu đã có nhưng sai, dùng `set-url` sau khi kiểm tra:

```bash
# Chỉ dùng lệnh tương ứng với trạng thái thực, không chạy cả add và set-url mù quáng.
# git remote add origin https://github.com/VagabondKingsman/open-super-agent-remake.git
# git remote set-url origin https://github.com/VagabondKingsman/open-super-agent-remake.git
# git remote add upstream https://github.com/kadaliao/open-super-agent.git
# git remote set-url upstream https://github.com/kadaliao/open-super-agent.git
```

Bảo vệ bổ sung tùy chọn trong clone này:

```bash
git config remote.pushDefault origin
git remote set-url --push upstream DISABLED
```

Push URL `DISABLED` làm push nhầm upstream thất bại, fetch URL không đổi. Đây là cấu hình Git local, không phải bảo vệ ở GitHub và không tự truyền sang máy khác. Tại lúc đối chiếu, upstream vẫn có push URL mặc định trỏ repo tác giả; **“chỉ đọc” hiện là quy ước vận hành nếu chưa đặt chốt này**. Luôn chỉ rõ `origin` trong lệnh push dù có cấu hình mặc định.

### 4.2. Fetch trước, không pull mù quáng

```bash
git fetch origin --prune
git fetch upstream --prune
git remote show upstream
```

Repo hiện dùng `upstream/main`; kiểm tra lại branch mặc định nếu tác giả đổi tên. `fetch` chỉ tải commit/tham chiếu, không áp chúng lên source đang chạy.

Nếu local vẫn shallow, tải đủ lịch sử **trước khi kết luận không có tổ tiên chung**:

```bash
# Chỉ chạy khi --is-shallow-repository vẫn là true.
git fetch --unshallow upstream
```

Đây là cập nhật checkout hiện có, không yêu cầu tạo clone khác. Sau fetch, xem graph/diff và thử:

```bash
git log --graph --oneline --decorate --all -30
git merge-base HEAD origin/i18n-vi
git merge-base origin/i18n-vi upstream/main
```

Không có merge-base sau khi đủ lịch sử, cùng dữ kiện mục 2, xác nhận cần xử lý lịch sử. Nếu có ancestor nhưng các nhánh phân kỳ bình thường thì review/cherry-pick/merge trên nhánh thử, không dùng cờ unrelated-history như thuốc chữa mọi lỗi.

### 4.3. Tách kết nối GitHub với Git CLI

Quyền connector/CloudAgent không có nghĩa lệnh `git push` trên box đã có phương thức xác thực. Nếu CLI báo lỗi auth/quyền repo, dừng push và dùng đường kết nối được hỗ trợ/CloudAgent của trợ lý điều phối. Không chép token vào URL remote, không đọc credential/browser session để tự xác thực, không dùng API ghi từng file nhằm né lỗi quyền.

## 5. Một lần: đưa dòng local về dòng đã công bố và nối nền upstream

### 5.1. Giữ các commit local mới, không viết lại nhánh GitHub

Sau khi commit công việc và có branch an toàn, tạo nhánh mới từ dòng GitHub:

```bash
git switch -c work/vi-docs-published origin/i18n-vi
# Chỉ thay DOCS_SHA bằng SHA thật của commit docs vừa tạo trên dòng local.
# git cherry-pick DOCS_SHA
```

Nếu có nhiều commit riêng chưa công bố, review từng commit và cherry-pick theo thứ tự cần thiết. Không cherry-pick commit nền `8019180` lên snapshot `4ad98e0` chỉ để làm SHA “giống nhau”: nội dung i18n đã có sẵn. Nếu local còn thay đổi khác so với snapshot, đối chiếu kỹ và đưa phần còn thiếu sang bằng commit riêng.

Giữ branch local cũ làm bằng chứng; không force di chuyển `i18n-vi` sang remote. Nếu nhờ trợ lý dùng CloudAgent, hãy yêu cầu áp đúng patch docs lên branch dựa trên `origin/i18n-vi` thay vì đẩy lại toàn bộ source.

### 5.2. Cầu nối lịch sử với **đúng baseline đã có trong remake**

Với snapshot hiện tại, nền upstream đã tích hợp là:

```text
3afd5a9682768bd86003cfd2f4d9323f2eb70f4d  (v0.5.0)
```

Một cách không sửa tree/không viết lại lịch sử là tạo merge commit chiến lược **`ours`** với **chính baseline đó**. Đây là bước nâng cao có chủ đích: khai báo baseline đã nằm trong snapshot; không lấy file từ baseline và không phủ nhận các thay đổi upstream mới hơn.

**Chỉ thực hiện khi đã xác minh:**

1. Commit baseline đúng upstream v0.5.0, không phải HEAD upstream mới tải về.
2. Snapshot công bố có cùng tree với local đã vá (bảng mục 2); local `8019180` có parent là baseline này. Review diff baseline → snapshot để chắc đây là nền + các bản vá riêng, không phải bản thiếu tính năng tùy ý.
3. Nhánh làm việc dựa trên `origin/i18n-vi`, worktree sạch, các commit riêng mới đã chuyển đầy đủ.
4. Baseline chưa là tổ tiên của nhánh; nếu đã là tổ tiên, **không làm lại**.

Có thể kiểm chứng các mốc đã biết sau fetch (nếu một object local không còn, dùng bằng chứng tree/diff và dừng để review, không đoán):

```bash
git show --no-patch --format='%H %P %s' 3afd5a9682768bd86003cfd2f4d9323f2eb70f4d
git rev-parse '4ad98e0e1bab9280535c4b7febac0efd322ac579^{tree}'
git rev-parse '80191801d29daf42d095bbf329a2f0d2fc1aa24c^{tree}'
git diff --exit-code 80191801d29daf42d095bbf329a2f0d2fc1aa24c 4ad98e0e1bab9280535c4b7febac0efd322ac579
git diff --stat 3afd5a9682768bd86003cfd2f4d9323f2eb70f4d 4ad98e0e1bab9280535c4b7febac0efd322ac579
```

Sau review, tạo cầu nối **trên nhánh thử**, không chạy trực tiếp để sửa nhánh đang phục vụ:

```bash
# Đang ở nhánh dựa trên origin/i18n-vi, đã mang theo các commit riêng cần giữ.
git switch -c sync/ancestry-baseline-20261106
BASE=3afd5a9682768bd86003cfd2f4d9323f2eb70f4d
BEFORE_TREE=$(git rev-parse 'HEAD^{tree}')
git merge --no-ff --allow-unrelated-histories -s ours "$BASE" \
  -m "chore: connect verified upstream v0.5.0 baseline ancestry"
test "$BEFORE_TREE" = "$(git rev-parse 'HEAD^{tree}')"
git merge-base --is-ancestor "$BASE" HEAD
```

Hai kiểm tra cuối phải thành công: nội dung không đổi và baseline trở thành tổ tiên. Review merge commit, chạy kiểm thử trước khi công bố.

**Cảnh báo quan trọng:** không thay `$BASE` bằng `upstream/main` mới nhất trong lệnh `-s ours`. Làm vậy sẽ đánh dấu các tính năng mới là đã tích hợp trong khi thực ra bỏ qua toàn bộ chúng. Không dùng chiến lược này cho các lần cập nhật thường kỳ. Nếu không chứng minh được baseline, dừng và nhờ người duy trì lập phương án chuyển lịch sử; không dùng `--allow-unrelated-histories` đại trà hoặc force-push.

Sau khi cầu nối được kiểm thử/công bố lên remake, các lần sau mới dùng quy trình merge thông thường dưới đây. Không tạo PR/push lên upstream để thực hiện cầu nối; toàn bộ thay đổi ở dòng remake.

## 6. Các lần cập nhật tiếp theo từ upstream

Chỉ dùng khi lịch sử đã có chung baseline. Với lần đầu đang ở nhánh cầu nối, tiếp tục trên nhánh đó; các lần sau tạo nhánh mới từ remake đã đồng bộ:

```bash
cd /workspace/open-super-agent
git status --short
git fetch origin --prune
git fetch upstream --prune
# Đổi hậu tố ngày/tên nếu nhánh đã tồn tại.
git switch -c sync/upstream-20261106 origin/i18n-vi
git merge-base HEAD upstream/main
git log --oneline HEAD..upstream/main
git diff --stat HEAD...upstream/main
```

Những commit riêng chưa có ở remote phải được giữ trên branch an toàn và đưa vào nhánh thử trước khi test; không bỏ chúng chỉ vì tạo nhánh từ origin. Đọc changelog/diff, chú ý cấu hình, schema database, model API, auth, scheduler, MCP, dependency và build output.

Merge theo cách cho phép review trước khi commit:

```bash
git merge --no-ff --no-commit upstream/main
```

- **Already up to date:** không có bản upstream mới để nhập; không tạo merge commit rỗng.
- **Merge sạch:** vẫn review `git diff --cached`, test và build; không coi “không conflict” là “không bug”.
- **Có conflict:** giải theo mục 7. Nếu muốn bỏ lần merge chưa công bố, kiểm tra `git status` rồi `git merge --abort` để quay về trạng thái trước merge; thay đổi giải conflict trong lần merge đó sẽ bị bỏ.

Sau khi giải xong và kiểm thử thành công, stage đúng file, xem `git diff --cached --check`, rồi:

```bash
git commit -m "merge: cập nhật upstream và giữ bản vá tiếng Việt"
```

Không rebase dòng công bố chỉ để graph ngắn; không lấy toàn bộ file phía upstream hoặc phía remake để bỏ qua việc hiểu conflict.

## 7. Giải conflict, nhất là i18n và cron

Liệt kê file chưa giải:

```bash
git status
git diff --name-only --diff-filter=U
```

Mở từng file bằng editor, hiểu thay đổi hai phía, bỏ marker `<<<<<<<`, `=======`, `>>>>>>>` sau khi ghép logic đúng. Không đổi/xóa khóa dữ liệu legacy chỉ vì thấy chữ Hán.

| Vùng dễ conflict | Cách giữ đúng |
|---|---|
| `osa/router.py`, `worker.py`, `server.py` | Nhận logic/tính năng mới của upstream; giữ gọi helper i18n thay vì đưa chuỗi Trung hardcode trở lại |
| `osa/routines.py` | Giữ validation trigger/ngày, reservation trước LLM filter, cleanup khi runtime lỗi và `goal_for` đã dịch; kiểm thử đồng thời, không chỉ xem label |
| `osa/i18n.py`, `osa/settings.py` | Giữ locale runtime + override lưu DB, fallback EN; không quay lại fallback ZH ngầm |
| `osa/locales/*/__init__.py`, `strings.json` | Thêm khóa mới vào VI/EN/ZH, giữ placeholder đúng tên/số và định dạng; không đổi ID tùy tiện |
| `web/src/components/*` | Đưa nhãn mới vào i18n, nhãn phải cập nhật khi locale đổi; không giữ bản dịch ở hằng import-time |
| `web/src/locales/*/common.json` | Đồng bộ khóa và `{{placeholder}}`; tiếng Trung có thể là khóa cũ, không phải giá trị VI |
| `tools.json`, `catalog.json`, `providers.json` | Overlay đủ mô tả/schema/title mới; tránh model hoặc người dùng nhận ZH do thiếu key |
| Template YAML/source và locale template | Nhận nội dung tính năng mới, dịch đủ tên/vai trò/kỹ năng/lịch; liên kết tên kỹ năng trong routine phải còn hợp lệ |
| `osa/computer/local.py`, UI Computer | Giữ graceful `unavailable`/detail khi thiếu Docker; không đổi API 200 thành crash 500 |
| `package-lock.json`, `uv.lock` | Giải theo dependency thực, dùng package manager phù hợp; không sửa tay số checksum hoặc bỏ lockfile |
| `config.yaml`, scripts, Compose | Bảo toàn localhost, locale, timezone, auth, đường dẫn dữ liệu và chính sách chỉ một instance |

Ví dụ nguyên tắc: upstream thêm một lỗi/nhãn mới thì tích hợp logic mới, đặt khóa dịch và cung cấp VI/EN/ZH; **không** chỉ chọn “ours” cả file khiến mất tính năng, cũng không chọn “theirs” cả file khiến mất hardening.

Stage từng file đã giải, ví dụ:

```bash
# Chỉ stage các file thực sự đã sửa/review.
# git add osa/routines.py osa/locales/vi/strings.json osa/locales/en/strings.json osa/locales/zh/strings.json
git diff --name-only --diff-filter=U
git diff --cached --check
```

Danh sách chưa giải phải rỗng; JSON/YAML/TypeScript/Python phải parse/build được. Kiểm thử i18n mới quan trọng hơn một phép tìm toàn repo ký tự Hán: docs/comment, locale ZH và matcher tương thích cũ được giữ có chủ ý.

## 8. Kiểm thử và build trước khi áp vào bot đang chạy

### 8.1. Phụ thuộc và kiểm tra tĩnh

```bash
uv sync --locked
uv run python -m compileall -q osa
(cd web && npm ci && npm run build)
git diff --check
```

`uv sync --locked` sẽ từ chối nếu manifest/lock không đồng bộ: sửa đúng dependency và review lockfile, không bỏ qua bằng cách nâng toàn bộ gói tùy tiện. `npm run build` chạy typecheck rồi Vite; production xuất vào **`osa/static/dist`**, được `.gitignore` bỏ qua. Build này cần chạy lại trên máy triển khai sau mỗi checkout thay đổi frontend; push source không tự thay bundle đang phục vụ.

Nếu không muốn build tác động bundle của instance đang chạy, hãy dừng trong cửa sổ bảo trì hoặc kiểm thử source trong môi trường cách ly trước; không chạy hai server production dùng cùng dữ liệu.

### 8.2. Hồi quy i18n/cron trên database thử

Script đã có: `scripts/osa-i18n-audit.py` (đợt audit ghi 17/17 PASS). Nó dùng mock cho dispatch/concurrency, không phải phép gửi webhook/tin chat thật. Các module import vẫn khởi tạo database, nên nên chỉ định DB tạm thay vì dùng dữ liệu production:

```bash
TEST_DIR=$(mktemp -d /tmp/osa-audit.XXXXXX)
uv run python - "$TEST_DIR" <<'PYTEST'
import sys
from pathlib import Path
import yaml
root = Path(sys.argv[1])
cfg = yaml.safe_load(Path('config.yaml').read_text(encoding='utf-8'))
cfg.setdefault('memory', {})['db'] = str(root / 'osa.db')
cfg['triggers'] = []
cfg['mcp_servers'] = {}
cfg.setdefault('computer', {})['enabled'] = False
(root / 'config.yaml').write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding='utf-8')
PYTEST
OSA_CONFIG="$TEST_DIR/config.yaml" OSA_LOCALE=vi \
  uv run python scripts/osa-i18n-audit.py
OSA_CONFIG="$TEST_DIR/config.yaml" OSA_LOCALE=vi \
  uv run python -m osa.catalog
OSA_CONFIG="$TEST_DIR/config.yaml" OSA_LOCALE=vi \
  uv run python -m osa.templates
```

Không chạy server/scheduler thật với cấu hình thử này. Đổi DB không tự cách ly mọi đường dẫn dữ liệu, browser/Computer hay credential môi trường; đừng dùng nó để thử thao tác có tác động ngoài. Không đưa DB thử/log/artifact vào Git.

Kỳ vọng test bảo vệ:

- Gói dịch, placeholder, tool schema và template/skill links đúng.
- Nhãn hệ thống/goal lịch VI; wrapper cũ VI/EN/ZH còn đọc được.
- Trigger JSON sai kiểu/ngày sai bị validation; tính next-run đúng.
- Webhook đồng thời không dispatch hai lần trong một runtime; lỗi khởi tạo không kẹt reservation.
- Login/OAuth, lệnh/thẻ kênh chat và helper độc lập có thông báo đã dịch.

**Không chạy `osa/computer/cdp_helper.py` trực tiếp trên host** để kiểm tra desktop. Script hồi quy hiện chỉ gửi op không hợp lệ, phải bị từ chối trước bootstrap. Muốn kiểm thử desktop thực cần backend Docker/Instabox riêng và dữ liệu thử; phần này chưa được xác minh đầu-cuối trên máy thiếu Docker.

## 9. Restart bản local và smoke sau build

Nạp đúng `.env`, đặt `OSA_LOCALE=vi` và `TZ=Asia/Ho_Chi_Minh` nếu muốn giờ Việt Nam. UI locale đã lưu trong DB có thể ưu tiên hơn biến môi trường; kiểm tra **Cài đặt → Ngôn ngữ**. Không thay key vault khi cập nhật code.

```bash
cd /workspace/open-super-agent
bash scripts/osa-stop.sh
# Đợi instance cũ tắt hoàn toàn, kiểm tra log/port, rồi:
bash scripts/osa-start.sh
```

Script stop không có supervisor/wait-readiness đầy đủ; khi thiếu PID file còn dùng `pkill` khớp tên OSA. Đảm bảo không nhầm instance khác; nếu server còn giữ port thì chưa start bản thứ hai. Script start báo PID trước khi biết API healthy; xem `logs/osa.log` và thử HTTP.

### Checklist nghiệm thu

- [ ] Mở `http://127.0.0.1:8765`, hard-refresh một lần; không có lỗi JS/blank page/build-required.
- [ ] Locale VI thực sự được lưu; sidebar/settings/template/routine/Computer không kẹt nhãn ZH cũ.
- [ ] `GET /api/settings`, `/api/bootstrap`, `/api/templates`, `/api/files`, `/api/tasks`, `/api/status` phản hồi phù hợp; khi bật auth kiểm tra qua phiên đã đăng nhập.
- [ ] Lấy ID Bot thực rồi kiểm tra `/api/bots/<id>/computer` và `/api/bots/<id>/routines`; không giả định Bot 1 tồn tại.
- [ ] Chưa có Docker: Computer/file state `unavailable`, lời giải thích VI, **không 500**; không đánh dấu desktop test PASS chỉ vì API 200.
- [ ] Kiểm tra next-run theo Asia/Saigon (UTC+7), lịch đang bật/tạm dừng đúng; không bật trùng trên máy cũ/test.
- [ ] Bộ test i18n/cron PASS; không tạo routine/gửi webhook thật chỉ để thử validation.
- [ ] Nếu cần kiểm tra chat/model, dùng một yêu cầu nhỏ đã được chấp thuận; lưu ý phí và không giao việc gửi/xóa/mua hàng.
- [ ] Kiểm tra group/DM/approval trên dữ liệu giả khi thay phần tương ứng; phê duyệt nhóm nằm ở chat riêng Bot.
- [ ] Theo dõi log và chi phí sau restart; các kênh chat nhận tin một nơi, không trả lời trùng.

Smoke GET mẫu nếu chưa bật auth:

```bash
curl --fail --silent --show-error http://127.0.0.1:8765/api/settings
curl --fail --silent --show-error http://127.0.0.1:8765/api/templates
curl --fail --silent --show-error http://127.0.0.1:8765/api/files
```

API 401 khi bật auth không tự là bug; đăng nhập bằng UI, không tắt mật khẩu để smoke. Không công khai nguyên response/log có dữ liệu riêng.

## 10. Push code riêng lên remake

Chỉ công bố sau khi review nội dung, diff, test và smoke. Tài liệu này **không phải yêu cầu push tự động cho mọi lần sau**; khi nhờ Bot thực hiện cần nêu repo/nhánh/phạm vi muốn đẩy.

### 10.1. Trên dòng đã khớp lịch sử origin

Nếu đang làm ở nhánh thử bắt đầu từ `origin/i18n-vi` (đã cherry-pick phần local cần giữ và xử lý baseline), có thể cập nhật nhánh remote bằng push fast-forward rõ đích:

```bash
git status --short
git log --oneline origin/i18n-vi..HEAD
git diff --stat origin/i18n-vi..HEAD
git push --dry-run origin HEAD:i18n-vi
# Sau khi kiểm tra đích và được phép công bố:
git push origin HEAD:i18n-vi
```

Nếu remote vừa thay đổi, fetch lại, tích hợp thay đổi mới trên nhánh thử, chạy lại kiểm thử. Nếu bị non-fast-forward/auth/protection, **dừng**, không thêm `--force`, không né policy/hook.

Có thể đẩy nhánh thử riêng lên **remake** và review bằng PR nội bộ nếu quy trình repo yêu cầu; không tự gửi PR sang `kadaliao/open-super-agent`. Không cập nhật `main` chỉ vì đã cập nhật `i18n-vi`; đó là một quyết định riêng.

Sau khi công bố, kiểm tra ref/SHA remote. Nếu local `i18n-vi` đã cùng dòng, có thể fast-forward bình thường; nếu vẫn là dòng `8019180` độc lập, giữ nó làm branch an toàn và dùng nhánh đã đồng bộ làm dòng triển khai, không ép rewrite branch cũ. Tên nhánh không quan trọng bằng ancestor và nội dung đúng.

### 10.2. Khi chỉ có quyền qua CloudAgent

Gửi trợ lý điều phối commit/patch, repo, nhánh đích và kết quả kiểm thử để CloudAgent áp **các thay đổi cần thiết** trên dòng GitHub hiện có. CloudAgent ở đây là môi trường coding của trợ lý hỗ trợ bạn, không phải nút/endpoint hay tính năng model bên trong OSA. Yêu cầu giữ nguyên lịch sử remake, không force-push, không thao tác upstream. Không yêu cầu nó “upload lại toàn bộ tree” lên lịch sử khởi tạo mới: làm vậy tiếp tục nhân đôi dòng lịch sử.

Không nhầm “commit local thành công” với “đã push GitHub”. Báo cáo luôn tách: SHA local, SHA công bố (có thể khác nếu cherry-pick), nhánh và kết quả build/runtime.

## 11. Nếu cần quay lại bản chạy tốt

1. Dừng/tạm dừng công việc có tác động ngoài, ghi lại lỗi, SHA và phiên bản dependency.
2. Nếu merge chưa commit/công bố: review rồi `git merge --abort`; nó bỏ các chỉnh sửa thuộc lần merge đó, không hoàn tác thao tác trên dịch vụ khác.
3. Nếu đã commit: giữ branch lỗi để điều tra, tạo nhánh phục hồi từ mốc `safety/...` đã kiểm thử; build lại dependency/web và restart có kiểm soát. Không dùng `reset --hard` để xóa lịch sử.
4. Nếu đã push: sửa bằng commit mới hoặc revert được review, không force sửa lịch sử. Revert merge cần chọn đúng mainline; không chạy `git revert` merge một cách đoán mò.
5. Kiểm tra migration database trước khi chạy code cũ: Git rollback **không hạ schema DB**. Chỉ restore backup dữ liệu sau khi xác nhận tác động/mất dữ liệu mới và đã dừng server đúng cách.
6. Chỉ bật lại lịch/kênh chat ở một instance sau smoke thành công.

## 12. Tóm tắt cho lần cập nhật sau

```text
Backup source + dữ liệu
→ worktree sạch, remotes đúng, fetch origin/upstream
→ kiểm tra ancestor (xử lý baseline một lần nếu chưa có)
→ nhánh thử từ dòng remake, giữ đủ commit riêng
→ merge upstream/main, giải conflict/i18n/cron
→ dependency + compile + audit + build
→ restart một instance, hard-refresh và smoke
→ push rõ đích origin, không upstream, không force
→ ghi SHA/kết quả và theo dõi vận hành
```

Nguồn đối chiếu: [cấu hình](configuration.md), [phát triển](development.md), [Docker](docker.md), [i18n](i18n.md), [kiến trúc](architecture.md), [hướng dẫn vận hành VI](huong-dan-vi.md). Khi upstream thêm route/model/config/tính năng, phải kiểm tra source thực thay vì sao chép lệnh cũ không kiểm chứng.
