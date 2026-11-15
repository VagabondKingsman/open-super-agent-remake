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


class _Clock:
    """时钟替身：能让单调钟停住、只让墙上时间走（整台机器被暂停就是这个样子）。"""

    def __init__(self):
        self.frozen = 0.0
        self.skew = 0.0

    def monotonic(self):
        return time.monotonic() - self.frozen

    def time(self):
        return time.time() + self.skew


async def test_a_paused_machine_warns_even_though_the_loop_never_blocked(monkeypatch, caplog):
    dumps, clock = [], _Clock()
    monkeypatch.setattr(looplag, "time", clock)
    monkeypatch.setattr(looplag.faulthandler, "dump_traceback", lambda **kw: dumps.append(kw))
    with caplog.at_level(logging.WARNING, logger="osa.looplag"):
        task = asyncio.create_task(looplag.watch(limit_s=0.1, sample_s=0.02, again_s=0.5))
        await asyncio.sleep(0.1)
        clock.frozen, clock.skew = 0.4, 0.4   # 机器被冻 0,4 秒：单调钟不动，墙上时间补上
        await asyncio.sleep(0.1)
        task.cancel()
        with __import__("pytest").raises(asyncio.CancelledError):
            await task
    msgs = [r.message for r in caplog.records if "暂停" in r.message]
    assert msgs, f"整机被暂停时没有 WARNING：{[r.message for r in caplog.records]}"
    assert "事件循环本身没被堵" in msgs[0]
    assert dumps, "没有把栈打出来"


async def test_a_blocked_loop_is_not_called_a_paused_machine(caplog):
    with caplog.at_level(logging.WARNING, logger="osa.looplag"):
        task = asyncio.create_task(looplag.watch(limit_s=0.1, sample_s=0.02, again_s=0.5))
        await asyncio.sleep(0.1)
        time.sleep(0.35)      # 只有单调钟和墙上时间一起走
        await asyncio.sleep(0.1)
        task.cancel()
        with __import__("pytest").raises(asyncio.CancelledError):
            await task
    assert any("堵住" in r.message for r in caplog.records)
    assert not [r for r in caplog.records if "暂停" in r.message]
