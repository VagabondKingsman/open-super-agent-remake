"""A stuck chat turn must not hold its bot's lock.

Nova, 2026-11-18: one tool step ran 926 s, the turn never finished, and the
bot's asyncio.Lock stayed held for 2.5 hours - every later message queued
behind it in silence. Router.respond now bounds the turn and releases the
lock either way.
"""
import asyncio
import time

from osa import router


def test_ceiling_reads_the_config(monkeypatch):
    monkeypatch.setitem(router.CFG["limits"], "turn_timeout_s", 42)
    assert router._turn_timeout_seconds() == 42
    monkeypatch.setitem(router.CFG["limits"], "turn_timeout_s", 0)
    assert router._turn_timeout_seconds() == 0


def test_a_stuck_turn_releases_the_lock(monkeypatch):
    monkeypatch.setitem(router.CFG["limits"], "turn_timeout_s", 0.2)
    monkeypatch.setattr(router.bots, "chat", lambda cid: {"id": cid})
    bot = router.Router(1)
    bot.added = []

    async def add(role, content, chat_id=None, **meta):
        bot.added.append(meta)

    async def hang(chat):
        await asyncio.sleep(30)

    async def release():
        return None

    bot.add = add
    bot._think = hang
    bot._release_desk = release

    async def body():
        t0 = time.monotonic()
        await bot.respond(1, {"origin": "user"})
        took = time.monotonic() - t0
        assert took < 5, took
        assert not bot.lock.locked(), "the turn lock is still held"
        assert any(m.get("kind") == "turn-timeout" for m in bot.added), bot.added

    asyncio.run(body())
