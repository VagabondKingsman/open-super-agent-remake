"""Router 每轮发给模型的内容：前面的部分要逐字不变，才能命中模型服务的缓存。"""
import re

from conftest import until
from osa import bots, memories, memory, router, server
from osa.config import CFG


async def test_system_prompt_and_history_stay_identical(llm, events, make_bot):
    a = make_bot("Cachy")
    chat = bots.chat(a["chat_id"])
    for i, text in enumerate(["你好", "今天有什么安排", "帮我记一下"], 1):
        llm.script("router:Cachy", f"第 {i} 次回复")
        await server.safe_handle(chat, text)
        await until(lambda: len(llm.bodies("router", "Cachy")) == i, what=f"第 {i} 轮")
        memories.log_work(a["id"], 1000 + i, f"做过的第 {i} 件事")   # 状态在变：下一轮“最近做过的事”不一样

    b1, b2, b3 = [b["messages"] for b in llm.bodies("router", "Cachy")]
    assert b1[0] == b2[0] == b3[0]                       # 系统提示词逐字不变
    assert "做过的第" not in b3[0]["content"]
    assert "做过的第 2 件事" in b3[-1]["content"]          # 变的部分附在最新一条消息后面
    assert b3[-1]["content"].startswith("帮我记一下")
    assert "system-attached current state" in b3[-1]["content"]
    assert b3[:len(b2) - 1] == b2[:-1]                   # 上一轮发过的历史（除了它最新那条）原样是这一轮的前缀


def test_state_goes_after_last_user_message():
    state = "\n\n(system-attached current state)"
    hist = [{"role": "user", "content": "你好"}]
    assert router.with_state(hist, state) == [{"role": "user", "content": "你好" + state}]
    assert hist == [{"role": "user", "content": "你好"}]   # 不改原来的列表
    hist = [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "嗨"}]
    assert router.with_state(hist, state)[-1] == {"role": "user", "content": state.lstrip()}


def test_history_window_moves_in_batches(make_bot, monkeypatch):
    monkeypatch.setitem(CFG["memory"], "inline_messages", 4)
    a = make_bot("Windowy")
    cid = a["chat_id"]
    prev = None
    for i in range(1, 13):
        memory.add("user", f"消息 {i}", cid, a["id"])
        ctx = memory.context(cid)
        kept = [m for m in ctx if m["role"] == "user"]
        assert 4 <= len(kept) <= 7 or i < 4
        if i in (4, 8, 12):       # 每满 4 条才挪一次
            assert kept[0]["content"] == f"消息 {i - 3}"
        elif prev is not None:    # 没挪：上一次的内容原样是这一次的前缀
            assert ctx[:len(prev)] == prev
        prev = ctx
    assert ctx[0]["role"] == "system" and "#" in ctx[0]["content"]   # 移出的只留编号和开头


async def test_state_block_carries_the_server_clock(llm, events, make_bot):
    """C12：模型说时间只能来自这一行或本轮的某个工具。它附在每轮的状态里，所以系统提示词照样逐字不变。"""
    a = make_bot("Clocky")
    llm.script("router:Clocky", "ok")
    await server.safe_handle(bots.chat(a["chat_id"]), "mấy giờ rồi")
    await until(lambda: llm.bodies("router", "Clocky"), what="请求")
    body = llm.bodies("router", "Clocky")[-1]
    state = body["messages"][-1]["content"]
    assert re.search(r"Now: \d{4}-\d\d-\d\d \d\d:\d\d:\d\dZ \(server clock, UTC\)", state), state[-400:]
    assert "Now:" not in body["messages"][0]["content"]      # 缓存的前缀里没有会变的东西


async def test_removed_index_rides_in_the_state_not_the_head(llm, events, make_bot, monkeypatch):
    """C13: “更早的对话”的索引每轮都在长。它要是留在 history 的第一条，缓存从那里就断了：
    实测一轮的第一次调用只命中 6%，而同一个 body 不改能命中 99%。"""
    monkeypatch.setitem(CFG["memory"], "inline_messages", 4)
    a = make_bot("Indexy")
    for i in range(6):
        llm.script("router:Indexy", f"回 {i}")
        await server.safe_handle(bots.chat(a["chat_id"]), f"第 {i} 条")
    body = llm.bodies("router", "Indexy")[-1]["messages"]
    assert body[0]["role"] == "system"
    assert "Earlier turns were removed from context" not in body[0]["content"]
    assert all(m["role"] != "system" for m in body[1:]), "history 开头不该再有 system 通知"
    assert "Earlier turns were removed from context" in body[-1]["content"]   # 索引在最后一条里
    assert body[-1]["content"].startswith("第 5 条")


async def test_each_turn_extends_the_previous_body(llm, events, make_bot, monkeypatch):
    """C14: 这一轮的正文要整段包住上一轮的正文（逐字），缓存才会命中 —— 供应商认的是“延长”，
    不是“前缀大致相同”。状态跟着它那条用户消息一起存下来，就是为此。"""
    monkeypatch.setitem(CFG["memory"], "inline_messages", 4)
    a = make_bot("Prefixy")
    for i in range(6):
        llm.script("router:Prefixy", f"答 {i}")
        await server.safe_handle(bots.chat(a["chat_id"]), f"问 {i}")
    bodies = [b["messages"] for b in llm.bodies("router", "Prefixy")]
    a1, a2 = bodies[4], bodies[5]          # 第 5、6 轮：窗口的分界（每隔 n 条才挪一次）这两轮没挪
    assert a2[:len(a1)] == a1              # 上一轮的正文原样是这一轮的开头
    assert "system-attached" in a1[-1]["content"]     # 状态挂在它那条用户消息上
    assert a1[-1]["content"].startswith("问 4")
    assert a2[len(a1) - 1] == a1[-1]                   # 下一轮里那条消息一字不差地还在


async def test_stored_state_is_not_overwritten_on_a_second_wake(make_bot):
    """同一条用户消息又醒一次（定时任务、回信）：留着当时发出去的那份，否则前缀就断了。"""
    a = make_bot("Wakey")
    cid = a["chat_id"]
    memory.conn.execute("insert into messages(ts, role, content, meta, chat_id, bot_id) values(?,?,?,?,?,?)",
                        (0, "user", "一条", "{}", cid, a["id"]))
    memory.conn.commit()
    memory.remember_state(cid, "STATE A")
    memory.remember_state(cid, "STATE B")
    body = memory.context(cid, me=a["id"])
    assert body[-1]["content"].endswith("STATE A")


async def test_a_tool_turn_chains_into_the_next_turn(llm, events, make_bot, monkeypatch):
    """C15: 带工具的一轮也要把“上一轮发出去的正文”原样留给下一轮 —— assistant 的 tool_calls 和 tool 结果
    都记在那条用户消息上（memory.keep_tail），否则下一轮的前缀断在工具往返处，17k 全部重算。"""
    from fakellm import Call
    monkeypatch.setitem(CFG["memory"], "inline_messages", 4)
    a = make_bot("Chainy")
    llm.script(f"router:{a['name']}", Call("quick_code", {"code": "print(7)"}), "答 0")
    await server.safe_handle(bots.chat(a["chat_id"]), "问 0")
    llm.script(f"router:{a['name']}", "答 1")
    await server.safe_handle(bots.chat(a["chat_id"]), "问 1")
    bodies = [b["messages"] for b in llm.bodies("router", a["name"])]
    tool_body = next(b for b in bodies if any(m.get("tool_calls") for m in b))
    assert any(m["role"] == "tool" for m in tool_body), "这一轮应该有工具往返"
    assert bodies[-1][:len(tool_body)] == tool_body   # 上一轮发过的整段（含工具往返）原样是这一轮的开头
