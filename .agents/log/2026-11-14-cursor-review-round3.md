# Phiên 2026-11-14 · cursor · rà soát sau vòng 2 (OSA-043)

- Bắt đầu/kết thúc: 21:20 → 22:35 Asia/Saigon
- Repo/base: `VagabondKingsman/open-super-agent-remake`, base `i18n-vi`
- Approval/scope: tiếp câu “plan deep fix các vấn đề còn hở … sau đó rà soát các vấn đề còn lại”. Không đụng `main`, không release.

## Vào phiên

Ba PR của vòng trước còn mở và chồng lên nhau (#95 ← #96 ← #97). Merge sai thứ tự sẽ mất phần đã làm, nên việc đầu tiên là hợp nhất theo chồng: #95 xong, #96 xung đột `CHANGELOG.md` — giữ cả hai mục, chạy lại toàn bộ (1270 passed), rồi merge; #97 đi kèm #96. Deploy: fast-forward checkout, restart user unit, pid đổi, manifest 200, bot trả lời.

## Đã làm (mỗi cái một PR)

1. **#98 — cửa chờ kết nối.** `provider_head_s` (120) canh “đã kết nối, chưa có header”, nhưng khi **không kết nối được** thì vẫn chờ đủ 120 giây: hai lần trong task 1632 đúng như vậy. Thêm `limits.provider_connect_s` (15) làm trần riêng cho TCP/TLS, và xếp `APIConnectionError` vào nhóm lỗi tạm thời (thử lại có backoff) thay vì để nó nổi lên trên.
2. **#99 — đường dẫn của riêng box này.** `install-logrotate.sh`, `tailnet-serve.sh` hết viết cứng `/home/boxes`; `net-fast.sh` suy ra repo/home/user từ vị trí script và chủ thư mục, và chỉ giữ 10 bản backup. `tailnet-serve.sh` chọn daemon theo **socket trả lời được** chứ không theo uid: chạy bằng user trước đây rơi vào socket userspace đã chết, đo được 0/90 lần đọc status rồi timeout 120 giây; sau khi sửa exit 0 trong vài giây. `.agents/OPS.md` viết lại theo box thật (user unit, DB ngoài checkout, VM tự resume), các hạn mức stream về đúng 60/60.
3. **#100 — “0 giây”.** `Chat.tsx` làm tròn về giây ngay nên mọi ngưỡng dưới 0,5 giây hiện “0 giây”; dưới 10 giây in một chữ số thập phân.

## Đã quyết trên dữ liệu sống

- `daily-brief` (routine 1) **bật lại**, hẹn 09:00 hằng ngày. Web search kiểm được trước khi bật: trả 2 023 ký tự.
- `gmail-reg-watchdog` (routine 3) **để tắt**, lý do ghi thẳng vào prompt của routine: Google chặn ở bước cross-device/SMS, máy không có `SMS_API_KEY`, không có `/dev/kvm`.
- VM Instabox đang `paused` → `Computer.start()` tự `resume`, đo được `running`, nên không cần script giữ VM.
- BOARD: OSA-016 (live routine) và OSA-020 (config USD) → Done kèm bằng chứng; E2E-OPEN bỏ mục “0 giây”.

## Evidence

| Việc | Bằng chứng |
|---|---|
| #96 hợp nhất, không mất phần nào | 1270 passed sau khi giữ cả hai mục changelog; CI backend 14m57s pass, mergeState CLEAN |
| Cửa chờ kết nối | `providers._default_timeout()` cho `connect=15.0, read=600`; 3 test mới; gọi thật tới deepseek thấy 401 từ server (đi được) |
| tailnet-serve.sh theo socket | trước: `0/90` đọc được, exit 124 ở 120s; sau: `tailscale=Running serve=on`, exit 0, `public-url.txt` đúng hostname |
| Dọn backup | thư mục giả 14 bản → còn 10 |
| Deploy | pid 3309452 → 161384, `/manifest.json` 200, 7 thread (có looplag), bot trả lời một câu thật |

## Còn hở

- `logrotate` **chưa cài** (cần root): `sudo /home/boxes/osa/scripts/install-logrotate.sh`. Trước khi cài, log append vẫn lớn dần (`osa.log` 3,0 MB).
- Nguyên nhân cú chặn event loop 11 phút hôm trước vẫn chưa biết; `looplag` đã bật và sẽ in stack lần tới.
- OSA-001/002/007/017/018/019 vẫn chờ Tin Tin (duyệt model, máy có Docker, điện thoại, người đọc bản `vi:`).
