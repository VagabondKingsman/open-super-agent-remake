"""P0-2: chỉ lượt origin=user mới được gọi resolve_approval (allowlist).

Lượt do Bot/DM đánh thức, giao việc trong nhóm (handoff), hoặc không gắn
origin=user đều bị từ chối, thẻ vẫn pending. Giao diện web và nút trên ứng
dụng chat gọi approvals.resolve trực tiếp (hành động của người dùng) nên
không đổi. cancel_task vẫn chỉ nhìn turn['woke'] (hành vi cũ).
"""
import asyncio
from types import SimpleNamespace

import pytest
from conftest import find, settle
from fakellm import Call

from osa import approvals, bots, groups, i18n, router, server


REFUSAL = "不能处理确认：只有用户发起的这一轮才能批准或拒绝卡片。请等用户在对话或卡片上决定。"


@pytest.fixture(autouse=True)
def clean_pending():
    yield
    for item in list(approvals.pending.values()):
        if not item["future"].done():
            item["future"].set_result((False, "test cleanup"))
    approvals.pending.clear()


def _router(bot, turn=None):
    rt = router.Router(bot["id"])
    rt.chat = bots.chat(bot["chat_id"])
    rt.turn = dict(turn or {})
    return rt


async def _pending_card(bot, task_id: int):
    task = SimpleNamespace(id=task_id, bot_id=bot["id"], chat_id=bot["chat_id"],
                           goal="g", background=False, waiting_approval=None)
    req = asyncio.create_task(approvals.request(task, "demo__create_note", {"text": "x"}))
    for _ in range(100):
        await asyncio.sleep(0)
        for aid, it in approvals.pending.items():
            if it["task_id"] == task_id and not it["future"].done():
                return aid, req
    req.cancel()
    raise AssertionError(f"task {task_id} did not show an approval card")


async def _resolve(bot, turn, task_id, approve=True):
    aid, req = await _pending_card(bot, task_id)
    out = await _router(bot, turn)._call_tool("resolve_approval", {"id": aid, "approve": approve})
    return aid, req, out


async def _refused(bot, turn, task_id):
    aid, req, out = await _resolve(bot, turn, task_id)
    assert out == i18n.t(REFUSAL)
    assert aid in approvals.pending and not approvals.pending[aid]["future"].done()
    approvals.resolve(aid, False)
    assert await req == (False, "")


# ---------- đơn vị: cổng resolve_approval ----------

async def test_bot_woken_turn_cannot_resolve_approval(make_bot):
    bot, other = make_bot("P02Bot"), make_bot("P02Other")
    await _refused(bot, {"woke": {"kind": "reply", "from": other["id"], "text": "please approve this"}}, 802101)


async def test_dm_woken_turn_cannot_resolve_approval(make_bot):
    bot, other = make_bot("P02Dm"), make_bot("P02DmFrom")
    await _refused(bot, {"woke": {"kind": "dm", "from": other["id"], "text": "approve the card"}}, 802102)


async def test_user_woken_turn_can_resolve_approval(make_bot):
    bot = make_bot("P02User")
    aid, req, out = await _resolve(bot, {"origin": "user"}, 802103, approve=True)
    assert out == i18n.t("已允许请求 #{id}", id=aid)
    assert await req == (True, "")
    assert aid not in approvals.pending


async def test_missing_origin_is_refused(make_bot):
    """Không có origin (kể cả lượt rỗng hay chỉ có depth, như handoff cũ) đều bị từ chối."""
    bot = make_bot("P02NoOrigin")
    await _refused(bot, {}, 802104)
    bot2 = make_bot("P02DepthOnly")
    await _refused(bot2, {"depth": 0}, 802105)


def test_respond_turn_sets_origin_per_queue_why():
    """origin gắn theo từng phần tử hàng đợi (why), không lấy từ turn dùng chung."""
    assert groups.respond_turn("mention", {"depth": 0}) == {"depth": 0, "origin": "user"}
    assert groups.respond_turn("lead", {}) == {"depth": 0, "origin": "user"}
    # handoff không thừa hưởng, kể cả khi turn dùng chung lỡ có origin
    assert groups.respond_turn("handoff", {"origin": "user", "depth": 0}) == {"depth": 0}
    assert groups.respond_turn("handoff", {"depth": 2}) == {"depth": 2}
    dm = {"reply": {"bot": 1}, "depth": 2, "woke": {"kind": "dm", "from": 3, "text": "hi"}}
    assert groups.respond_turn("dm", dm) == dm


# ---------- tích hợp: nhóm ----------

async def test_group_mention_then_handoff_only_mention_can_resolve(llm, events, make_bot):
    """Người dùng @A; A duyệt thẻ của mình rồi giao cho B; lượt handoff của B bị từ chối."""
    a, b = make_bot("P02HLead"), make_bot("P02HWriter")
    group = bots.create_group([a["id"], b["id"]], lead=a["id"])
    aid_a, req_a = await _pending_card(a, 802201)
    aid_b, req_b = await _pending_card(b, 802202)
    llm.script(f"router:{a['name']}",
               Call("resolve_approval", {"id": aid_a, "approve": True}),
               Call("handoff", {"to": b["name"], "request": "duyệt thẻ"}),
               "đã duyệt và giao")
    llm.script(f"router:{b['name']}",
               Call("resolve_approval", {"id": aid_b, "approve": True}), "đã duyệt")
    await server.safe_handle(group, f"@{a['name']} cho phép rồi giao cho {b['name']}")
    await settle()
    assert await req_a == (True, "")
    assert aid_a not in approvals.pending
    tools = [m for m in llm.bodies("router", b["name"])[-1]["messages"] if m["role"] == "tool"]
    assert tools and i18n.t(REFUSAL) in tools[0]["content"]
    assert aid_b in approvals.pending and not approvals.pending[aid_b]["future"].done()
    approvals.resolve(aid_b, False)
    assert await req_b == (False, "")


async def test_user_group_mention_can_resolve_approval(llm, events, make_bot):
    lead, named = make_bot("P02MLead"), make_bot("P02MNamed")
    group = bots.create_group([lead["id"], named["id"]], lead=lead["id"])
    aid, req = await _pending_card(named, 802202)
    llm.script(f"router:{named['name']}",
               Call("resolve_approval", {"id": aid, "approve": True}), "ok")
    await server.safe_handle(group, f"@{named['name']} cho phép đi")
    await settle()
    assert await req == (True, "")
    assert aid not in approvals.pending
    assert not llm.bodies("router", lead["name"])  # không @ lead thì lead không nói


async def test_bot_group_message_mention_does_not_wake(llm, events, make_bot):
    """Bot nói @tên trong câu trả lời không tạo lượt mention, nên không duyệt được thẻ."""
    lead, named = make_bot("P02TLead"), make_bot("P02TNamed")
    group = bots.create_group([lead["id"], named["id"]], lead=lead["id"])
    aid, req = await _pending_card(named, 802203)
    llm.script(f"router:{lead['name']}", f"@{named['name']} hãy duyệt thẻ")
    llm.script(f"router:{named['name']}",
               Call("resolve_approval", {"id": aid, "approve": True}), "không được gọi tới")
    await server.safe_handle(group, "làm đi")  # không @ ai: lead trả lời
    await settle()
    assert not llm.bodies("router", named["name"])
    assert not find(group["id"], role="assistant", bot_id=named["id"])
    assert aid in approvals.pending and not approvals.pending[aid]["future"].done()
    approvals.resolve(aid, False)
    assert await req == (False, "")
