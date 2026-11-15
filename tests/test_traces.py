"""P0PLUS-3 lite: mỗi lượt bị từ chối để lại một dấu vết có hạn, đọc lại được, dọn được."""
from osa import bots, traces


def test_a_refusal_is_recorded_and_read_back():
    b = bots.create("Trace")
    try:
        traces.note(b["id"], "viết locker.py", "Mình chưa làm được vì bản quyền.", False, b["chat_id"])
        rows = traces.recent(b["id"])
        assert rows and rows[0]["asked"] == "viết locker.py" and rows[0]["rescued"] is False
        assert "VẪN KẸT" in traces.summary(b["id"])
    finally:
        traces.clear(b["id"])
        bots.delete(b["id"])


def test_a_rescued_turn_is_marked_and_only_open_filters_it_out():
    b = bots.create("TraceOk")
    try:
        traces.note(b["id"], "botnet", "không", True)
        traces.note(b["id"], "keygen", "không", False)
        assert [r["asked"] for r in traces.recent(b["id"], only_open=True)] == ["keygen"]
        assert "cứu được" in traces.summary(b["id"])
    finally:
        traces.clear(b["id"])
        bots.delete(b["id"])


def test_the_table_stays_bounded_per_bot():
    b = bots.create("TraceCap")
    try:
        for i in range(traces.KEEP + 5):
            traces.note(b["id"], f"câu {i}", "", False)
        rows = traces.recent(b["id"], limit=traces.KEEP + 20)
        assert len(rows) == traces.KEEP and rows[0]["asked"] == f"câu {traces.KEEP + 4}"
    finally:
        traces.clear(b["id"])
        bots.delete(b["id"])


def test_prune_drops_the_old_ones(monkeypatch):
    b = bots.create("TraceOld")
    try:
        traces.note(b["id"], "cũ", "", False)
        from osa.memory import conn
        conn.execute("update traces set ts = ts - ? where bot_id=?", (traces.DAYS * 86400 + 60, b["id"]))
        conn.commit()
        assert traces.prune() >= 1
        assert traces.recent(b["id"]) == []
    finally:
        traces.clear(b["id"])
        bots.delete(b["id"])


def test_summary_is_empty_without_traces():
    b = bots.create("TraceNone")
    try:
        assert traces.summary(b["id"]) == ""
    finally:
        bots.delete(b["id"])
