"""任务号不能被用回的消息 id 撞掉：删 Bot 后 SQLite 会用回最大的消息 id，撞上还在跑的任务。"""
import asyncio

import pytest

from osa import router


def fake(bot_id=1):
    return router.Task(id=-1, goal="x", mode="single", bot_id=bot_id, chat_id=1, approval_chat_id=1)


def test_a_reused_message_id_gets_a_free_task_number():
    router.TASKS[4242] = fake()           # 一个还在 TASKS 里的老任务
    got = router.task_id(4242)
    assert got not in router.TASKS and got > 4242
    assert router.task_id(4242) not in router.TASKS      # 下一次也不会用回同一个号


def test_an_unused_message_id_is_the_task_id():
    assert router.task_id(900000001) == 900000001


async def test_dispatch_does_not_overwrite_a_live_task(make_bot, monkeypatch):
    bot = make_bot("IdClash")
    rt = router.Router(bot["id"])
    rt.chat = {"id": bot["chat_id"]}

    async def noop(task):
        await asyncio.sleep(0)

    async def quiet(event, chat_id=None):
        return None

    async def fixed_add(role, content, chat_id=None, **meta):
        return 5555                       # 每次派发都拿到同一个消息 id（消息被删过后的重用）

    monkeypatch.setattr(rt, "_run", noop)
    monkeypatch.setattr(rt, "emit", quiet)
    monkeypatch.setattr(rt, "add", fixed_add)

    first = await rt.dispatch("việc một")
    keep = router.TASKS[first.id]
    second = await rt.dispatch("việc hai")

    assert second.id != first.id
    assert router.TASKS[first.id] is keep        # 老任务没被覆盖
    assert router.TASKS[second.id] is second
    assert first.goal == "việc một" and second.goal == "việc hai"
