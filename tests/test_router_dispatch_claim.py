"""B1：Router 没调 dispatch 却说“已派发任务 #N”（N 不存在）。代码里拦下：给一次带工具的机会真的去派，
仍然没有就补一句更正；这条回复在以后的上下文里标成通知，不当成可以照抄的格式。假模型，无密钥。

RETRO-01：每次 dispatch 后都对 meta.tasks 断言；每个测试用自己的新 Bot（相当于新话题），不让历史互相污染。"""
import pytest

from conftest import find, settle, until
from fakellm import Call
from osa import bots, i18n, server


def _chat(bot):
    return bots.chat(bot["chat_id"])


def _replies(bot):
    return find(bot["chat_id"], role="assistant")


@pytest.fixture
def vi(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")


async def test_fake_dispatch_gets_corrective_round_that_really_dispatches(llm, events, make_bot, vi):
    bot = make_bot("ClaimA")
    llm.script(f"router:{bot['name']}", "Đã giao tác vụ #999.", Call("dispatch", {"goal": "tra cứu"}), "Giờ đã giao thật.")
    llm.script("worker", "xong")
    await server.safe_handle(_chat(bot), "ok")
    await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả task")
    await settle()

    reqs = llm.bodies("router", bot["name"])
    assert "dispatch" in reqs[1]["messages"][-1]["content"] and "#999" in reqs[1]["messages"][-1]["content"]
    assert reqs[1].get("tools")   # lượt sửa có tool
    dispatched = find(bot["chat_id"], kind="dispatch")
    assert len(dispatched) == 1
    reply = _replies(bot)[-1]
    assert reply["meta"]["tasks"] == [_dispatch_id(bot)]   # RETRO-01: lượt này có task thật
    assert reply["meta"]["fabricated_task_ids"] == [999]
    assert "Đính chính" not in reply["content"]   # đã giao thật thì không cần câu đính chính


async def test_short_confirmation_history_replay_is_caught(llm, events, make_bot, vi):
    """Lịch sử có 3 lượt xác nhận ngắn, mỗi lượt giao thật và nói “Đã giao tác vụ #N”; lượt 4 model chỉ bắt chước câu chữ."""
    bot = make_bot("ClaimB")
    name = f"router:{bot['name']}"
    for i in range(3):
        llm.script(name, Call("dispatch", {"goal": f"việc {i}"}),
                   lambda body: f"Đã giao tác vụ #{_last_dispatch(bot)}.")
        llm.script("worker", f"xong {i}")
        await server.safe_handle(_chat(bot), "ok")
        await until(lambda: len(find(bot["chat_id"], kind="result")) >= i + 1, what="kết quả")
        await settle()
        assert _replies(bot)[-1]["meta"]["tasks"]   # RETRO-01: lượt thật có task
        assert "fabricated_task_ids" not in _replies(bot)[-1]["meta"]

    llm.script(name, "Đã giao tác vụ #88888.", "Xin lỗi, mình chưa giao gì cả.")
    await server.safe_handle(_chat(bot), "ok")
    await settle()
    last = _replies(bot)[-1]
    assert last["meta"]["tasks"] == []
    assert last["meta"]["fabricated_task_ids"] == [88888]
    assert "Đính chính" in last["content"] and "#88888" in last["content"]
    assert len(find(bot["chat_id"], kind="dispatch")) == 3   # không có task ma

    # Lượt sau: câu sai được đưa vào như thông báo hệ thống, không phải một assistant message để chép theo
    llm.script(name, "Bạn cần gì nữa?")
    await server.safe_handle(_chat(bot), "còn gì không")
    await settle()
    ctx = llm.bodies("router", bot["name"])[-1]["messages"]
    assert not any(m["role"] == "assistant" and "#88888" in (m.get("content") or "") for m in ctx)
    assert any(m["role"] == "user" and "never existed" in str(m.get("content")) and "#88888" in str(m.get("content")) for m in ctx)


def _last_dispatch(bot):
    return _dispatch_id(bot)


def _dispatch_id(bot):
    from osa import memory
    return memory.conn.execute("select max(id) from messages where chat_id=? and json_extract(meta,'$.kind')='dispatch'",
                               (bot["chat_id"],)).fetchone()[0]


async def test_real_task_reference_is_not_flagged(llm, events, make_bot, vi):
    bot = make_bot("ClaimC")
    name = f"router:{bot['name']}"
    llm.script(name, Call("dispatch", {"goal": "việc dài"}), "Đã giao.")
    llm.script("worker", "xong")
    await server.safe_handle(_chat(bot), "làm đi")
    await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả")
    await settle()
    tid = _dispatch_id(bot)
    before = len(llm.bodies("router", bot["name"]))
    llm.script(name, lambda body: f"Tác vụ #{tid} đã giao xong rồi. Xem thêm PR #42 trên GitHub.")
    await server.safe_handle(_chat(bot), "sao rồi")
    await settle()
    assert len(llm.bodies("router", bot["name"])) == before + 1   # không có lượt sửa
    assert "fabricated_task_ids" not in _replies(bot)[-1]["meta"]


async def test_corrective_round_runs_only_once(llm, events, make_bot, vi):
    bot = make_bot("ClaimD")
    name = f"router:{bot['name']}"
    llm.script(name, "Đã giao tác vụ #777.", "Đã giao tác vụ #778 rồi nhé.", "không được dùng tới")
    await server.safe_handle(_chat(bot), "ok")
    await settle()
    assert len(llm.bodies("router", bot["name"])) == 2
    last = _replies(bot)[-1]
    assert last["meta"]["tasks"] == [] and last["meta"]["fabricated_task_ids"] == [777]
    assert last["content"].rstrip().endswith(i18n.t("（更正：这一轮没有派出任务 {ids}，上面说已派发是不对的。）", ids="#777"))
    assert not find(bot["chat_id"], kind="dispatch")


# ---- C10：没带任务号的“已经交给 worker 了” ----

def test_detector_reads_the_three_languages():
    """live 里漏掉的两条（chat 1 #118、#120）和它们的近亲；否定句、带 #N 的、已经在讲结果的都不算。"""
    from osa.router import Router
    claim = lambda t: Router._dispatch_claim_without_id(None, t)
    for text in ["Đã giao worker chạy đủ 8 lần, mỗi lần in 150 dòng.",
                 "Đã gọi `dispatch`. Worker sẽ chạy đủ 8 lần rồi tóm tắt.",
                 "Mình đã chuyển việc này sang worker.",
                 "Đã chuyển cho worker rồi.",
                 "已交给 worker 了", "已派发，worker 正在跑",
                 "I've dispatched it to the worker.", "Already dispatched, the worker is on it."]:
        assert claim(text), text
    for text in ["Chưa giao cho worker, để mình hỏi lại.",
                 "Tôi sẽ giao worker chạy 8 lần.",
                 "Tác vụ #12 đã giao xong.",
                 "Đã giao worker, kết quả đã về rồi.",
                 "Hôm nay là ngày 11 tháng 11, 17×23 = 391.",
                 "已派发任务 #12"]:
        assert not claim(text), text


async def test_numberless_claim_gets_corrective_round_that_really_dispatches(llm, events, make_bot, vi):
    """活还没派就说“Đã giao worker…”，修复轮真的调了 dispatch：不留更正句，记正常的 tasks。"""
    bot = make_bot("ClaimE")
    name = f"router:{bot['name']}"
    llm.script(name, "Đã giao worker chạy 8 lần, mỗi lần in 150 dòng. Kết quả sẽ về khi xong.",
               Call("dispatch", {"goal": "chạy run_code 8 lần"}), "Giờ đã giao thật.")
    llm.script("worker", "xong")
    await server.safe_handle(_chat(bot), "Giao cho worker: chạy run_code 8 lần")
    await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả task")
    await settle()

    reqs = llm.bodies("router", bot["name"])
    assert len(reqs) == 3 and reqs[1].get("tools")          # 说是说、修复轮调 dispatch、再收尾
    assert "no dispatch tool call" in reqs[1]["messages"][-1]["content"]
    assert len(find(bot["chat_id"], kind="dispatch")) == 1
    reply = _replies(bot)[-1]
    assert reply["meta"]["tasks"] == [_dispatch_id(bot)]
    assert "claimed_dispatch" not in reply["meta"]
    assert "Đính chính" not in reply["content"]


async def test_numberless_claim_twice_appends_correction_and_history_notice(llm, events, make_bot, vi):
    bot = make_bot("ClaimF")
    name = f"router:{bot['name']}"
    llm.script(name, "Đã gọi `dispatch`. Worker sẽ chạy 8 lần rồi tóm tắt.",
               "Đã giao worker rồi nhé.", "không được dùng tới")
    await server.safe_handle(_chat(bot), "Giao cho worker: chạy run_code 8 lần")
    await settle()

    assert len(llm.bodies("router", bot["name"])) == 2      # 只修一次
    last = _replies(bot)[-1]
    assert last["meta"]["tasks"] == [] and last["meta"]["claimed_dispatch"] is True
    assert last["content"].rstrip().endswith(i18n.t("（更正：这一轮还没真的派出任务，上面说已经交给 worker 是不对的。）"))
    assert not find(bot["chat_id"], kind="dispatch")

    llm.script(name, "Bạn cần gì nữa?")
    await server.safe_handle(_chat(bot), "còn gì không")
    await settle()
    ctx = llm.bodies("router", bot["name"])[-1]["messages"]
    assert not any(m["role"] == "assistant" and "never called the dispatch tool" in (m.get("content") or "") for m in ctx)
    assert any(m["role"] == "user" and "never called the dispatch tool" in str(m.get("content")) for m in ctx)


async def test_real_dispatch_in_the_same_turn_is_not_corrected(llm, events, make_bot, vi):
    """同一轮真的派了任务，然后说“Đã giao worker chạy rồi”：不该再修一轮。"""
    bot = make_bot("ClaimG")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "việc"}), "Đã giao worker chạy rồi.")
    llm.script("worker", "xong")
    await server.safe_handle(_chat(bot), "làm đi")
    await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả")
    await settle()
    assert len(llm.bodies("router", bot["name"])) == 2      # 调工具 + 收尾，没有修复轮
    reply = _replies(bot)[-1]
    assert reply["meta"]["tasks"] and "claimed_dispatch" not in reply["meta"]
    assert "Đính chính" not in reply["content"]
