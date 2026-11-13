"""重启等 Bot 闲着：有任务或在跑一轮时不换进程，空下来才换。"""
import asyncio

import httpx
import pytest

from osa import idle, router as rt, server


def http():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://127.0.0.1")


class FakeTask:
    def __init__(self, i, status):
        self.id, self.status = i, status


def test_busy_reads_tasks_and_locks(monkeypatch):
    monkeypatch.setattr(idle, "awaiting_reply", lambda: False)
    async def main():
        assert idle.busy() is False
        monkeypatch.setattr(rt, "TASKS", {7: FakeTask(7, "running")})
        assert idle.busy() is True
        monkeypatch.setattr(rt, "TASKS", {7: FakeTask(7, "done")})
        assert idle.busy() is False
        lock = asyncio.Lock()
        monkeypatch.setattr(rt, "RUNTIMES", {1: type("R", (), {"lock": lock})()})
        async with lock:
            assert idle.busy() is True
            assert idle.waiting()["turns"] == [1]
        assert idle.busy() is False
    asyncio.run(main())


async def test_an_unanswered_user_message_is_busy(make_bot):
    from osa import memory
    bot = make_bot("Cho")
    memory.add("user", "câu vừa gửi", bot["chat_id"])
    assert idle.awaiting_reply(bot["chat_id"]) is True    # 还没回：换进程会把话吞掉
    memory.add("assistant", "đã trả lời", bot["chat_id"])
    assert idle.awaiting_reply(bot["chat_id"]) is False


async def test_wait_until_idle_needs_a_quiet_stretch(monkeypatch):
    monkeypatch.setattr(idle, "QUIET", 0.05)
    monkeypatch.setattr(idle, "POLL", 0.01)
    busy = {"v": True}

    async def flip():
        await asyncio.sleep(0.08)
        busy["v"] = False
    monkeypatch.setattr(idle, "busy", lambda: busy["v"])
    t = asyncio.create_task(flip())
    assert await idle.wait_until_idle(2) is True
    await t


async def test_wait_until_idle_gives_up(monkeypatch):
    monkeypatch.setattr(idle, "QUIET", 5)
    monkeypatch.setattr(idle, "POLL", 0.01)
    monkeypatch.setattr(idle, "busy", lambda: True)
    assert await idle.wait_until_idle(0.05) is False


async def test_idle_route_queues_instead_of_restarting(monkeypatch):
    asked = []
    monkeypatch.setattr(server.backup, "request_restart", lambda delay=0.5: asked.append(delay))
    monkeypatch.setattr(server.idle, "busy", lambda: True)     # 一直忙：这一轮不会重启
    monkeypatch.setattr(server.idle, "waiting", lambda: {"busy": True, "tasks": [7], "turns": []})
    monkeypatch.setattr(server.idle, "wait_until_idle", lambda m: asyncio.sleep(0, result=False))
    async with http() as c:
        r = await c.post("/api/system/restart?when=idle&max=1")
    assert r.status_code == 200 and r.json()["queued"] is True
    assert r.json()["busy"] is True
    assert asked == []                                     # 没有硬重启
