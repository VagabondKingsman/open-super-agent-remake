"""超时看的是“任务跑了多久”，不是墙上时间：机器被冻住一小时（VM 被宿主暂停），醒来时在跑的任务
不能被 Watchdog 当成卡死全部取消。2026-11-15 这台箱一天被冻了十几次，最长 38 分钟，looplag 逐条记了。"""
import asyncio
import time
from types import SimpleNamespace

from osa import clock, router, watchdog
from osa.config import CFG

_real_sleep = asyncio.sleep


async def _run_once(monkeypatch, iterations: int = 2):
    slept = 0

    async def fake_sleep(_delay):
        nonlocal slept
        slept += 1
        if slept >= iterations:
            raise asyncio.CancelledError
        await _real_sleep(0)

    monkeypatch.setattr(watchdog.asyncio, "sleep", fake_sleep)
    try:
        await watchdog.watchdog()
    except asyncio.CancelledError:
        pass


def _task(started: float, last_progress: float):
    return SimpleNamespace(id=1, status="running", waiting_approval=False, started=started, paused_s=0.0,
                           last_progress=last_progress, repeat_history={}, recent_calls=[])


def _setup(monkeypatch):
    cancelled = []
    monkeypatch.setattr(router, "cancel", lambda tid, reason: cancelled.append((tid, reason)) or "")
    monkeypatch.setitem(CFG["limits"], "task_timeout_s", 60)
    monkeypatch.setitem(CFG["limits"], "no_progress_s", 30)
    monkeypatch.setattr(router, "TASKS", {})
    return cancelled


async def test_a_long_machine_pause_does_not_cancel_a_fresh_task(monkeypatch):
    cancelled = _setup(monkeypatch)
    now = clock.now()
    real = time.time
    router.TASKS[1] = _task(now - 2, now - 2)      # mới chạy 2 giây (theo đồng hồ không tính lúc máy ngủ)
    # 替换掉以后 lambda 里不能再叫 time.time()（会自己递归）
    monkeypatch.setattr(time, "time", lambda: real() + 2400)   # 40 phút trôi qua lúc máy bị treo
    await _run_once(monkeypatch)
    assert cancelled == []


async def test_a_task_that_really_ran_too_long_is_cancelled(monkeypatch):
    cancelled = _setup(monkeypatch)
    now = clock.now()
    router.TASKS[1] = _task(now - 120, now - 120)
    await _run_once(monkeypatch)
    assert cancelled and cancelled[0][0] == 1 and "60" in cancelled[0][1]


async def test_no_progress_uses_the_same_clock(monkeypatch):
    cancelled = _setup(monkeypatch)
    now = clock.now()
    router.TASKS[1] = _task(now - 5, now - 45)     # 总时长没到，但 45 秒没动了
    await _run_once(monkeypatch)
    assert cancelled and "30" in cancelled[0][1]


def test_the_fields_start_on_the_pause_free_clock():
    from osa.worker import Task
    t = Task(id=1, goal="x")
    assert t.started <= clock.now() + 1 and t.last_progress <= clock.now() + 1
    assert t.started > 0
