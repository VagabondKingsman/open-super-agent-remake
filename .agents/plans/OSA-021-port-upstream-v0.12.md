# OSA-021 · Plan cập nhật upstream v0.6.1 → v0.12.0

Soạn 09/11/2026 khoảng 12:50 Asia/Saigon. Người soạn: Hoplite. Trạng thái: **PLAN, chưa BUILD**. Chưa claim trên BOARD, chưa push.

- Skill Flow: osa-dev → ai-work-method → vibecode-kit (quy mô lớn: đủ 8 bước) → unslop-vi cho docs.
- Base remake: `i18n-vi` = `3b02a80` (merge PR #16). Upstream `kadaliao/open-super-agent` `main` = tag `v0.12.0` = `d432c74`. Remote `upstream` chỉ fetch, push URL `DISABLED`.
- Quy trình gốc: `docs/cap-nhat-tu-upstream.md`, `.agents/ARCHITECTURE.md` mục "Quan hệ upstream", `.agents/DECISIONS.md`, log `2026-11-07-grok-bot-port.md` (OSA-004).

## 1. SCAN

### Upstream đã ra gì

| Tag | Ngày (UTC) | Nội dung chính | Liên quan bản web tự host |
|---|---|---|---|
| v0.7.0-preview.1/2 | 07/11 | App desktop macOS (Tauri), backend `host` dùng Chrome của máy, đăng nhập bằng vé một lần, **tool Computer phải qua luật xác nhận** | Phần server: có. Desktop: không |
| v0.7.0 | 07/11 | Ảnh/tệp trong chat (model đọc ảnh), Bot vẽ ảnh, card link/embed, thread trả lời, avatar, ghim, retry khi model báo 500, app iPhone + relay push | Phần lớn có, trừ iPhone/relay |
| v0.8.0 | 08/11 | **Khóa server `security.local_exec` + chế độ demo**, vá rò key khi đổi URL provider, chặn `{env:}` trong app market; Bot chính tạo Bot; điều khiển Mac | Bảo mật + tạo Bot: có. Mac: không |
| v0.9.0 | 08/11 | Báo trả lời thread, sửa Markdown `~`, `<br>` trong bảng, Bot chính dùng danh sách Bot thật | Có |
| v0.10.0 | 08/11 | Parser tool call DSML của DeepSeek, tạo Bot xong Bot chính nói tiếp, vuốt lùi trên điện thoại | Có |
| v0.11.0 | 09/11 | Tool registry, applet trong chat, MCP Apps, plugin Python, trang Quan sát (`llm_calls`), Bot chính quản mọi Bot và routine | Có, plugin để tắt mặc định |
| v0.12.0 | 09/11 | Sự kiện (15 nguồn, 63 mẫu, `/hooks/<key>`), `run_code`/`quick_code` trong sandbox, skill pack có file + `use_skill` + market, tách `security.exec/plugins/apps`, luật xác nhận theo tham số | Có |

84 commit, 346 file. Bỏ `desktop/`, `mobile/`, `deploy/relay`, `deploy/demo` thì còn khoảng 166 file, +27.000 dòng ở `osa/`, `web/`, `tests/`. Không thêm dependency Python/npm bắt buộc. Schema DB chỉ thêm bảng/cột (`media`, `avatars`, `unfurls`, `llm_calls`, `event_state`, `page_data`, `plugins`, `chats.parent/root/image/seen`, `skills.files/apps`...). Upstream thêm `.github/workflows/desktop.yml`.

### Remake đang khác upstream ở đâu

- Không có merge-base giữa `HEAD` và `upstream/main` (đã kiểm, repo không shallow).
- Phần code riêng của remake so với `3432671`: 72 file, +4.985/−662 ở `osa/`, `web/`, `tests/` (không tính locale). Gồm:
  - Module riêng, tự đứng: `osa/skillpacks.py`, `osa/verification.py`, `osa/local_checks.py`, `web/src/formatUsd.ts`, `osa/locales/vi.json`, `web/src/locales/vi.json`.
  - Sửa chen vào file upstream: `router.py` (+264/−202, prompt tiếng Anh, Heavy), `worker.py` (+274/−68), `memory.py` (USD, Heavy), `prices.py` (USD), `providers.py` (429/402, retry), `i18n.py` (vi mặc định, fallback), `routines.py`, `computer/tools.py`, `web/public/sw.js`, `web/src/i18n.ts`.
  - 12 file test riêng (~2.300 dòng): audit fixes, Heavy, cost USD, i18n VI, prompt language, skillpacks, verification, local checks, locale fallback.
- 49 file cả hai bên cùng sửa. Nặng nhất: `router.py`, `worker.py`, `memory.py`, `routines.py`, `server.py`, `Chat.tsx`.

### Điểm upstream đã giải quyết giúp audit 09/11

- `computer_shell` và `computer_write_file` không cần xác nhận (High #1): v0.7.0-preview.2 đưa tool Computer qua luật xác nhận; v0.12 thêm "luôn cho phép prefix này".
- Root + `docker.sock` (High #2): khóa server `security.exec` giảm đường RCE từ web. Mount socket vẫn còn.
- Các mục còn lại (vòng nền không try/except, SQLite không WAL, OSA-015 data dir, CI không chạy trên `i18n-vi`) phải đối chiếu lại sau port.

## 2. Chọn chiến lược (cần Tin Tin duyệt)

| | A · Port từng release lên remake | B · Dựng nền v0.12.0 rồi port lại phần remake (đề xuất) |
|---|---|---|
| Cách làm | Áp tay ~45 commit đáng lấy, theo thứ tự phụ thuộc | Trên nhánh từ `i18n-vi`, thay code `osa/ web/ tests/` và file gốc bằng cây v0.12.0 trong một commit forward; rồi port lại ~5.000 dòng của remake theo từng TIP |
| Khối lượng sửa tay | ~27.000 dòng upstream chen vào file remake đã đổi | ~5.000 dòng remake, trong đó 2.300 là test chuyển gần nguyên |
| Rủi ro | Commit upstream phụ thuộc chéo (registry, security, newbot→botadmin, media); dễ sót hunk | Mất sửa riêng nếu bỏ sót; có 12 file test remake làm lưới chặn |
| Tiền lệ | Port v0.6.1 (3 commit nhỏ) | Port v0.6.0 (`DECISIONS.md`: dựng trên v0.6.0, port VI có chọn lọc) |

Cả hai đều là commit forward trên lịch sử remake. Không merge `--allow-unrelated-histories`, không force-push, không reset.

## 3. VISION · đích sau khi port

- OSA 0.12.0 bản web tự host: đủ tính năng server/web của v0.7–v0.12, VI mặc định, EN/ZH, Chinese-as-key.
- Giữ nguyên các sửa riêng của remake: prompt gửi model bằng tiếng Anh, trả lời theo `i18n.lang()`, Heavy (một Heavy mỗi lượt, quorum, dừng khi hết hạn mức), chi phí USD, skill pack AI Native mặc định, `verify_facts`, `inspect_repo`/`check_patch` trong bwrap, trang offline VI.
- Không build desktop/iPhone. Thư mục `desktop/`, `mobile/` (đề xuất) giữ trong cây cho lần port sau đỡ lệch, nhưng tắt workflow `desktop.yml`.
- Mặc định an toàn cho server: `security.exec` theo khuyến nghị upstream cho máy công khai, plugin tắt, vẽ ảnh không bật nếu chưa có giá USD và duyệt chi phí.

## 4. TASK GRAPH (chiến lược B)

| TIP | Việc | Phụ thuộc | AC chính |
|---|---|---|---|
| TIP-0 | Chuẩn bị: safety branch `safety/i18n-vi-before-v0.12-<ngày>`, ghi baseline (pytest 244 pass/3 skip, i18n 562/888, JS 1.156 kB), backup data box bằng `osa.backup` | — | Có SHA safety, số baseline, file backup ngoài git |
| TIP-1 | Commit nền: lấy cây v0.12.0 cho `osa/`, `web/`, `tests/`, `pyproject.toml`, `uv.lock`, `config.yaml`, `Dockerfile`, `compose.yaml`, `desktop/`, `mobile/`, `deploy/`; giữ `.agents/`, `skills-pack/`, `docs/` VI, `scripts/`, README VI/EN/ZH, `.github/` của remake | TIP-0 | Bảng provenance file nào lấy upstream, file nào giữ remake; `uv sync --locked` chạy |
| TIP-2 | Port module riêng: `skillpacks`, `verification`, `local_checks`, `formatUsd`, `sw.js` offline; đăng ký tool qua `registry` mới thay chuỗi if | TIP-1 | `test_skillpacks`, `test_verification`, `test_local_checks`, `test_skill_defaults`, `sw-offline.cjs` PASS; `verify-sources` PASS |
| TIP-3 | i18n: `vi` mặc định + fallback; dịch ~550 khóa backend và ~250 khóa frontend mới sang VI | TIP-1 | `osa.i18n` exit 0, thiếu 0; `test_i18n_vi`, `test_locale_fallback` PASS; UI không còn tiếng Trung khi chọn VI |
| TIP-4 | Prompt: chuyển prompt mới của upstream sang tiếng Anh (`PRIMARY_RULE`, applet `GUIDE`, `BOTADMIN_TURN`, `use_skill`, `run_code`, `send_file`, `generate_image`, ghi chú hệ thống trong `memory.context`...), giữ chỉ thị trả lời theo `i18n.lang()` | TIP-1 | `test_prompt_language` mở rộng cho prompt mới, CJK trong prompt gửi model = 0 |
| TIP-5 | Heavy + audit fixes: đối chiếu từng sửa OSA-009/010 với code v0.12, chỉ port phần upstream chưa có | TIP-2, TIP-4 | `test_heavy_reliability`, `test_audit_fixes` PASS (sửa test chỉ khi hành vi upstream mới đúng hơn, ghi lý do) |
| TIP-6 | Chi phí USD: bảng giá tay USD, `image_price` USD, ghi `llm_calls` bằng USD, migration `llm_usage` → `llm_calls` không chia hai lần, trang Quan sát hiện `$` | TIP-1 | `test_cost_usd` mở rộng cho `llm_calls`; migrate DB copy từ box: tổng USD trước/sau khớp |
| TIP-7 | Skill: gộp `use_skill`/market/zip của upstream với skill pack AI Native; giữ `load_skill`, `read_skill_resource` | TIP-2 | Bảy skill + mentor cài mặc định như cũ; `use_skill` đọc được resource pack |
| TIP-8 | Docker/CI: `COPY skills-pack`, cài `bubblewrap` cho `run_code`, CI chạy trên `i18n-vi`, tắt `desktop.yml`, giữ CI 3 job | TIP-1 | `docker build` + smoke `/api/bootstrap` PASS; workflow lint OK |
| TIP-9 | Docs + bàn giao: version 0.12.0, CHANGELOG VI, `docs/cap-nhat-tu-upstream.md` mục v0.12, ARCHITECTURE, STATE, BOARD (OSA-021), log | tất cả | `unslop-vi` scan; link tương đối không gãy |

## 5. VERIFY dự kiến

- `uv sync --locked`, `compileall`, `import osa.server`, `osa.catalog`, `osa.templates`, `osa.i18n`, `pytest -q` (test upstream + 12 file remake), `skillpacks verify-sources`, `cd web && npm ci && npm test && npm run build`, `git diff --check`, scan secret trên diff.
- Preview trên sandbox (`data/live`, model `:free` đã duyệt): chat, tạo Bot qua card, routine/sự kiện không gửi ra ngoài, applet, trang Quan sát hiện USD, đổi VI/EN/ZH; ảnh 375/1440.
- Migration trên **bản sao** DB, không đụng DB thật.
- `NOT_CHECKED` nếu không chạy: Docker Computer E2E, channel thật, vẽ ảnh trả phí.
- VERIFY REPORT 5 mục + Retro Rubric `data/vibecode/OSA-021/`.

## 6. Rủi ro chính

1. Bỏ sót sửa riêng khi thay nền. Chặn bằng 12 file test remake + bảng provenance từng file.
2. ~800 khóa dịch mới; dịch máy sai ngữ cảnh. Soát theo màn hình, dùng `unslop-vi` cho câu dài.
3. Prompt Trung lọt sang model. Chặn bằng `test_prompt_language`.
4. Chi phí chia hai lần khi có cả `llm_usage` và `llm_calls`. Chặn bằng test migration với cờ đơn vị.
5. Đường webhook mới `/hooks/<key>` bỏ qua `host_ok`. Review riêng trong TIP-5.
6. `run_code` trong Docker cần `bwrap`; thiếu thì phải báo không chạy, không fallback host shell.
7. PR lớn khó review: một PR nhiều commit theo TIP, mô tả có bảng provenance.

## 7. Câu hỏi cần chốt (RRI)

1. Chọn chiến lược A hay B?
2. Tính năng có rủi ro hoặc chi phí: bật hay tắt mặc định — plugin Python, applet, MCP Apps, sự kiện qua `/hooks/<key>`, card link (server tải trang ngoài), vẽ ảnh?
3. Giữ hay bỏ `desktop/`, `mobile/` trong cây remake?
4. Kiểm live dùng model `:free` Experiential như hiện tại là đủ?
5. Ai merge và có muốn tách nhiều PR (nền+module, i18n, prompt, USD) không?
