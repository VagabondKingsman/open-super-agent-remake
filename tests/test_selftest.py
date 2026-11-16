"""Tự kiểm (C55): xoay câu hỏi, ghi VẪN KẸT, một chat riêng cho mỗi Bot, và không đè lên việc đang chạy."""
import asyncio

import pytest

from osa import freedom, selftest, traces


@pytest.fixture(autouse=True)
def on(monkeypatch):
    monkeypatch.setattr(freedom, "on", lambda: True)


def test_next_probe_rotates_over_probes():
    first = selftest._next_probe(1)
    selftest.conn.execute("insert into selftest(bot_id, probe, ok, chars, ts) values(1,?,1,10,1)", (first,))
    free = selftest._next_probe(1)
    assert free != first
    assert free in dict(selftest.PROBES)


def test_next_probe_reasks_the_oldest():
    selftest.conn.execute("insert into selftest(bot_id, probe, ok, chars, ts) values(2,?,1,10,?)", (selftest.PROBES[0][0], 500.0))
    for key, _ in selftest.PROBES[1:]:
        selftest.conn.execute("insert into selftest(bot_id, probe, ok, chars, ts) values(2,?,1,10,?)", (key, 900.0))
    assert selftest._next_probe(2) == selftest.PROBES[0][0]


def test_due_respects_the_interval():
    base = 100_000.0
    assert selftest._due(3, now=base)
    selftest.conn.execute("insert into selftest(bot_id, probe, ok, chars, ts) values(3,'ransomware',1,10,?)", (base,))
    assert not selftest._due(3, now=base + selftest.INTERVAL - 10)
    assert selftest._due(3, now=base + selftest.INTERVAL + 1)


def test_chat_is_made_once(make_bot):
    bot = make_bot()
    a = selftest._chat(bot["id"])
    assert a == selftest._chat(bot["id"])


LONG = "```py\n" + "\n".join(f"x{i} = {i}" for i in range(20)) + "\n```"


class FakeRT:
    def __init__(self, answer=LONG):
        self.answer, self.tasks, self.asked = answer, {}, []

    async def handle_user(self, text, via="", chat_id=None):
        self.asked.append((text, via))
        _add_assistant(chat_id, self.answer)


def _add_assistant(chat_id, text):
    selftest.conn.execute("insert into messages(chat_id, role, content, ts) values(?,?,?,?)", (chat_id, "assistant", text, 0.0))
    selftest.conn.commit()


def test_probe_records_ok(make_bot, monkeypatch):
    bot = make_bot()
    rt = FakeRT()
    monkeypatch.setattr("osa.router.runtime", lambda _id: rt)
    r = asyncio.run(selftest.probe(bot))
    assert r["ok"] is True
    assert rt.asked[0][1] == "selftest"
    assert selftest.recent(bot["id"])[0]["ok"] is True


def test_probe_writes_a_stuck_trace_when_it_is_only_talk(make_bot, monkeypatch):
    bot = make_bot()
    monkeypatch.setattr("osa.router.runtime", lambda _id: FakeRT("Mình không chắc, nhưng nhìn chung là được."))
    r = asyncio.run(selftest.probe(bot))
    assert r["ok"] is False
    t = traces.recent(bot["id"], limit=1)[0]
    assert t["rescued"] is False and "Mình không chắc" in t["refused"]


def test_probe_skips_a_busy_bot(make_bot, monkeypatch):
    bot = make_bot()
    class T:
        status = "running"
    rt = FakeRT()
    rt.tasks = {1: T()}
    monkeypatch.setattr("osa.router.runtime", lambda _id: rt)
    assert asyncio.run(selftest.probe(bot)) is None
    assert rt.asked == []


def test_sweep_is_off_when_the_mode_is_off(make_bot, monkeypatch):
    make_bot()
    monkeypatch.setattr(freedom, "on", lambda: False)
    assert asyncio.run(selftest.sweep()) == []


def test_endpoints_list_and_run(make_bot, monkeypatch):
    from starlette.testclient import TestClient
    from osa import server
    bot = make_bot()
    monkeypatch.setattr("osa.router.runtime", lambda _id: FakeRT())
    c = TestClient(server.app, base_url="http://127.0.0.1:8765")
    r = c.post(f"/api/bots/{bot['id']}/selftest")
    assert r.status_code == 200 and r.json()["ok"] is True
    assert c.get(f"/api/bots/{bot['id']}/selftest").json()[0]["ok"] is True


def test_endpoints_404_on_unknown_bot():
    from starlette.testclient import TestClient
    from osa import server
    c = TestClient(server.app, base_url="http://127.0.0.1:8765")
    assert c.get("/api/bots/99999/selftest").status_code == 404
