# Vì sao event loop OSA đứng 672 giây (2026-11-14 09:38:44 → 09:49:57)

Read-only, một agent đọc log + DB. Không tool nào chạy trong khoảng trống: dòng cuối là header 200 của lượt model kế tiếp (task #1610), dòng kế là `GET /v1/machines` sau 672 giây. Access log uvicorn và WebSocket cùng tắt (người dùng phải tải lại trang); không restart, không crash (lần start kế 17:33). `llm_calls` hết hàng #2582 lúc 09:38:39; prompt-dump cuối 09:38:42.959, kế 11:34:29 ⇒ không lần nào quay lại `create_chat`. Hạn chờ 60 giây không bắn, Watchdog 900 giây bắn trễ 68 giây ⇒ mọi timer asyncio chết, tức thread loop đứng chứ không phải stream chậm.

## Nghi vấn và đã vá (PR #103)

- **fsync trên loop**: `tasklog.start/update/save` commit SQLite ngay trên thread loop; connection dùng chung, `journal_mode=delete`, `synchronous=FULL` (`osa/memory.py:22` trước khi sửa). Nay WAL + NORMAL.
- **`_bounded` chỉ xét `done`**: loop sống lại mà task vừa kịp xong thì coi như không quá hạn, nên đúng lượt treo đó không retry gì. Nay so cả giờ thật, quá hạn là `StreamStalled` + đóng stream.

## Chưa chốt

Không một file nào trên máy đổi mtime trong 09:39–09:49 (find trên /home/boxes, /var/log, /tmp = 0) ⇒ nghi cả máy hoặc cả tiến trình bị treo ngoài code (fsync toàn cục / hypervisor), không chỉ một hàm chặn. `dmesg` trên box này chỉ còn vòng đệm từ 02:34 hôm sau nên mất bằng chứng kernel; `journalctl -k` cho khoảng đó rỗng. Máy chỉ có **4 nhân** và load trung bình thường xuyên 20 khi chạy thử/buid — thiếu CPU cũng là một nguồn.

`looplag` (`osa/looplag.py`, `limits.loop_lag_s` 5) đã bật trên live; lần sau loop chậm quá 5 giây sẽ có WARNING + stack toàn bộ thread: đọc stack ở thread chính là biết trong `sqlite3_step`/`fsync` (lỗi của ta) hay trong `epoll` (máy treo).
