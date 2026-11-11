"""A4：每条回复在 meta 里带上这一轮用了多少——in/out 个 token、费用（美元）、整轮用时，以及第一个字多久出来（ttft）。
界面在回复下面淡淡写一行；数据源就是记账用的 llm_calls，这里断言两边对得上。假模型，无密钥。"""
import pytest

from conftest import find, settle
from osa import memory, server


def test_record_usage_returns_what_it_wrote(monkeypatch):
    u = memory.record_usage("router", "m", None, ms=1200, ttft=300)
    assert u == {"in": 0, "out": 0, "cache": 0, "cost": 0.0, "ttft": 300, "est": False}
    assert memory.record_usage("router", "m", None) is None   # 没有 usage 也没有用时：没记，返回 None


async def test_reply_meta_carries_turn_usage(llm, events, make_bot):
    bot = make_bot("UsageA")
    llm.script(f"router:{bot['name']}", "xong")
    await server.safe_handle(bot_chat(bot), "chào")
    await settle()
    reply = find(bot["chat_id"], role="assistant")[-1]
    u = reply["meta"]["usage"]
    assert u["in"] == 100, "fakellm 的默认 usage：prompt 100"
    assert u["out"] == 10
    assert u["cost"] >= 0 and u["sec"] >= 0
    assert isinstance(u["ttft"], int) and u["ttft"] >= 0
    assert not u.get("est")


async def test_usage_adds_up_over_tool_rounds(llm, events, make_bot):
    from fakellm import Call
    bot = make_bot("UsageB")
    llm.script(f"router:{bot['name']}", Call("list_tasks", {}), "xong")
    await server.safe_handle(bot_chat(bot), "có việc gì?")
    await settle()
    reply = find(bot["chat_id"], role="assistant")[-1]
    u = reply["meta"]["usage"]
    assert u["in"] == 200 and u["out"] == 20   # 两轮模型调用，每轮 100/10


def bot_chat(bot):
    from osa import bots
    return bots.chat(bot["chat_id"])
