"""C3：回复里的数和本轮工具结果对不上时，先给模型一轮机会按结果改，改不掉就在 meta 里标出来。

Chat 1 的实况：没调任何工具的一轮里回答“Bây giờ là 12:20 UTC”，机器当时是 08:11，还说“Đang lấy giờ bằng
quick_code”。C12 把真时钟放进每轮的状态；C3 管的是回复里其它没出处的数。
"""
import pytest

from conftest import find, settle
from fakellm import Call
from osa import bots, server, verification


def test_count_claims_keeps_only_numbers_without_a_source():
    claims = verification.count_claims
    assert claims("Đã chạy 8 lần, in 150 dòng.", "chạy 3 lần, in 150 dòng") == ["8 lần"]
    assert claims("Ran 3 steps and wrote 12 lines.", "steps: 3, lines: 12") == []
    assert claims("Còn 2.000 tệp, 7 dòng nữa.", "2000 tệp, 7 dòng") == []   # 分组写的和裸写的算同一个数
    assert claims("Bạn hỏi gì?", "8 lần") == []                        # 回复里没数就不用管


async def test_a_number_with_no_source_gets_one_repair_round(llm, events, make_bot):
    bot = make_bot("Counter")
    llm.script(f"router:{bot['name']}", Call("remember", {"text": "ba ý chính"}), "Đã chạy 8 lần rồi.")
    await server.safe_handle(bots.chat(bot["chat_id"]), "chạy giúp mình")
    await settle()

    first, _, repair = llm.bodies("router", bot["name"])   # 工具轮、正文轮、修一轮
    assert "8 lần" not in first["messages"][-1]["content"]  # 没说过就没人提醒
    assert "“8 lần”" in repair["messages"][-1]["content"]
    assert "nothing this turn gave that number" in repair["messages"][-1]["content"]
    [reply] = find(bot["chat_id"], role="assistant", text="8 lần")
    assert reply["meta"]["self_check"] == ["8 lần"]      # 改了一轮还是对不上：记下来


async def test_the_repair_round_runs_only_once(llm, events, make_bot):
    """改一轮还是那句 8 lần：不再追着改，只在 meta 里标出来（那句错话还在回复里，读者要知道）。"""
    bot = make_bot("Corrector")
    llm.script(f"router:{bot['name']}", Call("remember", {"text": "ba ý chính"}),
               "Đã chạy 8 lần rồi.", "Vẫn là 8 lần nhé.")
    await server.safe_handle(bots.chat(bot["chat_id"]), "chạy giúp mình")
    await settle()

    assert len(llm.bodies("router", bot["name"])) == 3     # 只修一次
    reply = find(bot["chat_id"], role="assistant")[-1]
    assert reply["meta"]["self_check"] == ["8 lần"]
    assert reply["content"].startswith("Đã chạy 8 lần")   # 正文是整段，含先前那句


async def test_a_turn_without_tools_is_not_checked(llm, events, make_bot):
    """没有工具结果可比的一轮（例如只聊天）不该为此多花一次调用。"""
    bot = make_bot("Chatty")
    llm.script(f"router:{bot['name']}", "Mình sẽ chạy 8 lần.")
    await server.safe_handle(bots.chat(bot["chat_id"]), "chạy giúp mình")
    await settle()
    assert len(llm.bodies("router", bot["name"])) == 1
    assert "self_check" not in find(bot["chat_id"], role="assistant")[-1]["meta"]
