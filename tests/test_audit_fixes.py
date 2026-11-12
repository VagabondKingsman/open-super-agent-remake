"""OSA-009: hồi quy cho B01–B07. Chỉ fake provider và DB tạm, không gọi LLM trả phí."""
import asyncio
import json
import time

import pytest

from conftest import find, until
from fakellm import Call, StreamReply
from osa import approvals, i18n, library, mcp_hub, memory, registry, routines, search, server, tasklog
from osa.config import CFG
from osa import worker
from osa.worker import Task


def _usage_rows(task_id: int):
    return memory.conn.execute(
        "select cache_hit, cache_miss, output, estimated from llm_calls where task_id=? order by ts",
        (task_id,)).fetchall()


async def _dispatch(llm, bot, goal: str, ack: str = "đã giao"):
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": goal}), ack)
    await server.safe_handle(bots_chat(bot), goal)
    return await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả task")


def bots_chat(bot):
    from osa import bots
    return bots.chat(bot["chat_id"])


async def test_b01_empty_length_is_not_done(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Length")
    llm.script("worker",
               StreamReply(content="", reasoning="chỉ suy nghĩ", finish="length"),
               StreamReply(content="", reasoning="vẫn trống", finish="length"))
    result = await _dispatch(llm, bot, "chứng minh số nguyên tố")
    assert result[0]["meta"]["status"] == "failed"
    assert "Mô hình không đưa ra câu trả lời" in result[0]["content"]
    assert result[0]["content"].strip() != "[Kết quả tác vụ #" + str(result[0]["meta"]["task_id"]) + "]"


async def test_b01_length_then_real_answer_is_done(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Retry")
    llm.script("worker", StreamReply(content="", reasoning="nháp", finish="length"), "PRIME_OK")
    result = await _dispatch(llm, bot, "trả lời ngắn")
    assert result[0]["meta"]["status"] == "done"
    assert "PRIME_OK" in result[0]["content"]


async def test_b01_truncated_text_is_not_done(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "en")
    bot = make_bot("Cut")
    llm.script("worker",
               StreamReply(content="half", finish="length"),
               StreamReply(content="still half", finish="length"))
    result = await _dispatch(llm, bot, "write a long proof")
    assert result[0]["meta"]["status"] == "failed"
    assert "still half" in result[0]["content"]
    assert "can't count as finished" in result[0]["content"]


async def test_b01_router_empty_length_is_not_a_blank_success(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("RouterEmpty")
    llm.script("router:RouterEmpty",
               StreamReply(content="", reasoning="hmm", finish="length"),
               StreamReply(content="", finish="length"))
    await server.safe_handle(bots_chat(bot), "chào")
    await until(lambda: find(bot["chat_id"], role="assistant"), what="reply router")
    text = find(bot["chat_id"], role="assistant")[-1]["content"]
    assert text == "Không có câu trả lời"
    assert text.strip()


async def test_b02_repeated_tool_stops_and_page_write_is_visible(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Drift")
    same = Call("search_memory", {"query": "sentinel-osa009"})
    llm.script("worker", [same, same, same], "LOOP_DONE")
    result = await _dispatch(llm, bot, "chỉ trả lời LOOP_DONE, không tìm gì")
    assert result[0]["meta"]["status"] == "done"
    assert "LOOP_DONE" in result[0]["content"]
    steps = tasklog.steps(result[0]["meta"]["task_id"])
    tools = [s for s in steps if s["kind"] == "tool"]
    assert len(tools) == 3
    assert tools[-1]["status"] == "error"
    assert "bị bỏ qua" in tools[-1]["body"]
    assert sum(1 for s in tools if s["status"] == "done") == 2


async def test_b02_save_page_is_a_visible_side_effect(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Page")
    llm.script("worker", Call("save_page", {"title": "Ngoai le", "content": "khong nam trong goal"}), "xong viec")
    result = await _dispatch(llm, bot, "chỉ trả lời xong viec")
    assert "xong viec" in result[0]["content"]
    assert "Tác vụ này còn sửa thư viện" in result[0]["content"]
    assert memory.conn.execute("select count(*) from pages where title='Ngoai le'").fetchone()[0] == 1
    dispatch = find(bot["chat_id"], kind="dispatch")[-1]
    assert dispatch["meta"].get("side_effects")


async def test_b02_quiet_run_still_shows_a_page_write(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("QuietPage")
    routine = routines.save(bot["id"], {"name": f"quiet-{bot['id']}", "prompt": "chỉ kiểm tra",
                                        "trigger": {"kind": "every", "minutes": 30}, "enabled": False})
    llm.script("worker", Call("save_page", {"title": "Quiet page", "content": "đã ghi"}), "[无新内容]")
    out = await routines.fire(routine, "schedule")
    assert out["accepted"]
    await until(lambda: routine["id"] not in routines.RUNNING, what="lịch chạy xong")
    result = find(bot["chat_id"], kind="result")
    assert result and "Quiet page" in result[0]["content"]
    assert routines.runs(routine["id"])[0]["status"] == "done"


async def test_b02_save_page_approval_can_block_the_write(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setitem(CFG["limits"], "save_page_approval", True)
    bot = make_bot("AskPage")
    llm.script("worker", Call("save_page", {"title": "Bi chan", "content": "no"}), "khong luu")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "lưu trang"}), "đã giao")
    await server.safe_handle(bots_chat(bot), "lưu trang")
    card = await until(lambda: [e for e in events.of("approval") if e.get("status") == "pending" and e.get("tool") == "save_page"],
                       what="thẻ xác nhận save_page")
    approvals.resolve(card[0]["id"], False, "đừng ghi")
    result = await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả sau khi từ chối")
    assert "khong luu" in result[0]["content"]
    assert "Tác vụ này còn sửa thư viện" not in result[0]["content"]
    assert memory.conn.execute("select count(*) from pages where title='Bi chan'").fetchone()[0] == 0


def test_b03_startup_reconciles_orphaned_routine_runs(make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Restart")
    routine = routines.save(bot["id"], {"name": f"osa009-{bot['id']}", "prompt": "ping",
                                        "trigger": {"kind": "every", "minutes": 30}, "enabled": False})
    now = time.time()
    memory.conn.execute(
        "insert into routine_runs(routine_id, ts, source, status, detail, finished) values(?,?,?,?,?,?)",
        (routine["id"], now, "schedule", "running", "", None))
    memory.conn.execute(
        "insert into routine_runs(routine_id, ts, source, status, detail, finished) values(?,?,?,?,?,?)",
        (routine["id"], now - 10, "schedule", "done", "giữ nguyên", now - 5))
    memory.conn.commit()
    tasklog.startup()
    rows = {r["status"]: r for r in routines.runs(routine["id"])}
    assert rows["interrupted"]["finished"]
    assert rows["interrupted"]["detail"] == i18n.t("服务重启，这次运行已中断")
    assert rows["done"]["detail"] == "giữ nguyên"
    assert rows["done"]["finished"] == now - 5


def test_b04_tool_text_and_worker_locale_hint(make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Locale")
    missing = library.tool_read_page({"page_id": 999999})
    assert missing == "Không có trang #999999"
    assert "没有页面" not in missing
    saved = library.tool_save_page(bot["id"], {"title": "", "content": ""})
    assert saved.startswith("Chưa lưu:")
    assert "没保存" not in saved
    task = Task(id=1, goal="g", bot_id=bot["id"], chat_id=bot["chat_id"])
    system = worker.worker_system(task, True)
    assert "Reply in Vietnamese" in system
    assert "必须用越南语" not in system
    assert "不要换成第三种语言" not in system


async def test_b04_search_and_unknown_tool_are_localized(make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "en")
    bot = make_bot("Search")
    text = await search.tool(bot["id"], {"query": "no-such-osa009-xyz"})
    assert text == "No matching memories or pages"
    task = Task(id=4242, goal="g", bot_id=bot["id"], chat_id=bot["chat_id"])
    log = tasklog.Log(task)
    step = await log.start("tool", "missing")

    async def progress(_):
        return None

    out, status = await worker._call_tool(task, log, step, "no_such_tool_osa009", "{}", progress,
                                           {"scope": registry.WORKER}, [])
    assert status == "error"
    assert out == "Unknown tool"


async def test_b05_ack_is_stored_before_the_result_and_localized(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Order")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "thời tiết"}), "Worker sẽ báo lại")
    llm.script("worker", "nắng")
    await server.safe_handle(bots_chat(bot), "thời tiết hôm nay")
    result = await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả")
    rows = memory.conn.execute(
        "select id, role, content, meta from messages where chat_id=? order by id", (bot["chat_id"],)).fetchall()
    ack_id = next(i for i, role, content, _meta in rows if role == "assistant" and "Worker sẽ báo lại" in (content or ""))
    result_id = next(i for i, role, _content, meta in rows
                     if role == "task" and json.loads(meta or "{}").get("kind") == "result")
    assert ack_id < result_id
    assert "nắng" in result[0]["content"]
    bodies = llm.bodies("router", "Order")
    tool_msgs = [m for m in bodies[-1]["messages"] if m["role"] == "tool"]
    assert tool_msgs and tool_msgs[0]["content"].startswith("Đã giao tác vụ #")
    assert "已派发" not in tool_msgs[0]["content"]


async def test_b06_mcp_is_error_marks_the_step_error(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")

    class Part:
        text = "Error executing tool expected_error"

    class Result:
        content = [Part()]
        isError = True

    text, is_error = mcp_hub._text(Result())
    assert is_error
    assert text == "Công cụ báo lỗi: Error executing tool expected_error"

    async def boom(**kwargs):
        raise mcp_hub.ToolResultError(text)

    # v0.12：MCP 工具挂在注册表上（mcp_hub.TOOLS 没了）。这里注册一个同样抛 ToolResultError 的 Worker 工具
    from osa import registry
    ctx = registry.Context("test-b06")
    ctx.simple("demo__expected_error", {"type": "function", "function": {"name": "demo__expected_error",
                                                                           "parameters": {"type": "object", "properties": {}}}},
               boom, where=frozenset({registry.WORKER}))
    task = Task(id=7706, goal="g", bot_id=1, chat_id=1)
    log = tasklog.Log(task)
    step = await log.start("tool", "demo__expected_error")

    async def progress(_):
        return None

    try:
        out, status = await worker._call_tool(task, log, step, "demo__expected_error", "{}", progress,
                                               {"scope": registry.WORKER}, [])
    finally:
        ctx.dispose()
    assert status == "error"
    assert "expected_error" in out
    await log.finish(step, status, out)
    assert tasklog.steps(task.id)[-1]["status"] == "error"


async def test_b07_cancel_records_estimate_or_real_usage():
    seen = asyncio.Event()

    class Fn:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class ToolCall:
        def __init__(self, name, arguments, index=0, id="call_0"):
            self.index = index
            self.id = id
            self.function = Fn(name, arguments)

    class Delta:
        def __init__(self, reasoning=None, content=None, tool_calls=None):
            self.reasoning_content = reasoning
            self.content = content
            self.tool_calls = tool_calls

    class Choice:
        def __init__(self, delta, finish=None):
            self.delta = delta
            self.finish_reason = finish

    class Chunk:
        def __init__(self, delta=None, usage=None, choices=True, finish=None):
            self.usage = usage
            self.choices = [Choice(delta or Delta(), finish)] if choices else []

    class Usage:
        def __init__(self):
            self.prompt_tokens = 8
            self.completion_tokens = 5
            self.prompt_cache_hit_tokens = 1

    class Stream:
        def __init__(self, chunks):
            self.chunks = chunks

        def __aiter__(self):
            return self._go()

        async def _go(self):
            for chunk in self.chunks:
                if chunk is None:
                    seen.set()
                    await asyncio.Event().wait()
                yield chunk

    class Client:
        def __init__(self, chunks):
            self.chat = type("Chat", (), {})()
            self.chat.completions = type("Completions", (), {})()
            self.chat.completions.create = self._create
            self._chunks = chunks

        async def _create(self, **kwargs):
            return Stream(self._chunks)

    async def cancelled(task_id, chunks):
        task = Task(id=task_id, goal="g", bot_id=1, chat_id=1)
        log = tasklog.Log(task)
        run = asyncio.create_task(worker._reply(task, log, "worker", Client(chunks), "fake-model",
                                                [{"role": "user", "content": "q"}]))
        await seen.wait()
        seen.clear()
        run.cancel()
        with pytest.raises(asyncio.CancelledError):
            await run
        return _usage_rows(task_id)

    estimated = await cancelled(9001, [Chunk(Delta(reasoning="abcd")), None])
    assert estimated == [(0, 0, memory.estimate_output_tokens("abcd"), 1)]

    recorded = await cancelled(9002, [Chunk(Delta(reasoning="abcd"), usage=Usage()), None])
    assert recorded == [(1, 7, 5, 0)]

    empty = await cancelled(9003, [None])
    assert empty == []

    args = "a" * 48
    tool_only = await cancelled(9004, [Chunk(Delta(tool_calls=[ToolCall("verify_facts", args)])), None])
    assert tool_only == [(0, 0, memory.estimate_output_tokens("verify_facts" + args), 1)]

    with_usage = await cancelled(9005, [Chunk(Delta(tool_calls=[ToolCall("verify_facts", args)]), usage=Usage()), None])
    assert with_usage == [(1, 7, 5, 0)]


async def test_r1_heavy_workers_keep_separate_repeat_history(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["limits"], "repeat_tool_limit", 3)
    bot = make_bot("Heavy")
    args = {"sums": [{"id": "sum", "values": [17, 25], "claimed_total": 42}]}

    def reply(body):
        if any(m.get("role") == "tool" for m in body["messages"]):
            return "HEAVY_DONE"
        return Call("verify_facts", args)

    llm.script("worker", *([reply] * 9))
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "mỗi người gọi verify_facts một lần", "mode": "heavy"}), "ack")
    await server.safe_handle(bots_chat(bot), "heavy")
    result = await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả heavy")
    assert result[0]["meta"]["status"] == "done"
    steps = [s for s in tasklog.steps(result[0]["meta"]["task_id"]) if s["kind"] == "tool"]
    by = {}
    for step in steps:
        by.setdefault(step["worker"], []).append(step)
    assert set(by) == {"h0", "h1", "h2"}
    for label, rows in by.items():
        assert len(rows) == 1, label
        assert rows[0]["title"] == "verify_facts" and rows[0]["status"] == "done"
        assert "bị bỏ qua" not in (rows[0]["body"] or "")


async def test_r2_blocked_batch_still_answers_every_tool_call(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setitem(CFG["limits"], "repeat_tool_limit", 3)
    bot = make_bot("Batch")
    seen = []
    real = search.tool

    async def wrapped(bot_id, args):
        seen.append(args)
        return await real(bot_id, args)

    monkeypatch.setattr(search, "tool", wrapped)
    same = Call("search_memory", {"query": "batch-osa009"})
    llm.script("worker", [same, same, same, same, same], "AFTER_BATCH")
    result = await _dispatch(llm, bot, "batch năm lần")
    assert "AFTER_BATCH" in result[0]["content"]
    assert len(seen) == 2
    follow = llm.bodies("worker")[1]["messages"]
    tools = [m for m in follow if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tools] == [f"call_{i}" for i in range(5)]
    assert all("bị bỏ qua" in m["content"] for m in tools[2:])
    statuses = [s["status"] for s in tasklog.steps(result[0]["meta"]["task_id"]) if s["kind"] == "tool"]
    assert statuses == ["done", "done", "error", "error", "error"]


async def test_r3_router_cancel_counts_tool_arguments(make_bot):
    from osa.router import Router

    seen = asyncio.Event()
    args = "b" * 48

    class Fn:
        def __init__(self, name, arguments):
            self.name, self.arguments = name, arguments

    class ToolCall:
        def __init__(self):
            self.index, self.id = 0, "call_0"
            self.function = Fn("verify_facts", args)

    class Delta:
        def __init__(self):
            self.reasoning_content = None
            self.content = None
            self.tool_calls = [ToolCall()]

    class Choice:
        def __init__(self):
            self.delta = Delta()
            self.finish_reason = None

    class Chunk:
        def __init__(self, hang=False, usage=None):
            self.usage = usage
            self.choices = [] if hang else [Choice()]
            self.hang = hang

    class Stream:
        def __aiter__(self):
            return self._go()

        async def _go(self):
            yield Chunk()
            seen.set()
            await asyncio.Event().wait()

    class Client:
        def __init__(self):
            self.chat = type("Chat", (), {})()
            self.chat.completions = type("Completions", (), {})()

        async def create(self, **kwargs):
            return Stream()

    client = Client()
    client.chat.completions.create = client.create
    bot = make_bot("RouteCancel")
    rt = Router(bot["id"])
    rt.chat = bots_chat(bot)
    run = asyncio.create_task(rt._stream(client, "router-tool-only", [{"role": "user", "content": "q"}], "sid", time.time()))
    await seen.wait()
    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run
    rows = memory.conn.execute(
        "select output, estimated from llm_calls where model=? order by ts", ("router-tool-only",)).fetchall()
    assert rows == [(memory.estimate_output_tokens("verify_facts" + args), 1)]



# C26: bị cắt vì độ dài, xin "câu trả lời đầy đủ" thì model thường kể lại từ đầu → một tin nhắn hai lần.
def test_c26_unrepeated_keeps_only_the_new_tail():
    from osa.router import _unrepeated
    a = "Ba việc vừa khép: Nova trả lời lại, demo khảo sát xong, hai số kiểm lại PASS."
    assert _unrepeated(a, a) == ""                       # 完全重复
    assert _unrepeated(a, a + " Đoạn tiếp theo.") == "Đoạn tiếp theo."
    assert _unrepeated(a, "Đoạn tiếp theo.") == "Đoạn tiếp theo."   # 没有重叠
    assert _unrepeated(a, "kiểm lại PASS. Đoạn tiếp theo.") == "Đoạn tiếp theo."   # 上一段结尾被重说了
    assert _unrepeated(a, "PASS. Đoạn tiếp.") == "PASS. Đoạn tiếp."   # 重叠太短，不算重复
    assert _unrepeated("", a) == a


async def test_c26_truncated_reask_lands_once(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Repeat")
    same = "Ba việc vừa khép: Nova trả lời lại, demo khảo sát xong, hai số kiểm lại PASS."
    llm.script(f"router:{bot['name']}", StreamReply(content=same, finish="length"),
               StreamReply(content=same, finish="stop"))
    await server.safe_handle(bots_chat(bot), "tóm tắt ba việc")
    await until(lambda: find(bot["chat_id"], role="assistant"), what="reply đã lặp")
    text = find(bot["chat_id"], role="assistant")[-1]["content"]
    assert text.count("Ba việc vừa khép") == 1
    assert text.strip() == same


def test_c26_call_kwargs_passes_max_tokens(monkeypatch):
    from osa.config import CFG, _spec_kwargs
    monkeypatch.setitem(CFG["roles"], "router", {**CFG["roles"]["router"], "max_tokens": 4096})
    assert _spec_kwargs(CFG["roles"]["router"])["max_tokens"] == 4096
    assert "max_tokens" not in _spec_kwargs({"model": "x"})   # 没配就不带，服务端的默认值照旧