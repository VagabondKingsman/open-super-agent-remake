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
