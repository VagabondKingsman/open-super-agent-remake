"""C4：一轮花得比平时多一倍就不再调工具，用手上的资料回答（meta.cost_guard 记下来）。"""
import json
import time

import pytest
from conftest import find, settle
from fakellm import Call
from osa import bots, memory, router, server


def _reply(cost: float, ts: float | None = None, role="assistant", chat_id=9701):
    memory.conn.execute("insert into messages(ts, role, content, meta, chat_id) values(?,?,?,?,?)",
                        (ts or time.time(), role, "x", json.dumps({"usage": {"cost": cost, "in": 1, "out": 1}}),
                         chat_id))
    memory.conn.commit()


def test_the_cap_is_a_multiple_of_the_usual_reply_of_the_last_week():
    assert memory.turn_cost_cap(least=1000) is None          # 样本太少：不管
    tag = time.time()
    for i in range(10):
        _reply(0.01, ts=time.time() - 3600 - i, chat_id=9702)
    cap, usual, n = memory.turn_cost_cap(factor=3, least=8)
    assert cap == pytest.approx(usual * 3) and n >= 10
    assert 0.027 <= cap <= 0.05          # 中位数里混着别的测试记的回复

    old = time.time() - 30 * 86400
    for i in range(10):
        _reply(1.0, ts=old - i, chat_id=9703)                # 一个月前贵得多：不算进 7 天
    assert memory.turn_cost_cap(least=8)[0] < 0.2

    assert memory.turn_cost_cap(factor=0) is None           # 0 = 关掉
    assert tag


def test_one_runaway_reply_does_not_loosen_the_guard():
    """C7：基准取中位数，所以跑飞的那一条自己抬不高护栏。
    线上 14 条回复：中位数 $0.0418，最大 $0.179 —— 平均数会被贵的那几条拉走：
    混进一条 $2 的，7 天平均从 $0.04 涨到 $0.19，2× 平均的护栏就从 $0.08 跑到 $0.38。"""
    now, chat = time.time(), 9704
    for i in range(11):
        _reply(0.04, ts=now - 600 - i, chat_id=chat)
    memory._cap_cache = None                                 # 一分钟的缓存：插了新回复要重算
    before, _, n_before = memory.turn_cost_cap(factor=3, least=8)
    _reply(2.0, ts=now - 60, chat_id=chat)                   # 一条跑飞的
    memory._cap_cache = None
    after, usual, n_after = memory.turn_cost_cap(factor=3, least=8)
    assert n_after == n_before + 1 and usual <= 0.05
    assert abs(after - before) <= before * 0.2               # 中位数几乎不动
    # 同一堆数字，换成平均数：一条就够把“平均”顶到中位数护栏之上
    assert (0.04 * 11 + 2.0) / 12 > before


async def test_an_expensive_turn_stops_calling_tools(llm, make_bot, monkeypatch):
    bot = make_bot("Saver")
    monkeypatch.setitem(router.CFG["limits"], "turn_cost_guard", 2.0)
    # 假模型没有价目，这一轮的费用是 0：把上限压到 0 以下，任何一轮都算超
    monkeypatch.setattr(memory, "turn_cost_cap", lambda **kw: (-0.5, -1.0, 10))
    llm.script("router:Saver", Call("remember", {"text": "ba ý chính"}), "Mình trả lời luôn: X, Y, Z.")

    await server.safe_handle(bots.chat(bot["chat_id"]), "tìm ba ý chính")
    await settle()

    first, second = llm.bodies("router", "Saver")[-2:]
    assert first.get("tools")                      # 第一轮有工具，用了 remember
    assert not second.get("tools")                 # 超了以后：不再给工具
    assert "more than 2x the usual" in second["messages"][-1]["content"]
    [reply] = find(bot["chat_id"], role="assistant", text="X, Y, Z")
    assert reply["meta"]["cost_guard"]["cap"] == -0.5
    assert reply["meta"]["cost_guard"]["turns"] == 10


async def test_a_turn_of_usual_cost_keeps_its_tools(llm, make_bot, monkeypatch):
    bot = make_bot("Normal")
    monkeypatch.setitem(router.CFG["limits"], "turn_cost_guard", 2.0)
    monkeypatch.setattr(memory, "turn_cost_cap", lambda **kw: (10.0, 5.0, 10))    # 一比就便宜
    llm.script("router:Normal", Call("remember", {"text": "một"}), Call("remember", {"text": "hai"}), "xong")

    await server.safe_handle(bots.chat(bot["chat_id"]), "làm hai việc")
    await settle()

    bodies = llm.bodies("router", "Normal")
    assert len(bodies) == 3 and all("tools" in b for b in bodies)   # 每一轮都还能调工具
    [reply] = find(bot["chat_id"], role="assistant", text="xong")
    assert "cost_guard" not in reply["meta"]


async def test_the_guard_can_be_switched_off(llm, make_bot, monkeypatch):
    bot = make_bot("Spender")
    monkeypatch.setitem(router.CFG["limits"], "turn_cost_guard", 0)     # 0 = 关掉
    llm.script("router:Spender", Call("remember", {"text": "một"}), Call("remember", {"text": "hai"}), "xong")

    await server.safe_handle(bots.chat(bot["chat_id"]), "việc")
    await settle()

    bodies = llm.bodies("router", "Spender")
    assert len(bodies) == 3 and all("tools" in b for b in bodies)
