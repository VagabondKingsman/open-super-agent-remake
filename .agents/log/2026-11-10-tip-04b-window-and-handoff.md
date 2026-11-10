# Phiên 2026-11-10 · cursor · TIP-04b và bàn giao sau PR #35

- Bắt đầu/kết thúc: 10/11/2026 16:22–17:05 Asia/Saigon (UTC+7).
- Repo: `VagabondKingsman/open-super-agent-remake`. `origin/i18n-vi` = `90d820c` (merge [PR #35](https://github.com/VagabondKingsman/open-super-agent-remake/pull/35), giờ commit merge 16:23:51). Tree của `90d820c` trùng `e5d9f5a` (head PR #35).
- Branch local `fix/tip-04b-window-handoff` tách từ `90d820c`. Commit fix `5e20f83` (cherry-pick từ `b9fdaa7`), cộng commit docs của phiên này. Box không push được lên GitHub. Patch nằm ở `/workspace/osa-pr35-update/` trên box vận hành, cloud agent sẽ đẩy và mở PR.
- Approval: Tin Tin giao cài bản mới nhất vào OSAR đang chạy, test E2E live bản fix (cho phép gọi xAI trả phí và dùng Instabox), sửa cửa sổ task, làm cho suite pass, viết handoff và docs.
- Skill Flow: osa-dev → ai-work-method → vibecode-kit. Prose qua unslop-vi.

## Trình tự đã làm

1. Cài: `git fetch origin`. Khi đó PR #35 chưa merge, `origin/fix/e2e-audit-b1-b6` = `e5d9f5a` đã gộp `i18n-vi` sau PR #34. Checkout nhánh local `verify/e2e-fix-20261110` tại `e5d9f5a`. Stash `config.yaml` rồi trả lại. Backup DB trước khi restart.
2. Build frontend (`npm ci`, `npm run build`) vì server phục vụ `osa/static/dist`. Restart bằng `scripts/osa-stop.sh && scripts/osa-start.sh`.
3. Test live bản fix B1–B6 trên Instabox, 16:25–16:35.
4. Ảnh trang vẫn 500 × 136 dù màn hình VM là 1920 × 1080. Cửa sổ task là 510 × 267. Giả thuyết cũ (màn hình dọc 425 × 1601 do VNC) sai. Sửa TIP-04b, restart, test lại 16:39–16:46.
5. Tìm hai test bị skip bằng `pytest -rs`. Sửa một, giữ skip một.
6. Fetch lại: PR #35 đã merge vào `i18n-vi`. Tách nhánh mới từ `90d820c`, cherry-pick fix TIP-04b, viết docs và handoff.

## TIP-04b: cách sửa

- `osa/computer/base.py` `_win()` / `_size()`: với backend không phải `host`/`linked`, gửi `size` = `computer.width` × `computer.height` (mặc định 1280 × 800), không lớn hơn màn hình thật (`self.width`, `self.height`; Instabox đọc bằng `xdpyinfo`).
- `osa/computer/cdp_helper.py` `Ctx.fit()`: mỗi lần chọn cửa sổ cho task hoặc chat, đọc `Browser.getWindowBounds`. Cửa sổ ở trạng thái `normal` mà rộng hoặc cao dưới 90% kích thước đó thì `Browser.setWindowBounds` lên kích thước đó, rồi chờ 0,3 giây. Cửa sổ `minimized` được đưa về `normal` trước. `maximized`/`fullscreen` giữ nguyên. Chạy cả với cửa sổ đã mở, nên VM đang chạy không cần máy mới.
- Helper trên VM có tên theo SHA-1 nội dung (`/tmp/osa-cdp-<hash>.py`), nên restart OSA là VM dùng bản mới.

## Evidence

| AC | Kết quả | Bằng chứng |
|---|---|---|
| B2 · PUT `reasoning_effort` = `ultra` | PASS. 400, "Mức suy nghĩ chỉ được là: low, medium, high, xhigh, max" | `b2-effort.txt` |
| B2 · models/test reviewer `grok-4.7` effort `max` | PASS. ok, `effort_rejected: max` | `b2-effort.txt` |
| B6 · models/test `grok-4.20-0309-reasoning` worker `high` | PASS. ok, `effort_rejected: high` | `b2-effort.txt` |
| B1 · dispatch thật có `meta.tasks` | PASS. Tin 210, 221, 229, 234 | DB chat 4, 7, 8 |
| B1 · nhắc id task có thật không bị gắn cờ | PASS. Tin 224 nhắc #220 | chat 7 |
| B1 · đường bịa dispatch live | NOT_CHECKED. Hai lượt "ok" trong chat 8 không tái hiện. Unit test phủ | chat 8 |
| B3 · Heavy 2 bản nháp (#209) | PASS. done, reviewer trả 906 ký tự gộp đủ ý | `b3-task209.json` |
| B5 · lead tự handoff (#220) | PASS lần 2. Lần 1 cơ chế chạy nhưng xAI báo "at capacity" giữa stream | chat 7, `b5-capacity-error.log` |
| B4 · `computer_screenshot` `screen: true` (#233) | PASS. 1920 × 1080 | `b4-screen.png` |
| TIP-04b · ảnh trang | PASS. Trước 500 × 136 (#233), sau 1270 × 669 (#238 và gọi trực tiếp) | `b4-page.png`, `b4b-page.png`, `b4b-dims.txt` |
| TIP-04b · cửa sổ trên VM | PASS. Cửa sổ task 510 × 267 → 1280 × 800, không tạo máy mới | `b4b-geometry-before.txt`, `b4b-geometry-after.txt` |
| pytest toàn bộ | PASS. `819 passed, 1 skipped` | log lệnh |
| Frontend | PASS. `tsc --noEmit` exit 0, `npm test` 34/34, `phone-platform.cjs` 1/1 | `b0-*.txt` |

Bằng chứng nằm trên box vận hành, thư mục `osa-e2e-fix-verify-20261110/`, không đưa vào git (có ảnh chụp màn hình và dữ liệu chat).

- Test bị skip:
  - `tests/test_host_computer.py::test_real_chrome` trước đây cần `OSA_TEST_CHROME=1`. Khi bật thì fail vì conftest tắt `computer.enabled`. Test vẫn tự bật cho chính nó. Tự chạy trên máy local khi có Chrome (`OSA_TEST_CHROME=0` để bỏ), và bị bỏ trên CI trừ khi `OSA_TEST_CHROME=1`. Lần chạy trên box: PASS.
  - `tests/test_host_desktop.py::test_real_desktop` chỉ chạy trên macOS, điều khiển chuột và bàn phím thật. Linux không chạy được. BLOCKED, giữ skip.
- Chi phí live: usage.today.cost $7,048106 → $7,447328, tức $0,399 cho cả hai đợt (B1–B6 $0,344, TIP-04b $0,055). Đây là số OSA ghi nhận, không phải hóa đơn xAI.
- Secrets: không ghi key, mật khẩu, link VNC/sshx/Tailscale. Quét thư mục bằng chứng không thấy key.
- Trạng thái: commit local, chờ cloud agent đẩy và mở PR.

## Còn mở / next step

- B1: đường model bịa dispatch chỉ có unit test. Thông báo đưa lại vào ngữ cảnh vẫn ghi "that task never existed" kể cả khi lượt sửa đã giao task thật. Chưa sửa.
- Lỗi provider giữa stream (xAI "at capacity") không được thử lại. `create_chat` chỉ thử lại lỗi lúc gửi request. Lượt được đánh thức bị mất.
- Router hiểu "ok, giao luôn đi" thành task #228 có bước xóa cookie và cache Chromium dùng chung. Đã hủy task khi nó mới liệt kê thư mục.
- Dòng reset chủ đề lưu "[新话题]" dù UI tiếng Việt.
- Filter live path NOT_CHECKED.
- Android: `cargo test` NOT_CHECKED (box có rustc 1.85.1, deps cần 1.87). APK NOT_CHECKED (không có Android SDK).
- `GET /shot` trả 409 trên Instabox. Đây là hành vi đã biết (Instabox dùng live view), không phải regression.
- `config.yaml` trên box có `computer.idle_pause_s: 2592000` cho keepalive Instabox. Không commit.
