# Bộ AI Native cài mặc định trên OSA

Repo đi kèm bảy package gốc: ai-work-method, vibecode-kit, refinery, sot-kernel-in-a-box, html3d-slides, unslop, unslop-vi; cộng lớp hướng dẫn ai-native-mentor. Tin Tin đã xác nhận đây là các skill do team mình tạo và cho phép đóng gói. Xem skills-pack/ai-native/NOTICE.md và LICENSE (MIT như repo); credit gốc và tham chiếu font giữ nguyên.

## Cài lần đầu và bot mới

Chạy OSA như thường lệ. Trong FastAPI lifespan, sau settings.apply(), server gọi skillpacks.ensure_defaults(). Không cần lệnh import, mirror riêng, shell LLM hay API trả phí để cài. Dockerfile cũng copy toàn bộ pack vào image; không chỉ bản chạy từ checkout.

- Nguồn đi cùng repo: skills-pack/ai-native/<name>/. Bảy SKILL.md và mọi helper/reference giữ nguyên bytes, không thay bằng adapter. source-hashes.json kiểm đúng tập file và SHA-256 trước khi cài.
- Native store vẫn là bảng skills trong SQLite theo memory.db. Các default có bot_id=NULL, dùng chung cho mọi bot. list_for() giữ bot-specific override ưu tiên hơn shared; bot tạo sau tự thấy defaults, không copy thêm tám hàng cho từng bot.
- Runtime resources ở thư mục cạnh DB: <data-dir>/skill-packs/ai-native/<name>/. Với cấu hình mặc định là data/skill-packs/ai-native/.
- Khi cài bảy nguồn, installer tạo SKILL.md adapter ngắn cho runtime; SKILL.source.md chứa đúng bytes SKILL.md gốc. Helpers/references giữ đường dẫn tương đối như nguồn. Mentor có body/reference riêng, không cần alias.
- SQLite chỉ lưu adapter và mentor theo native format, không nhồi mọi reference vào prompt. Giới hạn body native vẫn 20.000 ký tự, description 200; tool đọc source/reference theo trang tối đa 5.500 ký tự, giảm thêm khi JSON escape dài.

## Cập nhật an toàn, không ghi đè bản sửa tay

Bảng bundled_skill_state ghi name, native skill id, version, bundle hash, record hash và resource-tree hash. Startup chạy trong SQLite BEGIN IMMEDIATE để serialize hai tiến trình cài cùng lúc.

- Lần đầu: tạo tám shared skill và resource trees sau khi preflight toàn bộ pack.
- Cùng version/hash: không tạo bản trùng, không đổi id/timestamp.
- Pack đổi version/hash: chỉ cập nhật skill có record và resources vẫn khớp bản installer đã cài trước. Resource tree được stage riêng rồi replace; không chạy helper trong quá trình cài.
- Body/description bị người dùng sửa, helper/reference đổi hoặc thêm file, native id khác: giữ nguyên cả skill/resources đó, báo preserved-user-edit. Các skill khác vẫn cập nhật.
- Shared skill có sẵn cùng tên nhưng khác nội dung: giữ nguyên, báo preserved-unmanaged. Legacy import khớp hoàn toàn có thể adopted mà không thêm hàng.
- Bot-specific override không bị chạm. Người dùng đã xóa default: metadata giữ tombstone, không tự tạo lại sau restart (preserved-deletion).

Hash là kiểm tính toàn vẹn, không phải chữ ký xác thực hay bằng chứng helper an toàn. Không sửa source-hashes.json để che một file chưa audit. Nếu source hash/file set sai, startup dừng trước cài, báo lỗi; có thể opt out để mở app và xử lý pack.

## Tắt auto-install/reconcile

Trong config.yaml:

```yaml
skills:
  ai_native_defaults: false
```

Hoặc đặt OSA_AI_NATIVE_DEFAULTS=false trước khi khởi động; env có ưu tiên hơn YAML, nhận true/false/1/0. Không có khóa cấu hình thì mặc định true để bản cài cũ cũng nhận pack. Opt out không xóa skill/resources đã cài và không tắt quyền dùng chúng. Muốn gỡ, export/backup rồi xóa đúng skill trong UI sau khi chủ việc xác nhận.

## Cập nhật nguồn trong repo

1. Backup data/DB/resources trước thay đổi. Kiểm quyền và giữ attribution/license riêng nếu nguồn mới có.
2. Đồng bộ từ mirror đã duyệt: uv run python -m osa.skillpacks prepare --source /path/to/approved/mirror. Lệnh giữ tên file gốc, bỏ cache; từ chối symlink, credential filenames, binary/large payload. Không sửa bytes nguồn để thích nghi host; sửa adapter trong osa/skillpacks.py.
3. Quét secrets/PII và review diff; kiểm uv run python -m osa.skillpacks verify-sources. Mỗi thay đổi nguồn cần source-hashes.json tương ứng. Tăng version trong manifest khi phát hành phương pháp mới; thay hash nội dung cũng được phát hiện dù chưa tăng version.
4. Chạy tests/build/i18n, commit nguồn + manifest. Server restart reconcile những bản chưa sửa tay. uv run python -m osa.skillpacks defaults chạy cùng cơ chế an toàn mà không cần restart.
5. uv run python -m osa.skillpacks verify báo native discovery/resources. uv run python -m osa.skillpacks zip --output /path/ai-native-pack.zip tạo archive đầy đủ.

Lệnh install là **reinstall chủ động**, khác defaults: thay nội dung/resources trùng tên, có thể mất sửa tay. Chỉ dùng sau backup và khi chủ việc muốn reset. Với --bot-id, chỉ thay native record ở scope bot nhưng resources vẫn shared theo tên; không dùng lệnh đó để tạo phiên bản resource riêng từng bot.

## Nạp và phối hợp lúc chạy

Prompt chỉ có danh sách tên/mô tả. Router và Worker đều có load_skill và read_skill_resource; load_skill trả method_source cho adapter. Đọc tiếp next_offset đến null/COMPLETE; CONTINUE_REQUIRED không phải đã đọc đủ. path rỗng liệt kê resources, không chạy code. Goal dispatch phải tự đủ TIP/AC, Skill Flow, input/output và giới hạn; Worker nạp lại skill vì không thấy tool result riêng của Router.

Mentor dạy:

- Code: ai-work-method -> vibecode-kit -> unslop-vi cho docs/PR VI. SCAN/TIP/VERIFY rút gọn cho bug nhỏ; QA 3 tầng và Retro Rubric theo rủi ro.
- Nguồn ngoài: ai-work-method -> refinery; giữ evidence_span/origin_id/disputed/honest-null, không tính trang sao chép là nguồn độc lập.
- Nguồn nội bộ: ai-work-method -> sot-kernel-in-a-box, có owner/A3/digest/bites/publish gate.
- Research ra slide: refinery -> owner duyệt -> SOT gate -> html3d-slides -> unslop-vi.
- Prose EN/VI: unslop/unslop-vi; lỗi chính tả một bước thì trả trực tiếp, không ép TIP hay cả bộ.

Bốn ví dụ ở ai-native-mentor/references/worked-examples.md. Có thể gọi /ai-native-mentor, /refinery hoặc /unslop-vi trong chat như native skills khác.

Router/Worker có [verify_facts](deterministic-verification.md); blog dùng markdown_body, copy counts/totals từ tool. Patch fixture được operator cấp quyền có [inspect_repo/check_patch trong sandbox](local-patch-checks.md), không bàn giao như đã đạt khi apply/test chưa PASS.

## Giới hạn và kiểm tra

Skill không cấp thêm quyền gửi tin, đăng bài, chi tiền, đọc credential hay chạy code trên host. Helper Python cần dependencies tương ứng (thường PyYAML); chỉ đọc helper không có nghĩa đã chạy. Computer/Docker vẫn cần cài riêng; resource_dir trên host không tự xuất hiện trong Docker. measure-ui.js cần DOM/browser; node --check không thay render/GPU/layout QA. Thiếu runtime/source/owner thì NOT_CHECKED, không lấy LLM thay gate tất định.

```bash
uv run pytest -q
uv run python -m osa.i18n
(cd web && npm test && npm run build)
```

Bằng chứng default-install và scan: [ai-native-default-install.md](ai-native-default-install.md). Kết quả LLM thật trước đây, lỗi và giới hạn: [ai-native-live-eval.md](ai-native-live-eval.md); đợt cài mặc định không gọi LLM trả phí.
