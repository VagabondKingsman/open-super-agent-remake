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


@pytest.fixture
def fast_idle(monkeypatch):
    monkeypatch.setitem(CFG, "limits", {**CFG["limits"], "stream_idle_s": 0.2, "stream_retries": 1})


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


async def test_stall_every_time_gives_up_after_retries(fast_idle):
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
    monkeypatch.setitem(CFG, "limits", {**CFG["limits"], "stream_idle_s": 0.2, "stream_retries": 0})
    client = Client(STALL, OK)
    with pytest.raises(providers.StreamStalled):
        await _reply(9305, client)
    assert client.calls == 1


def test_idle_limit_shorter_than_watchdog():
    """Watchdog 3 分钟没进展就取消任务；流的空闲上限必须更短，重来才有机会。"""
    assert 0 < providers.stream_idle_s() < 180


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
