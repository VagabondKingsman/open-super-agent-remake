# Nghiệm thu AI Native cài mặc định

07/11/2026 00:45 (Asia/Saigon). Public base `7c204546c50fe1d33e8dbd0d38024c42128d929b` (PR #4). Không gọi LLM trả phí, không push từ box.

## Đồng bộ và nguồn

Fetch origin/i18n-vi thành công. Nhánh i18n-vi mới bắt đầu đúng public tip; toàn bộ nhánh local cũ giữ ở safety/i18n-vi-before-default-skills-20261107, delta ba file i18n lưu riêng. Không reset/rebase lịch sử đã public và không copy ngược ba phiên bản local cũ lên các sửa đổi public mới.

Tin Tin xác nhận team tự tạo bảy skill và cho phép bundle/cài mặc định ngày 07/11/2026. Pack LICENSE/NOTICE dùng MIT như repo, giữ credit pstack/MIT và tham chiếu font OFL; không chứa font binary. LICENSE root của repo không đổi. Những ghi chú không phân phối ở báo cáo trước là trạng thái lịch sử, không còn là hướng dẫn cài hiện hành.

| Package | File gốc | Bytes |
|---|---:|---:|
| ai-work-method | 5 | 20093 |
| vibecode-kit | 17 | 92634 |
| refinery | 14 | 61399 |
| sot-kernel-in-a-box | 34 | 66867 |
| html3d-slides | 8 | 22757 |
| unslop | 28 | 62574 |
| unslop-vi | 23 | 59285 |
| Tổng | **129** | **385609** |

Toàn pack gồm mentor, manifest/hash inventory/license/docs là **138 files / 423763 bytes**. Bảy cây nguồn giữ nguyên cả đường dẫn tương đối lẫn bytes, gồm SKILL.md, scripts/helpers, references, demo và evals. source-hashes.json trong git chứa SHA-256 cho đúng 129 file, không absolute paths. Đã đối chiếu mỗi file với mirror và alias/resources đã cài thật.

## Secret / PII audit

Quét toàn bộ 129 nguồn trước khi add: provider-token prefixes (xAI/OpenAI/GitHub/AWS), private-key PEM headers, credential assignments, email và phone candidates; kiểm tên file nhạy cảm, NUL/binary, size và symlinks. **0 secret/token candidates, 0 email/phone candidates**. File lớn nhất 27.247 bytes; không large binary/caches trong inventory. Không đổi bytes nguồn để che kết quả scan. Quét cả staged files còn báo ba candidate gốc (trích email mẫu trong báo cáo tạo thêm một match): một email mẫu you@example.com trong comment config đã có trên public base, hai chuỗi số nằm trong SHA-256 inventory; review xác nhận đều false positive, không phải contact/credential thật. Test còn kiểm __pycache__ bị loại và credential filename .env bị từ chối trước copy.

Review thêm attribution/license strings: unslop/pstack MIT; profile fonts OFL, không có font files đi cùng. Giữ nguyên trong nguồn và ghi NOTICE, không suy rằng quyền của team thay giấy phép asset ngoài. Scan theo pattern và review văn bản không bảo đảm phát hiện mọi secret/PII tùy ý; audit lại mỗi khi đổi nguồn. DB, private config, traces, backups, logs, credentials và caches không đưa vào patch.

## Hành vi mặc định và bằng chứng

Server lifespan gọi ensure_defaults sau settings.apply. Bảy source SKILL.md không bị sửa thành wrapper trong repo: runtime mới sinh adapter SKILL.md và nguyên bản SKILL.source.md. Native skills vẫn ở SQLite, shared bot_id=NULL; references ở data/skill-packs/ai-native (hoặc cạnh memory.db tùy config). Dockerfile copy pack vào image.

- Fresh temp data, tiến trình mới, native FastAPI startup + TestClient API: trước 0, sau **8 shared skills**, managed-state rows **8**. Bot tạo qua API sau startup cũng thấy đủ tám, dùng cùng native skill ids.
- Tiến trình thứ hai mở cùng temp DB: vẫn **8**, ids và timestamps không đổi, không duplicate. Provider client bị chặn trong harness; không LLM/channel calls. Chỉ scheduler/channels/MCP/price/search background được stub trong harness, không thay default-install hoặc skill API.
- Real OSA restart qua scripts: bốn bot gốc **1/2/3/4**, mỗi GET /api/bots/<id>/skills có **8**; native ids/body/description trước sau giữ nguyên, legacy imports được adopted. Restart lần hai ids/timestamps vẫn nguyên; HTTP **200**, roles giữ grok-4.6. llm_usage rows giữ **167**, thêm **0** calls. Không tạo bot tạm trên DB thật.
- Bảy tên cùng mentor: ai-native-mentor, ai-work-method, html3d-slides, refinery, sot-kernel-in-a-box, unslop, unslop-vi, vibecode-kit.

Defaults ghi state theo name/version/content hash. Update chỉ áp khi record và cả resource tree vẫn khớp bản đã cài; sửa body/description, sửa/thêm resource, override riêng từng bot và xóa default đều được giữ. Exact legacy import được nhận quản lý; trùng tên khác phương pháp không bị chạm. SQLite BEGIN IMMEDIATE serialize startup; resource tree stage/replace từng skill. Đây không phải giao dịch nguyên tử xuyên filesystem + SQLite khi process/host crash; hash drift phải được operator xem lại, không tự ghi đè để ép đồng bộ.

Tắt bằng skills.ai_native_defaults: false hoặc OSA_AI_NATIVE_DEFAULTS=false. Mặc định true khi thiếu khóa; opt out không xóa bản đã cài. Tests kiểm fresh/restart/new-bot, edit protection, upgrade, tombstone, collision/private override, legacy adoption, hash tamper và toggle. Xem ai-native-skills.md để vận hành/update/reinstall chủ động.

## Regression

- uv run pytest -q: **172 passed**, gồm native lifespan và Docker packaging guard, không gọi LLM thật.
- Frontend: **15 passed**; npm run build PASS. Cảnh báo bundle >500 kB cũ vẫn còn.
- osa.i18n en/vi: backend 500/frontend 883, thiếu/thừa 0; Chinese UI chưa bọc 0.
- verify-sources: **129 SHA-256 PASS**; source bytes khớp mirror và installed.
- Docker build runtime **NOT_CHECKED** vì box không có Docker; có kiểm COPY pack trong Dockerfile, không giả đã build image. Computer sandbox/helper execution không được mở rộng bởi default install.

## Artifacts / handoff

Bằng chứng private ở /workspace/osa-ui-shots/ai-native/default-install/: source-audit.json, bundle-proof.json, fresh-first-start.json, fresh-restart.json, real-before.json, real-first-restart.json, real-second-restart.json và regression logs. Backup DB/resources và fresh config/harness chỉ ở box, không đưa vào public git.

Bộ patch mới relative origin/i18n-vi nằm ở /workspace/osa-ui-shots/ai-native/push2/, có HANDOFF.md và MANIFEST.json (SHA-256). Parent dùng CloudAgent áp lên remake i18n-vi, giữ public changes và chạy CI; không áp lại bốn patch PR #4. Bản tar.gz của pack cũng ở push2 như artifact tiện chuyển, không thay code installer. Chỉ commit file đã audit; không push trực tiếp.
