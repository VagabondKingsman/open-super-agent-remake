---
name: self-build
description: >-
  Tự sửa chính mình: đọc mã OSA trong repo đã mount, tái hiện lỗi bằng test, sửa, chạy cả bộ, mở PR nhánh riêng. Dùng khi việc là "sửa OSA" chứ không phải "dùng OSA".
---

# self-build · sửa chính hệ thống đang chạy mình

Mục tiêu: thay đổi **có bằng chứng** và không làm sập chỗ đang chạy. Ba thứ không được đoán: lỗi, phạm vi, kết quả.

## 0. Đọc trước khi viết
- Repo ở `/data/repo` (mount từ máy chủ, `OSA_COMPUTER_MOUNTS`); trên máy này kho mã thật là `/home/boxes/osa`.
- `.agents/BOARD.md` là danh sách việc mở có người nhận — nhận một dòng, đừng mở việc thứ mười một.
- `.agents/OPS.md` nói máy này chạy thế nào (user unit, DB ngoài checkout, VM tự resume).

## 1. Tái hiện trước
- Viết test đỏ đúng chỗ hỏng, chạy riêng tệp đó: `.venv/bin/python -m pytest tests/test_x.py -q`.
- Test chạm `computer_shell` phải gọi `approvals.shell_confirmed(task_id)` trước, không là treo chờ thẻ.
- Không tái hiện được thì chưa sửa — chỉ ghi lại cách đo vào BOARD.

## 2. Sửa nhỏ, đúng một việc
- Nhánh riêng: `git switch -c fix/<việc> origin/i18n-vi`. **Không đẩy thẳng vào `i18n-vi`.**
- Đổi tên hàm trong `osa/`: grep lời gọi + test trước, giữ tên cũ làm alias mỏng.
- Thông báo cho người dùng đi qua `i18n.t`, và thêm câu vào `osa/locales/{en,vi}.json` — `python -m osa.i18n` phải ra `缺 0`.

## 3. Cửa
- `./scripts/test.sh` (tự bọc xvfb khi không có DISPLAY) — phải xanh cả bộ, không chỉ tệp vừa sửa.
- Frontend: `cd web && npm test && npx tsc --noEmit`.
- Commit message nói **vì sao** và **test nào**; `git commit -F -` với heredoc.

## 4. Đưa lên và chạy thật
- `gh pr create --base i18n-vi --head <nhánh>`; chờ ba check `backend`/`frontend`/`docker` xanh, kèm `mergeStateStatus` CLEAN.
- Merge xong mới đưa cây đang chạy lên bản đã merge rồi `systemctl --user restart osa`, và đo lại bằng chứng trên bản mới.
- `./scripts/test.sh` (~4 phút) là cửa duy nhất; không có nó thì thay đổi chỉ là đề xuất.

## 5. Học lại
- Một lượt bị model từ chối rồi được cứu sẽ tự ghi một dòng vào `## LEARNED SHAPES` của mình; dấu vết các lượt đó nằm trong bảng `traces` (xem `osa/selfreview.py`).
- Việc học không chỉ trông vào may: `osa/selftest.py` mỗi 12 tiếng tự hỏi một câu hard, và `POST /api/bots/<id>/selftest` chạy ngay một lượt. Xem lịch sử bằng `GET` cùng đường đó; một dòng `STUCK` trong log `/home/boxes/osa-data/logs/osa.log` là bài học sắp được viết.
- Sửa xong một lỗi lặp lại: hoặc là thêm một dòng bài học, hoặc thêm một test — đừng sửa cùng chỗ ba lần mà không để lại cái nào.

## Bẫy đã gặp
- Trong tiến trình, gọi provider phải `settings.apply()` trước, không thì key `xpl_` 401.
- Test gọi `settings.save()` phải trả lại overrides + CFG, không là các test sau mất thẻ duyệt (all-on không phát thẻ).
- `router.TASKS` khoá theo số tác vụ riêng; đối chiếu tin nhắn bằng `Task.msg_id` và `meta.task_id`.
