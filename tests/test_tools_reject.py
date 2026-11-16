"""Model không được khai báo hỗ trợ tools (dolphin-mistral-24b-venice-edition): bỏ tools rồi vẫn trả lời.

Đo live 16/11: gateway trả 400 "The selected model route is not declared to support tools" — cả lượt chết
dù model trả lời chữ bình thường được. Ở đây: 400 lần đầu → gọi lại không kèm tools → nhớ luôn cho lần sau.
"""
import httpx
import openai
import pytest

from osa import providers


def _client(seen: list, fail_first: bool):
    calls = {"n": 0}

    class Completions:
        async def create(self, **kw):
            seen.append(kw)
            calls["n"] += 1
            if fail_first and calls["n"] == 1:
                raise openai.BadRequestError(
                    "The selected model route is not declared to support tools.",
                    response=httpx.Response(400, request=httpx.Request("POST", "http://x/v1/chat/completions")),
                    body=None)
            return "ok"

    return type("C", (), {"base_url": "http://x/v1", "chat": type("Ch", (), {"completions": Completions()})()})


async def test_a_400_about_tools_retries_without_them(monkeypatch):
    seen: list = []
    monkeypatch.setitem(providers.CFG["limits"], "provider_transient_retries", 0)
    out = await providers.create_chat(_client(seen, True), model="dolphin-x", tools=[{"a": 1}],
                                      tool_choice={"b": 1}, messages=[{"role": "user", "content": "hi"}])
    assert out == "ok"
    assert "tools" not in seen[1] and "tool_choice" not in seen[1]


async def test_the_next_call_already_knows(monkeypatch):
    seen: list = []
    await providers.create_chat(_client(seen, False), model="dolphin-x", tools=[{"a": 1}],
                                messages=[{"role": "user", "content": "hi"}])
    assert "tools" not in seen[0]      # đã nhớ từ lần trước (cùng base_url + model)
