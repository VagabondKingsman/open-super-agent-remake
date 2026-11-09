"""OSA-029 R1: watchdog / prune / embed 三个后台循环遇到异常只记日志，不能整个退出。无网络、无真模型。"""
import asyncio
import logging
import time
from types import SimpleNamespace

import pytest

from osa import memory, router, search, tasklog, watchdog
from osa.config import CFG

_real_sleep = asyncio.sleep


async def _run_loop(monkeypatch, module, coro_fn, iterations: int):
    """Run coro_fn() with its sleeps shortened; return once it has slept `iterations` times.

    Fails if the loop task exits (i.e. died) before that.
    """
    slept = 0
    reached = asyncio.Event()

    async def fake_sleep(_delay):
        nonlocal slept
        slept += 1
        if slept >= iterations:
            reached.set()
            await _real_sleep(3600)   # park; the test cancels the loop
        await _real_sleep(0)

    monkeypatch.setattr(module.asyncio, "sleep", fake_sleep)
    task = asyncio.ensure_future(coro_fn())
    waiter = asyncio.ensure_future(reached.wait())
    await asyncio.wait({task, waiter}, timeout=5, return_when=asyncio.FIRST_COMPLETED)
    died = task.done()
    err = task.exception() if died and not task.cancelled() else None
    task.cancel()
    waiter.cancel()
    await asyncio.gather(task, waiter, return_exceptions=True)
    assert not died, f"loop exited after {slept} sleeps: {err!r}"
    return slept


def _task(tid, overdue=True):
    ahead = 0.0 if overdue else time.time() + 3600
    return SimpleNamespace(id=tid, status="running", waiting_approval=False, started=ahead, paused_s=0.0,
                           last_progress=ahead, repeat_history={}, recent_calls=[])


@pytest.fixture
def cancelled(monkeypatch):
    calls = []
    monkeypatch.setattr(router, "cancel", lambda tid, reason: calls.append(tid) or "")
    monkeypatch.setitem(CFG["limits"], "watchdog_interval_s", 0)
    monkeypatch.setattr(router, "TASKS", {})
    return calls


async def test_watchdog_survives_exception_in_iteration(monkeypatch, cancelled, caplog):
    boom = {"n": 0}

    def tokens_today():
        boom["n"] += 1
        if boom["n"] == 1:
            raise RuntimeError("db locked")
        return 0

    # Healthy task: only the token-budget check is reached.
    router.TASKS[1] = _task(1, overdue=False)
    monkeypatch.setattr(memory, "tokens_today", tokens_today)
    with caplog.at_level(logging.ERROR, logger="osa.watchdog"):
        await _run_loop(monkeypatch, watchdog, watchdog.watchdog, iterations=3)
    assert boom["n"] >= 2   # iteration 2 ran after iteration 1 raised
    assert any("watchdog" in r.getMessage() for r in caplog.records)


async def test_watchdog_bad_task_does_not_skip_others(monkeypatch, cancelled):
    class Broken:
        id = 1
        waiting_approval = False

        @property
        def status(self):
            raise RuntimeError("corrupt task")

    router.TASKS[1] = Broken()
    router.TASKS[2] = _task(2)
    await _run_loop(monkeypatch, watchdog, watchdog.watchdog, iterations=2)
    assert 2 in cancelled


async def test_prune_loop_survives_exception(monkeypatch, caplog):
    calls = {"n": 0}

    def prune():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("disk I/O error")

    monkeypatch.setattr(tasklog, "prune", prune)
    with caplog.at_level(logging.ERROR, logger="osa.tasklog"):
        await _run_loop(monkeypatch, tasklog, tasklog.prune_loop, iterations=3)
    assert calls["n"] >= 2
    assert any("prune" in r.getMessage() for r in caplog.records)


async def test_embed_loop_survives_db_error_while_saving(monkeypatch, caplog):
    class Conn:
        def __init__(self):
            self.updates = 0

        def execute(self, sql, args=()):
            if sql.startswith("update"):
                self.updates += 1
                raise RuntimeError("database is locked")
            return SimpleNamespace(fetchall=lambda: [(1, "t", "x")])

        def commit(self):
            pass

    async def fake_embed(texts):
        return [[1.0, 0.0] for _ in texts]

    fake = Conn()
    monkeypatch.setattr(search, "conn", fake)
    monkeypatch.setattr(search, "embed", fake_embed)
    monkeypatch.setattr(search, "embed_config", lambda: {"provider": "p", "model": "m"})
    search._wake.set()
    with caplog.at_level(logging.ERROR, logger="osa.search"):
        await _run_loop(monkeypatch, search, search.embed_loop, iterations=1)
    assert fake.updates == 1   # failed once, backed off, loop still alive
    assert any("embed_loop" in r.getMessage() for r in caplog.records)
