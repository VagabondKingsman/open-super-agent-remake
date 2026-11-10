"""B2/B6：reasoning_effort 只能存认得的值；模型服务不认某个强度（400）时去掉重试一次并记下来。假模型，无密钥。"""
import httpx
import pytest

from conftest import find, until
from fakellm import Call, HttpError
from osa import i18n, memory, providers, server
from osa.config import CFG

REJECT = HttpError(400, {"error": {"message": "Model grok-x does not support parameter reasoningEffort", "type": "invalid_request_error"}})


def _picky(ok: str = "完成"):
    """带 reasoning_effort 就 400，不带就正常回答。"""
    return lambda body: REJECT if "reasoning_effort" in body else ok


@pytest.fixture(autouse=True)
def clean_rejects():
    memory.conn.execute("delete from settings where key='effort_rejects'")
    memory.conn.commit()
    yield
    memory.conn.execute("delete from settings where key='effort_rejects'")
    memory.conn.commit()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://127.0.0.1")


async def test_settings_rejects_unknown_effort(no_password, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "en")
    before = memory.conn.execute("select value from settings where key='overrides'").fetchone()
    async with _client() as c:
        r = await c.put("/api/settings", json={"roles": {"worker": {"reasoning_effort": "ultra"}}})
        assert r.status_code == 400 and "Reasoning effort must be one of" in r.json()["detail"]
        assert "xhigh" in r.json()["detail"]
    after = memory.conn.execute("select value from settings where key='overrides'").fetchone()
    assert before == after   # 没存进去


@pytest.mark.parametrize("effort", ["", "low", "medium", "high", "xhigh", "max"])
def test_settings_accepts_known_effort(effort, monkeypatch):
    from osa import settings
    before = memory.conn.execute("select value from settings where key='overrides'").fetchone()
    try:
        settings.save({"roles": {"filter": {"reasoning_effort": effort}}})
    finally:
        memory.conn.execute("delete from settings where key='overrides'")
        if before:
            memory.conn.execute("insert into settings values('overrides', ?)", before)
        memory.conn.commit()
        settings.apply()


async def _text(stream) -> str:
    return "".join([c.choices[0].delta.content or "" async for c in stream if c.choices])


async def test_create_chat_drops_rejected_effort_and_remembers(llm):
    llm.script("other", _picky("ok1"), _picky("ok1"), _picky("ok2"))
    r = await providers.create_chat(llm.client, model="grok-x", messages=[{"role": "user", "content": "hi"}],
                                    reasoning_effort="max", stream=True)
    assert await _text(r) == "ok1"
    sent = llm.bodies("other")
    assert sent[0]["reasoning_effort"] == "max" and "reasoning_effort" not in sent[1]
    assert providers.effort_rejected(str(llm.client.base_url), "grok-x", "max")
    # 下一次直接不带，不再先挨一次 400
    r = await providers.create_chat(llm.client, model="grok-x", messages=[{"role": "user", "content": "hi"}],
                                    reasoning_effort="max", stream=True)
    assert await _text(r) == "ok2"
    assert len(llm.bodies("other")) == 3 and "reasoning_effort" not in llm.bodies("other")[2]
    # 别的强度、别的模型不受影响
    assert not providers.effort_rejected(str(llm.client.base_url), "grok-x", "high")
    assert not providers.effort_rejected(str(llm.client.base_url), "grok-y", "max")


async def test_create_chat_other_400_still_raises(llm):
    import openai
    bad = HttpError(400, {"error": {"message": "bad messages"}})
    llm.script("other", bad, bad)
    with pytest.raises(openai.BadRequestError):
        await providers.create_chat(llm.client, model="grok-x", messages=[{"role": "user", "content": "hi"}],
                                    reasoning_effort="high", stream=True)
    assert len(llm.bodies("other")) == 2   # 去掉强度重试了一次，仍然 400：报原来的错，不记
    assert not providers.effort_rejected(str(llm.client.base_url), "grok-x", "high")

    llm.script("other", bad)
    with pytest.raises(openai.BadRequestError):
        await providers.create_chat(llm.client, model="grok-x", messages=[{"role": "user", "content": "hi"}], stream=True)
    assert len(llm.bodies("other")) == 3   # 没带强度的 400 不重试


async def test_worker_task_survives_rejected_effort(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["roles"], "worker", {**CFG["roles"]["worker"], "reasoning_effort": "max"})
    bot = make_bot("Effort")
    llm.script("worker", _picky("任务做完了"), _picky("任务做完了"))
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "算一下"}), "派出去了")
    await server.safe_handle(__import__("osa.bots", fromlist=["chat"]).chat(bot["chat_id"]), "帮我算")
    result = await until(lambda: find(bot["chat_id"], kind="result"), what="任务结果")
    assert result[-1]["meta"]["status"] == "done" and "任务做完了" in result[-1]["content"]
    w = llm.bodies("worker")
    assert w[0].get("reasoning_effort") == "max" and "reasoning_effort" not in w[1]


async def test_model_test_reports_rejected_effort(monkeypatch):
    """设置里点“测试”：用途设了模型不认的强度，回 ok 并带上 effort_rejected 和翻译好的提醒。"""
    import json
    seen = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if "reasoning_effort" in body:
            return httpx.Response(400, json=REJECT.body)
        return httpx.Response(200, json={"id": "x", "object": "chat.completion", "created": 0, "model": "grok-x",
                                         "choices": [{"index": 0, "finish_reason": "stop",
                                                      "message": {"role": "assistant", "content": "red"}}],
                                         "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6}})
    make = providers.AsyncOpenAI
    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(providers, "AsyncOpenAI", lambda **kw: make(**kw, http_client=httpx.AsyncClient(transport=transport)))
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setitem(CFG["providers"], "fakex", {"base_url": "http://fake.llm/v1"})
    monkeypatch.setitem(CFG["roles"], "reviewer", {**CFG["roles"]["reviewer"], "reasoning_effort": "max"})
    res = await providers.test("fakex", "grok-x", "chat", "reviewer")
    assert res["ok"] and res["effort_rejected"] == "max", res
    assert "max" in res["effort_warning"] and "không nhận" in res["effort_warning"]
    assert [("reasoning_effort" in b) for b in seen] == [True, False]
    assert providers.effort_rejected("http://fake.llm/v1", "grok-x", "max")
