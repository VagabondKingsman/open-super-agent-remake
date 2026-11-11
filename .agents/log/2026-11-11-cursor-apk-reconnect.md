# Phiên 2026-11-11 · cursor · nút kết nối lại trên APK

- Royan duyệt plan: cạnh chấm đỏ trên APK có nút Kết nối lại.
- Base `2fe3e47` (merge PR #53).
- Skill Flow: osa-dev → ai-work-method → vibecode-kit.

## Đã làm

- Chấm đỏ là `connected === false`, socket `/ws` đóng. Trang vẫn còn.
- Nút chỉ khi `desktop.platform === 'android'` và chấm đỏ.
- Bấm: hủy lịch chờ, đóng socket cũ, mở socket ngay. 8 giây. Đang thử thì bấm tiếp bị bỏ.
- Xong: "Đã kết nối lại", chấm xanh. Thất bại: "Vẫn không nối được server", chấm đỏ, rồi lịch 1,5 giây đến 30 giây chạy lại.
- Dòng thông báo tự mất sau 2,5 giây. Không gọi `webview.navigate`.

## Evidence

| AC | Kết quả | Bằng chứng |
|---|---|---|
| Lịch chờ bị lần mới thay | PASS | `web/tests/ws-reconnect.cjs`, `npm test` 44/44 |
| en/vi thiếu 0 | PASS | `python -m osa.i18n` exit 0. Frontend 1234 câu, thiếu 0 |
| Typecheck | PASS | `tsc --noEmit` exit 0 |

- Paid usage: 0. Chưa deploy, nên APK đang mở server cũ chưa có nút. Không build APK mới.
