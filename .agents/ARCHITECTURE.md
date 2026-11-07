# Bản đồ kỹ thuật OSA

Nền hiện hành v0.6.0; đây là map để tìm đúng chỗ, không thay SCAN code ở ref mới. Chi tiết tại `docs/architecture.md`, `docs/i18n.md`, `docs/vi/` ở root.

## Thành phần

| Vùng | Vai trò và điểm vào |
|---|---|
| Backend | Python/FastAPI, `osa/server.py`: API + WebSocket `/ws`, lifespan/startup. `osa/router.py` nhận chat/route; `osa/worker.py` tác vụ nền; `run_heavy` trong `osa/worker.py` phối hợp nhiều worker; watchdog theo tiến độ/ngân sách. |
| Frontend | React + TypeScript + Vite trong `web/`; `src/store.ts`, `src/components/`. Build ra `osa/static/dist/` gitignored; push source không tự cập nhật bundle trên host. |
| Persistence | SQLite qua `osa/memory.py`; settings, bots, chats/tasks/usage và skills. Dữ liệu thật nằm ngoài source; import module có thể mở DB. |
| i18n | `osa/i18n.py`, `osa/locales/en.json`, `vi.json`; `web/src/i18n.ts`, `src/locales/en.json`, `vi.json`. Chinese-as-key, ZH dùng source, EN/VI dịch theo key. Fresh install VI; lựa chọn server đã lưu được giữ. LocalStorage/preference migration có test. |
| Skills | `osa/skills.py` quản bảng `skills`; shared `bot_id=NULL`, private override được ưu tiên. `osa/skillpacks.py` quản pack, hashes/default state; nguồn tracked trong `skills-pack/ai-native/`. |
| Routines | `osa/routines.py`, UI Routines: lịch/webhook, validate, reservation trước await filter, cleanup lỗi; quiet không gửi khi không mới. Không dùng routine thật để test. |
| Auth/channels | `osa/auth.py`: shared password `OSA_PASSWORD`, không phải multi-user/RBAC. Channels private/pairing nằm `osa/channels/`; API/WebSocket không đồng nghĩa external sends đã được duyệt. |
| Computer | `osa/computer/`: Docker local hoặc Instabox, CDP/VNC/takeover; task dùng cửa sổ riêng nhưng chia sẻ máy/files/logins. Không có Docker thì API báo unavailable/docker_missing. |
| Apps/pages | MCP catalog và runtime ở `osa/catalog/`, `osa/mcp_hub.py`; pages/files/library, vault và backups là dữ liệu vận hành, không đưa vào handoff repo. |

## Skills và verification

- Native body giới hạn 20.000 ký tự, description 200. Adapter ngắn ở DB, original `SKILL.source.md` và resources ở `<data-dir>/skill-packs/ai-native/<name>/`.
- `load_skill`/`read_skill_resource` có paging tối đa 5.500 ký tự (giảm khi JSON escape dài), trạng thái COMPLETE/CONTINUE_REQUIRED và next_offset. Đọc hết source/reference cần dùng; listing không phải execution.
- `osa/verification.py`: `verify_facts`, deterministic count/Decimal sums/source quotes/AC check ids; không shell/network. `markdown_body` khóa scope blog. Instruction gọi verifier chưa phải hard gate mọi câu model viết.
- `osa/local_checks.py`: inspect_repo/check_patch cho allowlist fixture nhỏ, snapshot và exact patch hash, offline bubblewrap, git check/apply/pytest; không apply vào source gốc. Registry do operator đặt cạnh DB, ngoài git; không đăng ký repo OSA/home/credential tree.
- Lifespan sau `settings.apply()` gọi `ensure_defaults`: bảy skill + mentor shared cho mọi bot, kể cả bot tạo sau. Source file-set/SHA-256 phải khớp. State version/hash cho phép update bản chưa sửa; giữ edits/resources/deletion tombstones và private overrides. SQLite serialize startup, nhưng không có atomic transaction xuyên FS+DB khi host crash.
- Opt-out `skills.ai_native_defaults: false` trong config hoặc `OSA_AI_NATIVE_DEFAULTS=false` (env ưu tiên). Không xóa skill đã cài. Lệnh `install` là reinstall chủ động, có thể mất edits; không dùng thay `defaults` nếu chưa được duyệt reset.

## Lệnh kiểm tra

Chạy từ repo root trên môi trường đã chuẩn bị. Dùng Python ≥3.11, uv; Node theo Vite lockfile (`^20.19.0 || >=22.12.0`). Không commit build output.

```bash
uv sync --locked
uv run python -m osa.i18n
uv run pytest -q -ra
uv run python -m osa.skillpacks verify-sources
(cd web && npm ci && npm test && npm run build)
git diff --check
```

Pytest fixtures phải thiết lập temp DB trước import. Không gọi CLI `defaults/install` vào DB thật chỉ để verify docs. Các lệnh catalog/templates có thể dùng để kiểm manifest, không phải test tất cả tài khoản/app thật.

`scripts/osa-start.sh` / `osa-stop.sh` quản instance local bằng PID/ownership, không broad pkill. Chỉ restart khi biết data dir và tác vụ đang chạy, có phê duyệt phù hợp. Mặc định loopback `127.0.0.1:8765`; trước public exposure cần OSA_PASSWORD + HTTPS, không mở VNC/CDP/tunnel không bảo vệ. Không dump settings/vault để tìm key.

CI đã có `.github/workflows/ci.yml`: backend compile/import/catalog/templates/i18n/pytest; frontend test/build; Docker compose/build/smoke. Trigger push hiện chỉ main, PR không giới hạn branch trong workflow. Chưa đọc check-runs thì không khẳng định CI remote xanh; coverage Docker Computer E2E không suy ra từ job app-image smoke.

## Quan hệ upstream và lịch sử

Remake GitHub ban đầu là snapshot, không cùng ancestry upstream; cùng tree không có nghĩa cùng SHA/merge-base. Kiểm shallow/ancestor trước reconcile, không force-push hay merge unrelated hàng loạt.

Lần v0.6: merge trực tiếp gặp khoảng 64 conflict giữa i18next cũ và Chinese-as-key. Abort; dựng trên upstream `9790ffa` (v0.6.0), port VI + missing-Docker + routine hardening có chọn lọc. Local từng nối ancestry safety bằng `ours` sau khi tree đã test; **không dùng chiến lược đó làm mẫu merge chung**. Public nhận delta bằng forward commits trên lịch sử remake qua PR #1, không thay lịch sử GitHub bằng upstream.

Lần cập nhật sau: đọc release/diff upstream, tạo safety, nhánh remake mới; port delta/commit có chọn lọc, giữ VI/security/tests rồi PR i18n-vi. Không tự restore i18next hoặc cherry-pick merge commit mù quáng. Quy trình chi tiết trong `docs/cap-nhat-tu-upstream.md`.
