"""假模型：按剧本流式返回文字或工具调用，走真的 AsyncOpenAI 客户端（请求经 httpx.MockTransport 送到这里）。

剧本按角色排队：router（还能细到某个 Bot：router:名字）、worker、reviewer，其他的归 other。
每次请求取队首的一条；队空了 router 回“好的”，别的回“完成”。一条可以是：
- 字符串：直接回答；
- Call / [Call, ...]：调用工具；
- HttpError：按状态码和 JSON 报错（用来模拟 429/402）；
- Stall：流开了以后先给一块思考，然后再也不出块（复现流卡住，见 limits.stream_idle_s）；
- 函数 (body) -> 上面几种之一：按收到的请求临时决定。
"""
import asyncio
import json
import re
from dataclasses import dataclass, field

import httpx
from openai import AsyncOpenAI


@dataclass
class Call:
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class HttpError:
    """让这次补全以 HTTP 错误结束。headers 用小写，例如 retry-after。"""
    status: int
    body: dict | str
    headers: dict = field(default_factory=dict)


@dataclass
class StreamReply:
    """一条可控制 finish_reason / usage 的流。content 空且 finish=length 用来复现 reasoning-only。"""
    content: str = ""
    reasoning: str = ""
    finish: str = "stop"
    calls: list = field(default_factory=list)
    usage: dict | None = None
    omit_usage: bool = False


@dataclass
class Stall:
    """流开了、出了一块思考之后就卡住，直到客户端按 stream_idle_s 关掉它。"""
    reasoning: str = "..."


async def _stalled(reply: Stall):
    yield f"data: {json.dumps(_chunk({'role': 'assistant', 'reasoning_content': reply.reasoning}), ensure_ascii=False)}\n\n".encode()
    await asyncio.Event().wait()


def _chunk(delta: dict, finish=None) -> dict:
    return {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 0, "model": "fake",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}


def _sse(reply) -> bytes:
    if isinstance(reply, StreamReply):
        delta = {"role": "assistant"}
        if reply.reasoning:
            delta["reasoning_content"] = reply.reasoning
        if reply.content or not reply.calls:
            delta["content"] = reply.content
        finish = reply.finish
        if reply.calls:
            delta["tool_calls"] = [{"index": i, "id": f"call_{i}", "type": "function",
                                    "function": {"name": c.name, "arguments": json.dumps(c.args, ensure_ascii=False)}}
                                   for i, c in enumerate(reply.calls)]
            finish = reply.finish or "tool_calls"
        events = [_chunk(delta), _chunk({}, finish)]
        if not reply.omit_usage:
            usage = reply.usage or {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110,
                                    "prompt_cache_hit_tokens": 0}
            events.append({"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 0, "model": "fake",
                           "choices": [], "usage": usage})
        return ("".join(f"data: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events) + "data: [DONE]\n\n").encode()
    if isinstance(reply, Call):
        reply = [reply]
    if isinstance(reply, str):
        events, finish = [_chunk({"role": "assistant", "content": reply})], "stop"
    else:
        calls = [{"index": i, "id": f"call_{i}", "type": "function",
                  "function": {"name": c.name, "arguments": json.dumps(c.args, ensure_ascii=False)}}
                 for i, c in enumerate(reply)]
        events, finish = [_chunk({"role": "assistant", "content": None, "tool_calls": calls})], "tool_calls"
    events.append(_chunk({}, finish))
    events.append({"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 0, "model": "fake", "choices": [],
                   "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}})
    return ("".join(f"data: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events) + "data: [DONE]\n\n").encode()


def system_of(body: dict) -> str:
    return next((m.get("content") or "" for m in body["messages"] if m["role"] == "system"), "")


def role_of(body: dict) -> tuple[str, str]:
    """(角色, Bot 名字)。按系统提示词的开头认。"""
    sys = system_of(body)
    if m := re.match(r'You are "(.+?)"', sys):
        return "router", m.group(1)
    if sys.startswith("You are the Worker"):
        return "worker", ""
    if sys.startswith("You are the reviewer"):
        return "reviewer", ""
    return "other", ""


class FakeLLM:
    def __init__(self):
        self.requests: list[tuple[str, str, dict]] = []   # (角色, Bot 名字, 请求体)
        self.scripts: dict[str, list] = {}
        self.failures: list[int] = []   # 接下来的对话请求依次直接返回这些状态码（模拟服务那边出故障）
        self.failed = 0                 # 已经按 failures 报错了几次
        self.transport = httpx.MockTransport(self._handle)
        self.gap = 0.0          # worker 请求在返回前先等这么久，用来观察并发
        self.worker_peak = 0    # 同时处于处理中的 worker 请求数的峰值
        self._worker_inflight = 0
        self.client = AsyncOpenAI(base_url="http://fake.llm/v1", api_key="test",
                                  http_client=httpx.AsyncClient(transport=self.transport))

    def script(self, who: str, *replies):
        """who：router、router:名字、worker、reviewer、other。"""
        self.scripts.setdefault(who, []).extend(replies)

    def fail(self, *codes: int):
        """接下来的几次对话请求依次返回这些状态码，不消耗剧本。"""
        self.failures.extend(codes)

    def bodies(self, role: str, name: str = "") -> list[dict]:
        return [b for r, n, b in self.requests if r == role and (not name or n == name)]

    def _next(self, role: str, name: str, body: dict):
        for key in (f"{role}:{name}", role):
            if self.scripts.get(key):
                reply = self.scripts[key].pop(0)
                return reply(body) if callable(reply) else reply
        return "好的" if role == "router" else "完成"

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/chat/completions"):
            if self.failures:
                self.failed += 1
                return httpx.Response(self.failures.pop(0), json={"error": {
                    "message": "Internal Server Error (request_id: fake-0000)", "type": "server_error"}})
            body = json.loads(request.content)
            role, name = role_of(body)
            self.requests.append((role, name, body))
            worker = role == "worker"
            if worker:
                self._worker_inflight += 1
                self.worker_peak = max(self.worker_peak, self._worker_inflight)
            try:
                if worker and self.gap:
                    await asyncio.sleep(self.gap)
                reply = self._next(role, name, body)
                if isinstance(reply, HttpError):
                    payload = reply.body if isinstance(reply.body, str) else json.dumps(reply.body)
                    headers = {"content-type": "application/json", **{str(k).lower(): str(v) for k, v in reply.headers.items()}}
                    return httpx.Response(reply.status, headers=headers, content=payload.encode())
                if isinstance(reply, Stall):
                    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=_stalled(reply))
                if not body.get("tools") and not isinstance(reply, (str, StreamReply)):
                    reply = "（没给工具，只能回答）"
                if isinstance(reply, StreamReply) and reply.calls and not body.get("tools"):
                    reply = "（没给工具，只能回答）"
                return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=_sse(reply))
            finally:
                if worker:
                    self._worker_inflight -= 1
        if path.endswith("/models"):
            return httpx.Response(200, json={"object": "list", "data": [{"id": "fake", "object": "model"}]})
        return httpx.Response(404, json={"error": {"message": f"假模型没有 {path}"}})
