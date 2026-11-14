# OSA-041 · Plan bịt các lỗ còn hở quanh thư mục dữ liệu

Soạn 14/11/2026 19:10 Asia/Saigon, sau PR #95. Trạng thái: **PLAN**. Người soạn: phiên cursor-agent.

Bối cảnh: PR #95 vá đúng một lỗ (biến môi trường bị lọc nên tiến trình con ghi vào `<repo>/data`). Khi rà để vá, thấy **cùng một lớp lỗi còn ba chỗ khác**, và bản thân dữ liệu vẫn tự sinh trong thư mục dữ liệu. Plan này bịt lớp lỗi, không chỉ bịt một hiện tượng.

## 1. SCAN — bằng chứng

| # | Chỗ | Hiện tượng |
|---|---|---|
| H1 | `osa/config.py:11,18` | `OSA_DATA_DIR` vắng thì `DATA = ROOT / "data"`; mọi lần `import osa` chạy tay (python -c, script, pytest không qua conftest) **tạo lại** `data/` trong repo. Chính comment `tests/conftest.py:29` ghi "không set thì config.DATA rơi vào data/ của code". |
| H2 | `osa/relay.py:39` | `DB_PATH` mặc định `repo/data/relay.db`, **không** đọc `OSA_DATA_DIR`; bật relay trên box này là ghi vào repo dù đã có data dir. |
| H3 | `scripts/worker_cache.py:19` | `os.environ.get("OSA_DATA_DIR", "/home/boxes/osa-data")` — mặc định là đường dẫn của riêng box này; máy khác chạy là đọc DB sai. |
| H4 | `scripts/net-fast.sh:15` | `BK="$H/osa-data/net-backup-$STAMP"` — bản sao lưu nằm **trong** thư mục dữ liệu; `osa-data/net-backup-20261111-014649/` và `backup-repo-data-20261114.tar.gz` đang nằm đó. Sao lưu thư mục dữ liệu là **tự bao chính nó**. |
| H5 | `osa/providers.py:291 dump_prompt` | Không có trần: mỗi request một tệp `.json`, 24 giờ sinh 300 MB / 2 381 tệp (đã cắt tay về 500). Bật lâu dài là đầy đĩa. |

Không có lỗ nào làm hỏng dữ liệu; cả năm đều là **đường dẫn và dung lượng**, tức là loại lỗi chỉ lộ ra sau vài ngày.

## 2. QUYẾT ĐỊNH

- **D1 (H1, H2, H3) một nguồn sự thật cho thư mục dữ liệu.** `config.py` giữ nguyên thứ tự ưu tiên `OSA_DATA_DIR` → `<repo>/.env` → `ROOT/data`, và khi rơi xuống nấc cuối thì **ghi một dòng cảnh báo** nêu đường dẫn, để nó không bao giờ im lặng. Đọc `.env` theo đúng quy ước đã có ở `scripts/osa-start.sh` (`OSA_DOTENV=0` để tắt), chỉ đọc từ `ROOT`, không phụ thuộc cwd. `.env` là chính tệp systemd đang dùng, nên không thêm nguồn mới.
  - Hệ quả tốt: `python -c "import osa"` chạy tay đi đúng kho thật thay vì đẻ kho thứ hai.
  - An toàn cho test: `conftest.py` đặt `OSA_DATA_DIR` **trước** khi import osa nên env vẫn thắng `.env`.
- **D2 (H4) sao lưu ra ngoài.** `net-fast.sh` ghi vào `$H/osa-backups/`; chuyển hai hiện vật đang có ra đó; ghi quy ước vào `.agents/OPS.md`.
- **D3 (H5) trần cho dump.** `dump_prompt` sau khi ghi thì dọn còn **N tệp mới nhất** (mặc định 500, `OSA_PROMPT_DUMP_KEEP`, 0 = không giới hạn) và **bỏ qua** body lớn hơn `OSA_PROMPT_DUMP_MAX_MB` (mặc định 4). Ghi hỏng vẫn không được làm hỏng request (giữ nguyên `try/except`).
- **D4** mỗi quyết định có test riêng; không đổi hành vi mặc định nào ngoài cảnh báo.

## 3. BUILD — thứ tự

1. `osa/config.py`: hàm `_env_data_dir()` (env → `.env` → `ROOT/data` + cảnh báo). `relay.py:39` dùng cùng nấc `OSA_DATA_DIR`.
2. `tests/test_data_dir.py`: thêm `test_hand_run_follows_the_env_file` (probe không có env, có `.env` tạm → dùng kho đó, `ROOT/data` vẫn sạch), `test_env_file_can_be_switched_off` (`OSA_DOTENV=0` → hành vi cũ), `test_relay_db_follows_the_data_dir`.
3. `dump_prompt`: trần + test `test_prompt_dump_keeps_only_the_newest` và `test_prompt_dump_skips_a_huge_body`.
4. `scripts/net-fast.sh` + `scripts/worker_cache.py` + `.agents/OPS.md`; chuyển hiện vật sao lưu ra `osa-backups/`.
5. Chạy `ruff`, `pytest -q` toàn bộ ở nhánh riêng, PR vào `i18n-vi`.

## 4. RỦI RO VÀ CÁCH CHẶN

| Rủi ro | Chặn |
|---|---|
| `.env` cũ trỏ kho đã xoá → mọi lệnh tay đi vào kho ma | Chỉ dùng khi thư mục **tồn tại**; không thì cảnh báo và rơi về `ROOT/data` |
| pytest lỡ đọc DB thật qua `.env` | `conftest.py` đặt env trước import; có test khẳng định `TMP` được dùng |
| Dọn dump xoá nhầm tệp người dùng trỏ vào | Chỉ dọn trong thư mục dump, chỉ `*.json` do chính nó đặt tên, và chỉ khi `KEEP > 0` |
| Người dùng coi `ROOT/data` là chỗ chính đáng (cài mới, chưa có `.env`) | Nấc cuối **giữ nguyên** hành vi, chỉ thêm cảnh báo |

## 5. NGHIỆM THU

- Máy này: chạy `python -c "import osa.memory"` **không** env → không sinh `<repo>/data`.
- `osa/relay.py` với `OSA_DATA_DIR` đặt → DB nằm trong đó.
- Dump 600 request với `KEEP=500` → đúng 500 tệp.
- Toàn bộ test xanh, CI xanh, không đổi `config.yaml` lẫn hợp đồng API.
