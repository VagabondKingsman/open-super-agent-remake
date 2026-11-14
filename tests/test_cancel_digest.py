"""取消任务时，卡片里要带上取消前做到的事：只写“已取消”会把做过的事一起埋掉。"""
from osa import router, tasklog


def test_cancel_text_lists_what_was_done(monkeypatch):
    monkeypatch.setattr(tasklog, "tail", lambda tid, n=5: ["Terminal: ls -la", "Chụp màn hình"])
    text = router._cancel_text(1610, "Watchdog：900 秒没有进展")
    assert text.startswith("[任务 #1610 已取消：")
    assert "取消前做到：" in text
    assert "- Terminal: ls -la" in text and "- Chụp màn hình" in text


def test_cancel_text_without_steps_is_just_the_reason(monkeypatch):
    monkeypatch.setattr(tasklog, "tail", lambda tid, n=5: [])
    text = router._cancel_text(1610, "Watchdog：900 秒没有进展")
    assert text == "[任务 #1610 已取消：Watchdog：900 秒没有进展]"


def test_tail_returns_finished_tools_in_order():
    from osa.memory import conn
    conn.execute("insert into task_steps(task_id, ts, kind, title, status) values(99001, 0, 'tool', 'a', 'done')")
    conn.execute("insert into task_steps(task_id, ts, kind, title, status) values(99001, 1, 'tool', 'b', 'running')")
    conn.execute("insert into task_steps(task_id, ts, kind, title, status) values(99001, 2, 'tool', 'c', 'done')")
    conn.execute("insert into task_steps(task_id, ts, kind, title, status) values(99001, 3, 'tool', 'd', 'done')")
    conn.commit()
    assert tasklog.tail(99001, n=5) == ["a", "c", "d"]   # cũ → mới, bỏ cái đang chạy
    assert tasklog.tail(99001, n=2) == ["c", "d"]
