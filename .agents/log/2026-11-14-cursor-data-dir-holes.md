# Phiên 2026-11-14 · cursor · bịt lớp lỗi thư mục dữ liệu (OSA-040, OSA-041)

- Bắt đầu/kết thúc: 11:23 → 13:00 Asia/Saigon
- Repo/base/branch: `VagabondKingsman/open-super-agent-remake`, base `i18n-vi`; nhánh `fix/child-env-data-dir` (PR #95, head `ac92a7e`) và `fix/data-dir-holes` (PR #96, head `13bfaa5`)
- Approval/scope: operator yêu cầu “fix lỗi 3”, “rá soát các thư mục khác”, rồi “plan deep fix các vấn đề còn hở”. Không đụng `main`, không release, không đổi tag.

## Chuyện đã xảy ra

1. **`<repo>/data` là kho thứ hai (PR #95).** Bot một lần đọc nhầm DB 1 bot trong đó. Đo thì ra gốc: `osa/host.py::_env()` lọc **mọi** biến `^OSA_`, nên mọi terminal/sandbox của Bot chạy `import osa` mà không có `OSA_DATA_DIR` — và `tests/conftest.py` cũng chưa hề đặt biến, nên test tự lớn kho đó.
2. **Vá:** `KEEP_FOR_CHILD = {OSA_DATA_DIR}`, conftest trỏ vào thư mục tạm, test chạy thật một lệnh terminal. Trước khi xoá: so từng tệp, 5 skill pack chỉ có trong `data/` được chép sang `osa-data/skill-packs/ai-native/` (Bot sau đó liệt kê đủ 14 pack), backup nguyên thư mục ở `osa-backups/`, rồi mới xoá.
3. **Rà tiếp thì thấy cùng một lớp lỗi còn ba chỗ** — nên không dừng ở #95: `config.py` vẫn rơi về `data/` khi thiếu env, `relay.py` tự ghi `repo/data/relay.db`, `worker_cache.py` mặc định đường của riêng box này, `dump_prompt` không có trần (300 MB / 2 381 tệp trong một ngày), backup của `net-fast.sh` nằm trong chính thư mục dữ liệu.
4. **OSA-041 / PR #96** bịt cả bốn: `.env` là nấc giữa (`.env` systemd vốn đã dùng, `OSA_DOTENV=0` tắt, `OSA_DOTENV=<path>` cho test), nấc cuối cảnh báo; relay và worker_cache theo cùng nguồn; dump có trần kích thước + số tệp; backup ra `osa-backups/`.

## Evidence

| Việc | Bằng chứng |
|---|---|
| Gốc lỗi | `osa/host.py:348` lọc `^OSA_`; bot mở `data/osa.db` trong log; index FTS của DB repo 288 KB |
| Kho thật | `/proc/<pid>/environ` → `OSA_DATA_DIR=/home/boxes/osa-data` |
| Sau khi vá (#96) | `env -u OSA_DATA_DIR python -c "from osa import config, memory"` → `DATA=/home/boxes/osa-data`, `<repo>/data` không được tạo |
| Test | #95: 1258 passed, 1 skipped · #96: **1263 passed, 3 skipped**, evals 37/37, i18n 缺 0/缺 0 |
| CI | #95: backend/docker/frontend pass, CLEAN · #96: frontend, docker pass, backend chạy |
| Sao lưu trước khi xoá | `osa-data/backup-repo-data-20261114.tar.gz` → đã chuyển sang `/home/boxes/osa-backups/` |

## Rà phần còn lại — đã kiểm, chưa vá

- **Task #1610 bị mất lượt:** 14 bước đều `done` tới 09:38, nhưng câu trả lời cuối không tới; Watchdog huỷ 09:54 sau 900 giây không tiến triển. Cùng với `gmail-reg-watchdog` (đang tắt, blocker lặp 3 lần ở cross-flow QR của Google) là hai việc mở.
- **Không có logrotate** cho `osa-data/logs/osa.log` (systemd append mãi; 3 MB hiện tại, ~4 MB/ngày khi máy chạy thực).
- **`osa-tailnet.service` tồn tại hai bản**: bản system đang enabled+active, bản user `disabled` — cùng kiểu bẫy với cặp `osa.service` cũ.
- **5 script cầm cứng `/home/boxes/osa-data`** (`ask.py`, `probe_run.py`, `scenario_from_log.py`, heredoc unit trong `net-fast.sh`, docstring `worker_cache.py`) — máy khác là đọc sai DB.
- `osa-data/start.out` là rác của một lần chạy cũ (PID 1133003), không script nào ghi nữa.
- Đã kiểm và **không** phải lỗi: media có gc 1 ngày theo `meta.attachments` (19 ảnh “mồ côi” là ảnh trong ngày); `overrides` chỉ đè `EDITABLE_LIMITS` nên `config.yaml` không hề cũ; model cứu hộ `dolphin-mistral-24b-venice-edition` trả lời được; một listener, `NRestarts=0`, lần restart 11:34Z là restart sạch; tailnet serve chỉ trong tailnet.
