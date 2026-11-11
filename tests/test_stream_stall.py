"""流开了之后卡住或断了（task #253：xAI 的流 3 分钟没有新块，Watchdog 把 8 分钟的任务取消了）：同一轮重来一次。"""
import asyncio

import httpx
import openai
import pytest
from conftest import find, settle
from osa import bots, memory, providers, server, tasklog, worker
from osa.config import CFG
from osa.worker import Task


class Delta:
    def __init__(self, content=None, reasoning=None):
        self.content, self.reasoning_content, self.tool_calls = content, reasoning, None


class Chunk:
    def __init__(self, delta, finish=None):
        self.usage = None
        self.choices = [type("Choice", (), {"delta": delta, "finish_reason": finish})()]


class Stream:
    """chunks 里的 'hang' 表示从这里开始不再出块，Exception 表示流中途报错。"""
    def __init__(self, chunks):
        self.chunks, self.closed = chunks, False

    def __aiter__(self):
        return self._go()

    async def _go(self):
        for c in self.chunks:
            if c == "hang":
                await asyncio.Event().wait()
            if isinstance(c, tuple) and c[0] == "sleep":   # 这一块之前停一会儿
                await asyncio.sleep(c[1])
                continue
            if isinstance(c, Exception):
                raise c
            yield c

    async def close(self):
        self.closed = True


class Client:
    def __init__(self, *plans):
        self.plans, self.calls, self.streams = list(plans), 0, []
        self.chat = type("Chat", (), {})()
        self.chat.completions = type("Completions", (), {})()
        self.chat.completions.create = self._create

    async def _create(self, **kwargs):
        plan = self.plans[min(self.calls, len(self.plans) - 1)]
        self.calls += 1
        s = Stream(plan)
        self.streams.append(s)
        return s


OK = [Chunk(Delta(content="xong")), Chunk(Delta(), "stop")]
STALL = [Chunk(Delta(reasoning="đang nghĩ")), "hang"]


def _capacity():
    return openai.APIError("The model is currently at capacity due to high demand.",
                           httpx.Request("POST", "https://api.example/v1/chat/completions"), body=None)


PAUSES: list = []


@pytest.fixture
def fast_idle(monkeypatch):
    monkeypatch.setitem(CFG, "limits", {**CFG["limits"], "stream_idle_s": 0.2, "stream_first_chunk_s": 0.6,
                                         "stream_retries": 1})
    PAUSES.clear()

    async def no_wait(attempt):
        PAUSES.append(attempt)
    monkeypatch.setattr(providers, "retry_pause", no_wait)


async def _reply(task_id, client):
    task = Task(id=task_id, goal="g", bot_id=1, chat_id=1)
    log = tasklog.Log(task)
    msg = await worker._reply(task, log, "worker", client, "fake-model", [{"role": "user", "content": "q"}])
    return task, msg


async def test_stalled_stream_retried_once_and_task_goes_on(fast_idle):
    client = Client(STALL, OK)
    task, msg = await _reply(9301, client)
    assert msg["content"] == "xong" and client.calls == 2
    assert client.streams[0].closed   # 卡住的流被关掉，不留着连接
    steps = tasklog.steps(9301)
    assert [s["status"] for s in steps if s["kind"] == "think"] == ["error"]
    notes = [s for s in steps if s["kind"] == "note"]
    assert len(notes) == 1 and notes[0]["status"] == "error"
    err = memory.conn.execute("select err from llm_calls where task_id=9301 and err is not null").fetchall()
    assert len(err) == 1


def no_fallback(monkeypatch, role: str):
    """这个角色不配备用模型：只看原来的重试行为。"""
    monkeypatch.setitem(CFG["roles"], role, {k: v for k, v in CFG["roles"][role].items() if k != "fallback"})


async def test_stall_every_time_gives_up_after_retries(fast_idle, monkeypatch):
    no_fallback(monkeypatch, "worker")
    client = Client(STALL)
    with pytest.raises(providers.StreamStalled):
        await _reply(9302, client)
    assert client.calls == 2


async def test_capacity_error_mid_stream_retried(fast_idle):
    client = Client([Chunk(Delta(content="nửa")), _capacity()], OK)
    _, msg = await _reply(9303, client)
    assert msg["content"] == "xong" and client.calls == 2


async def test_quota_error_mid_stream_not_retried(fast_idle):
    quota = openai.APIError("insufficient_quota: out of credits",
                            httpx.Request("POST", "https://api.example/v1/chat/completions"), body=None)
    client = Client([quota], OK)
    with pytest.raises(openai.APIError):
        await _reply(9304, client)
    assert client.calls == 1


async def test_retries_zero_keeps_old_behaviour(monkeypatch):
    no_fallback(monkeypatch, "worker")
    monkeypatch.setitem(CFG, "limits", {**CFG["limits"], "stream_idle_s": 0.2, "stream_first_chunk_s": 0.2,
                                         "stream_retries": 0})
    client = Client(STALL, OK)
    with pytest.raises(providers.StreamStalled):
        await _reply(9305, client)
    assert client.calls == 1


def test_idle_limit_shorter_than_watchdog():
    """Watchdog 3 分钟没进展就取消任务；流的空闲上限、第一块的上限都必须更短，重来才有机会。"""
    assert 0 < providers.stream_idle_s() < 180
    assert providers.stream_idle_s() <= providers.stream_first_chunk_s() < 180


# F1：想得久的模型第一块来得慢，不算卡住；第一块之后才按 stream_idle_s 算
async def test_slow_first_chunk_within_first_limit_is_not_a_stall(fast_idle):
    client = Client([("sleep", 0.4), Chunk(Delta(content="xong")), Chunk(Delta(), "stop")])
    _, msg = await _reply(9306, client)
    assert msg["content"] == "xong" and client.calls == 1 and PAUSES == []


async def test_first_chunk_never_comes_is_a_stall(fast_idle):
    client = Client(["hang"], OK)
    _, msg = await _reply(9307, client)
    assert msg["content"] == "xong" and client.calls == 2 and client.streams[0].closed


async def test_mid_stream_gap_uses_idle_limit_not_first_limit(fast_idle):
    # 第一块之后停 0.4 秒：比第一块的上限（0.6）短，但比两块之间的上限（0.2）长，算卡住
    client = Client([Chunk(Delta(reasoning="a")), ("sleep", 0.4), Chunk(Delta(content="muộn")), Chunk(Delta(), "stop")], OK)
    _, msg = await _reply(9308, client)
    assert msg["content"] == "xong" and client.calls == 2


async def test_guard_stream_explicit_limits():
    s = Stream([("sleep", 0.15), Chunk(Delta(content="x")), ("sleep", 0.15), Chunk(Delta(content="y"))])
    got = [c async for c in providers.guard_stream(s, idle_s=0.3, first_s=0.3)]
    assert len(got) == 2
    s = Stream([Chunk(Delta(content="x")), ("sleep", 0.3), Chunk(Delta(content="y"))])
    with pytest.raises(providers.StreamStalled):
        [c async for c in providers.guard_stream(s, idle_s=0.1, first_s=5)]


# F3：重来之前等一会儿（2–5 秒，带随机）
async def test_worker_retry_waits_before_calling_again(fast_idle):
    client = Client(STALL, OK)
    await _reply(9309, client)
    assert PAUSES == [1]


def test_retry_delay_between_2_and_5_seconds():
    for attempt in (1, 2, 3, 10):
        for _ in range(50):
            d = providers.stream_retry_delay(attempt)
            assert 2.0 <= d <= 5.0


async def test_retry_pause_uses_delay(monkeypatch):
    waited = []

    async def fake_sleep(s):
        waited.append(s)
    monkeypatch.setattr(providers.asyncio, "sleep", fake_sleep)
    await providers.retry_pause(1)
    assert len(waited) == 1 and 2.0 <= waited[0] <= 3.0


# C9：主模型连着卡住、重来也没用，就换 roles.<role>.fallback 的备用模型把这一轮做完，而不是让任务失败
def _backup_provider(monkeypatch, role: str, model: str):
    """给这个角色配一个备用模型，走一个单独的假服务，好分辨请求落到哪个模型上。"""
    monkeypatch.setitem(CFG["providers"], "backup", {"base_url": "http://backup.llm/v1", "api_key_env": "BACKUP_KEY"})
    monkeypatch.setitem(CFG["roles"], role, {**CFG["roles"][role], "fallback": {"provider": "backup", "model": model}})


async def test_worker_stalls_twice_then_backup_model_finishes_the_round(fast_idle, monkeypatch):
    _backup_provider(monkeypatch, "worker", "backup-model")
    main, backup = Client(STALL), Client(OK)
    monkeypatch.setattr(providers, "client", lambda name, timeout=None: backup if name == "backup" else main)
    task, msg = await _reply(9311, main)
    assert msg["content"] == "xong" and main.calls == 2 and backup.calls == 1
    ok = [r[0] for r in memory.conn.execute("select model from llm_calls where task_id=9311 and err is null")]
    assert "backup-model" in ok   # 用量记在真正答话的那个模型上
    notes = [s["title"] for s in tasklog.steps(9311) if s["kind"] == "note"]
    assert len(notes) == 2 and "backup-model" in notes[-1]


async def test_backup_model_stalling_too_gives_up(fast_idle, monkeypatch):
    _backup_provider(monkeypatch, "worker", "backup-model")
    main, backup = Client(STALL), Client(STALL)
    monkeypatch.setattr(providers, "client", lambda name, timeout=None: backup if name == "backup" else main)
    with pytest.raises(providers.StreamStalled):
        await _reply(9312, main)
    assert main.calls == 2 and backup.calls == 1   # 备用模型只试一次，不跟着无限重来


async def test_fallback_equal_to_primary_is_ignored(fast_idle, monkeypatch):
    monkeypatch.setitem(CFG["roles"], "worker", {**CFG["roles"]["worker"], "fallback": {"model": "fake-model"}})
    client = Client(STALL)
    with pytest.raises(providers.StreamStalled):
        await _reply(9313, client)
    assert client.calls == 2


# F2：作废那一次的用量也要记
async def test_worker_failed_attempt_usage_is_recorded(fast_idle):
    client = Client([Chunk(Delta(reasoning="nghĩ rất nhiều " * 20)), "hang"], OK)
    await _reply(9310, client)
    rows = memory.conn.execute("select output, estimated from llm_calls where task_id=9310 and err is null").fetchall()
    assert any(r[1] == 1 and r[0] > 0 for r in rows)


def test_retry_classification():
    req = httpx.Request("POST", "https://x/v1")
    assert providers.retry_midstream(providers.StreamStalled("x"))
    assert providers.retry_midstream(openai.APIConnectionError(request=req))
    assert providers.retry_midstream(_capacity())
    assert not providers.retry_midstream(providers.ProviderLimit("quota", 402, "", ""))
    assert not providers.retry_midstream(ValueError("bad"))
    bad = openai.BadRequestError("bad", response=httpx.Response(400, request=req), body=None)
    assert not providers.retry_midstream(bad)


async def test_router_stall_before_any_text_is_retried(fast_idle, monkeypatch, events, make_bot):
    client = Client(STALL, [Chunk(Delta(content="Chào bạn")), Chunk(Delta(), "stop")])
    monkeypatch.setattr(providers, "client", lambda name, timeout=None: client)
    b = make_bot("Stally")
    await server.safe_handle(bots.chat(b["chat_id"]), "chào")
    await settle()
    assert client.calls == 2
    assert find(b["chat_id"], role="assistant", text="Chào bạn")
    assert not [e for e in events.of("error") if e.get("chat_id") == b["chat_id"]]


async def test_router_does_not_retry_after_text_was_shown(fast_idle, monkeypatch, events, make_bot):
    client = Client([Chunk(Delta(content="Một nửa câu")), _capacity()], [Chunk(Delta(content="khác")), Chunk(Delta(), "stop")])
    monkeypatch.setattr(providers, "client", lambda name, timeout=None: client)
    b = make_bot("Halfy")
    await server.safe_handle(bots.chat(b["chat_id"]), "chào")
    await settle()
    assert client.calls == 1   # 正文已经推到界面上，重来会重复，所以照旧报错


async def test_router_retry_resets_shown_thinking_and_records_usage(fast_idle, monkeypatch, events, make_bot):
    before = memory.conn.execute("select count(*) from llm_calls where role='router' and estimated=1").fetchone()[0]
    client = Client([Chunk(Delta(reasoning="đang nghĩ " * 20)), "hang"],
                    [Chunk(Delta(reasoning="đang nghĩ")), Chunk(Delta(content="Chào lại")), Chunk(Delta(), "stop")])
    monkeypatch.setattr(providers, "client", lambda name, timeout=None: client)
    b = make_bot("Resetty")
    await server.safe_handle(bots.chat(b["chat_id"]), "chào")
    await settle()
    assert client.calls == 2 and PAUSES == [1]
    streams = [e for e in events.of("stream") if e.get("chat_id", b["chat_id"]) == b["chat_id"]]
    kinds = ["reset" if e.get("reset") else "thinking" if e.get("thinking") else "delta" for e in streams]
    i = kinds.index("reset")
    assert "thinking" in kinds[:i] and "thinking" in kinds[i + 1:]
    assert find(b["chat_id"], role="assistant", text="Chào lại")
    after = memory.conn.execute("select count(*) from llm_calls where role='router' and estimated=1").fetchone()[0]
    assert after == before + 1


def test_config_yaml_documents_stream_defaults(monkeypatch):
    """AUDIT-F9：config.yaml 里注释掉的三行和代码默认值一致。"""
    import re
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "config.yaml").read_text()
    got = {k: float(v) for k, v in re.findall(r"^  # (stream_\w+): (\d+)", text, re.M)}
    assert set(got) == {"stream_first_chunk_s", "stream_idle_s", "stream_retries"}
    monkeypatch.setitem(CFG, "limits", {k: v for k, v in CFG["limits"].items() if not k.startswith("stream_")})
    assert got == {"stream_first_chunk_s": providers.stream_first_chunk_s(), "stream_idle_s": providers.stream_idle_s(),
                   "stream_retries": providers.stream_retries()}


async def test_a_connection_that_never_opens_is_a_stall_not_a_hang(monkeypatch):
    """任务 212：连接卡住时 create_chat 一直等（客户端默认 600 秒），Watchdog 3 分钟就把任务取消，
    一个模型调用都没发出去。现在连接阶段也有上限，超了就是“流卡住”，可以重来、可以换备用模型。"""
    from types import SimpleNamespace
    monkeypatch.setitem(CFG["limits"], "provider_head_s", 0.05)

    async def slow(**kw):
        await asyncio.sleep(0.5)
        return "ok"

    client = SimpleNamespace(base_url="https://example.invalid/v1",
                             chat=SimpleNamespace(completions=SimpleNamespace(create=slow)))
    with pytest.raises(providers.StreamStalled) as e:
        await providers.create_chat(client, model="m", messages=[], stream=True)
    assert providers.retry_midstream(e.value) is True          # 值得重来

    # 非流式请求不受这个上限约束：整段回答本来就要等
    assert await providers.create_chat(client, model="m", messages=[]) == "ok"


async def test_reply_retries_a_connection_that_never_opened(monkeypatch):
    """_reply 把“连接没建起来”当成这一轮没成：重来一次，成了就把任务做完，不留给 Watchdog 取消。"""
    from types import SimpleNamespace
    monkeypatch.setitem(CFG["limits"], "provider_head_s", 0.05)
    calls = []

    async def create(**kw):
        calls.append(1)
        if len(calls) == 1:
            await asyncio.sleep(0.5)          # 第一次连接卡住
        return Stream([Chunk(Delta(content="好的"))])

    client = SimpleNamespace(base_url="https://example.invalid/v1",
                             chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    task = Task(id=9001, goal="x", mode="single", bot_id=1, chat_id=1, approval_chat_id=1)
    log = tasklog.Log(task, "probe")
    msg = await worker._reply(task, log, "worker", client, "m", [{"role": "user", "content": "hi"}])
    assert len(calls) == 2 and (msg.get("content") or "").startswith("好的")
