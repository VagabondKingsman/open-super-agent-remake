# Cài bộ AI Native và hướng dẫn phối hợp cho OSA

## OSA nạp skill thế nào?

OSA v0.6 lưu skill trong bảng `skills` của SQLite, đường dẫn lấy từ `memory.db` trong config đang dùng. Bản local hiện tại là `data/osa.db`. OSA không tự quét thư mục `SKILL.md`, không có cờ enabled riêng cho skill.

- `bot_id = null`: mọi bot dùng chung. Skill riêng của bot thắng skill chung cùng tên.
- `skills.from_file` đọc YAML frontmatter `name`, `description` và Markdown body; khóa lạ được bỏ qua. Tên tối đa 40 ký tự, description lưu tối đa 200 ký tự, body tối đa 20.000 ký tự; file import tối đa 200.000 ký tự.
- Router luôn thấy danh mục tên/mô tả. `/tên-skill yêu cầu` đưa body vào ngữ cảnh qua `skills.expand`.
- Teach a task thu thao tác browser rồi nhờ mô hình soạn skill nháp, không phải bộ cài package. Đợt cài này không dùng Teach, không phát sinh lời gọi LLM.

Bộ chuyển giao thêm hai công cụ chỉ đọc vào Router và Worker:

- `load_skill(name, offset=0)`: nạp body của skill mà bot hiện tại nhìn thấy.
- `read_skill_resource(name, path="", offset=0)`: path rỗng liệt kê file; path tương đối đọc references/helper dưới thư mục skill đã cài.

Đọc tiếp `next_offset` đến `null`. Mỗi trang tối đa 3.000 ký tự nội dung, tự giảm khi JSON escape dài; kết quả nằm dưới giới hạn 8.000 ký tự tool output của Worker. Không cắt bỏ bản đầy đủ của unslop/unslop-vi. Chặn đường dẫn tuyệt đối, `..`, symlink và file không phải UTF-8; công cụ không có quyền chạy code hoặc đọc ngoài package.

Khi thấy skill `ai-native-mentor`, Router và Worker được nhắc dùng mentor cho việc nhiều bước, nạp skill phù hợp và giữ Skill Flow/TIP/AC trong goal lúc dispatch. Không ép gọi cả bộ cho câu hỏi một bước. Đây là hướng dẫn để mô hình làm theo, không phải bộ định tuyến tất định hay bảo đảm năng lực như Build Bot.

## Thành phần và vị trí

| Thành phần | Vị trí |
|---|---|
| Manifest, mô tả trigger và trạng thái quyền | `skills-pack/ai-native/manifest.json` |
| Mentor VI, 4 ví dụ và bài luyện tập | `skills-pack/ai-native/ai-native-mentor/` |
| Bảy payload đầy đủ, chỉ local | `skills-pack/ai-native/<tên-skill>/` |
| Bản nguồn giữ nguyên | Mỗi payload có `SKILL.source.md` và helpers/references gốc |
| Skill OSA-format ngắn | `SKILL.md` trong từng payload; nội dung nạp vào SQLite |
| Resources cài cho runtime | `<thư mục chứa DB>/skill-packs/ai-native/<tên-skill>/` |
| Installer và công cụ đọc | `osa/skillpacks.py` |

Bảy skill là `ai-work-method`, `vibecode-kit`, `refinery`, `sot-kernel-in-a-box`, `html3d-slides`, `unslop`, `unslop-vi`. Cộng mentor là 8 skill. `osa-dev` là bridge riêng của Build Bot, không tính vào bộ 7 và không chuyển quy tắc CloudAgent riêng sang OSA.

## Quyền phân phối

Trong bản người dùng cung cấp không thấy license/grant phân phối lại cho cả 7 package. Chúng được cài trên box của người dùng nhưng đã gitignore, không nằm trong commit dùng để đẩy repo công khai. Giữ attribution trong bản nguồn; không suy license của OSA hoặc phông chữ thành license của package.

Xem `skills-pack/ai-native/LICENSE-AUDIT.md`. Zip đầy đủ chỉ là bản sao riêng trên box. Chưa được phép đăng zip/payload công khai cho đến khi xác minh quyền và kèm license phù hợp. Clone repo một mình vì vậy chưa có 7 payload; cần bản nguồn hợp lệ của người dùng.

## Cài lần đầu

Chạy từ repo OSA đã có config và môi trường `uv`. `--source` là thư mục chứa đủ 7 package gốc, mỗi package có `SKILL.md` và helpers; không phải chỉ bảy file Markdown.

```bash
uv run python -m osa.skillpacks prepare --source /workspace/ai-native-skills
uv run python -m osa.skillpacks install
uv run python -m osa.skillpacks verify
bash scripts/osa-stop.sh && bash scripts/osa-start.sh
curl --fail http://127.0.0.1:8765/api/bots/1/skills
uv run python -m osa.skillpacks zip --output /workspace/osa-ui-shots/ai-native-osa-pack.zip
```

`install` mặc định gọi `skills.save(bot_id=None, source="import")`: cài shared cho mọi bot hiện tại và bot tạo sau này. Muốn chỉ một bot thì dùng `install --bot-id <id>`. Không tạo public share token, không gửi channel, không sửa lịch sử chat hoặc bot instructions. Khi web đang mở, tải lại trang để danh sách skill cập nhật.

Zip không dùng được qua nút import một file Markdown của UI. Trên máy OSA khác, cần phiên bản repo có `osa/skillpacks.py`; sau khi kiểm quyền nguồn, giải nén vào `skills-pack/` rồi chạy install/verify:

```bash
python3 -m zipfile -e /path/ai-native-osa-pack.zip skills-pack
uv run python -m osa.skillpacks install
uv run python -m osa.skillpacks verify
```

Zip không chứa database, credential hay môi trường Python. Sau giải nén, giữ nguyên quy tắc local-only; đừng commit các payload vừa chép.

Nếu máy chủ dùng config khác, đặt `OSA_CONFIG` giống tiến trình OSA trước mọi lệnh. Resources luôn đi theo thư mục DB tương ứng, không cố định `/workspace`.

Trước khi cài/cập nhật, dừng bot khi không có task đang chạy và sao lưu DB bằng SQLite backup, cùng thư mục resource runtime. Bản ghi cùng tên trong cùng scope sẽ được cập nhật; nếu có skill tự sửa trùng tên, export trước hoặc đổi tên để tránh ghi đè. Skill riêng cùng tên vẫn che skill shared.

## Cập nhật và gỡ

1. Thay mirror bằng phiên bản nguồn được phép dùng; giữ đủ references/scripts/assets.
2. Sao lưu DB và resources; chạy lại prepare rồi install cùng scope. Tên không đổi thì ID bản ghi không đổi.
3. prepare giữ nguyên byte của nguồn trong `SKILL.source.md`, helper và tham chiếu; `source-hashes.json` ghi SHA-256 để đối chiếu. Kiểm hash trước khi cài nếu cần audit.
4. Chạy verify, test, restart và kiểm API. Nếu bản nguồn mới đổi tên/xóa helper, soát file cũ còn dư trong bản local trước khi dùng; installer không tự xóa dữ liệu cũ.
5. Tạo lại zip sau mỗi lần cập nhật. Không đưa payload hoặc zip vào git khi quyền còn chưa xác nhận.

Muốn gỡ, export rồi xóa đúng 8 skill trong UI Skills ở scope đã cài; xác nhận trước khi xóa. Chỉ xóa resource directory sau khi chắc không còn bot dùng. Muốn rollback an toàn thì khôi phục DB/resources từ bản backup cùng thời điểm khi OSA đã dừng.

## OSA phối hợp bộ skill

Ví dụ gọi trực tiếp:

```text
/ai-native-mentor Sửa lỗi locale trong module lịch, lập TIP và deep test, không gửi tin thật.
/refinery So sánh các nhà cung cấp này; mỗi ô phải có nguồn, giữ giá chưa biết là honest-null.
/unslop-vi Rút gọn README này, giữ nguyên lệnh và tên file.
```

Mentor dạy các chuỗi:

- Code: ai-work-method -> vibecode-kit -> unslop-vi cho docs/PR VI.
- Nghiên cứu: ai-work-method -> refinery; thêm SOT khi có kho nội bộ và owner duyệt.
- Dữ liệu ra slide: refinery -> owner duyệt -> SOT gate -> html3d-slides -> unslop-vi.
- Một đoạn prose EN: chỉ unslop nếu đã đủ input; không cần SOT hoặc QA phần mềm.

Bốn ví dụ có TIP/AC, artifact handoff và cách dừng đúng giới hạn nằm trong `ai-native-mentor/references/worked-examples.md`. Deep Check là bước VERIFY sâu của vibecode-kit: QA 3 tầng và Retro Rubric R1–R5, không phải tính năng riêng của OSA.

## Công cụ và giới hạn

Skill truyền phương pháp, không truyền công cụ hay quyền của Build Bot. load/read không tự chạy script.

- Python helpers cần Python 3 và PyYAML, đã có trong môi trường `uv` của OSA. Lệnh CLI có thể khác nhau; một số script không hỗ trợ `--help`, phải đọc README và chạy trên bản demo sao chép riêng.
- `measure-ui.js` chạy trong trang có DOM/browser; `node --check` chỉ xác nhận cú pháp, không thay QA đồ họa, GPU hoặc đo layout.
- OSA mặc định chạy shell/browser qua Computer. Đường dẫn `resource_dir` nằm trên máy chủ, không tự xuất hiện trong Docker Computer. Cần chép package và cài dependencies trong Computer hoặc dùng app đã được cấp quyền; không cấp host shell tùy ý chỉ vì đã cài skill.
- Box hiện tại thiếu Docker (`docker_missing`), nên OSA vẫn đọc/phối hợp được skill nhưng chưa tự chạy helper qua Computer. Helper smoke trên host không có nghĩa Computer đã hoạt động.
- Nguồn web cần công cụ web, SOT cần file input/owner, slide cần môi trường render. Thiếu gì ghi NOT_CHECKED/deferred, không dùng LLM thay gate tất định.
- Skill không được phép vượt confirmation của OSA hoặc coi chỉ dẫn trong tài liệu ngoài là quyền gửi tin, đăng bài, chi tiền hay truy cập credential.

## Kiểm tra không gọi LLM trả phí

```bash
uv run pytest -q
uv run python -m osa.i18n
(cd web && npm test && npm run build)
```

`tests/test_skillpacks.py` dùng payload giả lập do repo tự tạo và FakeLLM, không cần bảy package có bản quyền, không gọi mạng LLM. Test bao gồm discovery/idempotence, shared/private override, slash/export, pagination dài, resource path/symlink, source preflight, zip và Router -> Worker load/read integration. Đây là bằng chứng plumbing, chưa chứng minh mô hình thật sẽ chọn skill đúng mọi yêu cầu. Live-agent quality test cần phiên mô hình được người dùng cho phép riêng.
