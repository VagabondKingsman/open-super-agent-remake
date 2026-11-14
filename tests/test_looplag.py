"""事件循环被堵住时要留下能被查的东西：一条 WARNING 加一份栈。"""
import asyncio
import logging
import time

from osa import looplag


def test_limit_comes_from_limits(monkeypatch):
    monkeypatch.setitem(looplag.CFG["limits"], "loop_lag_s", 3)
    assert looplag.lag_limit_s() == 3
    monkeypatch.setitem(looplag.CFG["limits"], "loop_lag_s", 0)
    assert looplag.lag_limit_s() == 0   # 0 = 不查
    looplag.CFG["limits"].pop("loop_lag_s", None)
    assert looplag.lag_limit_s() == 5   # 默认


async def test_blocked_loop_warns_and_dumps_a_stack(monkeypatch, caplog):
    dumps = []
    monkeypatch.setattr(looplag.faulthandler, "dump_traceback", lambda **kw: dumps.append(kw))
    with caplog.at_level(logging.WARNING, logger="osa.looplag"):
        task = asyncio.create_task(looplag.watch(limit_s=0.1, sample_s=0.02, again_s=0.5))
        await asyncio.sleep(0.1)      # 先把点打起来
        time.sleep(0.35)              # 同步堵住循环
        await asyncio.sleep(0.1)
        task.cancel()
        with __import__("pytest").raises(asyncio.CancelledError):
            await task
    assert any("堵住" in r.message for r in caplog.records), "循环被堵住时没有 WARNING"
    assert dumps, "没有把栈打出来"


async def test_a_healthy_loop_stays_quiet(caplog):
    with caplog.at_level(logging.WARNING, logger="osa.looplag"):
        task = asyncio.create_task(looplag.watch(limit_s=5, sample_s=0.02))
        await asyncio.sleep(0.15)
        task.cancel()
        with __import__("pytest").raises(asyncio.CancelledError):
            await task
    assert not [r for r in caplog.records if "堵住" in r.message]
