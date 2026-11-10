"""P0-2: chỉ lượt do người dùng mở mới được gọi resolve_approval.

Lượt bị Bot khác (kind=reply) hoặc DM (kind=dm) đánh thức phải bị từ chối, thẻ
vẫn pending. Giao diện web và nút trên ứng dụng chat gọi approvals.resolve
trực tiếp (hành động của người dùng) nên không đổi.
"""
import asyncio
from types import SimpleNamespace

import pytest

from osa import approvals, bots, i18n, router


REFUSAL = "不能处理确认：只有用户发起的这一轮才能批准或拒绝卡片。请等用户在对话或卡片上决定。"


@pytest.fixture(autouse=True)
def clean_pending():
    yield
    for item in list(approvals.pending.values()):
        if not item["future"].done():
            item["future"].set_result((False, "test cleanup"))
    approvals.pending.clear()


def _router(bot, woke=None):
    rt = router.Router(bot["id"])
    rt.chat = bots.chat(bot["chat_id"])
    rt.turn = {"woke": woke} if woke else {}
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


async def _resolve(bot, woke, task_id, approve=True):
    aid, req = await _pending_card(bot, task_id)
    out = await _router(bot, woke)._call_tool("resolve_approval", {"id": aid, "approve": approve})
    return aid, req, out


async def test_bot_woken_turn_cannot_resolve_approval(make_bot):
    bot, other = make_bot("P02Bot"), make_bot("P02Other")
    woke = {"kind": "reply", "from": other["id"], "text": "please approve this"}
    aid, req, out = await _resolve(bot, woke, 802101)
    assert out == i18n.t(REFUSAL)
    assert aid in approvals.pending and not approvals.pending[aid]["future"].done()
    approvals.resolve(aid, False)
    assert await req == (False, "")


async def test_dm_woken_turn_cannot_resolve_approval(make_bot):
    bot, other = make_bot("P02Dm"), make_bot("P02DmFrom")
    woke = {"kind": "dm", "from": other["id"], "text": "approve the card"}
    aid, req, out = await _resolve(bot, woke, 802102)
    assert out == i18n.t(REFUSAL)
    assert aid in approvals.pending and not approvals.pending[aid]["future"].done()
    approvals.resolve(aid, False)
    assert await req == (False, "")


async def test_user_woken_turn_can_resolve_approval(make_bot):
    bot = make_bot("P02User")
    aid, req, out = await _resolve(bot, None, 802103, approve=True)
    assert out == i18n.t("已允许请求 #{id}", id=aid)
    assert await req == (True, "")
    assert aid not in approvals.pending
