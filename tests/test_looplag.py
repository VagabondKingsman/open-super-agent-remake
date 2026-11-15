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
    """时钟替身，演“整台机器被暂停”：暂停期间两个钟都不走，醒来时墙上时间一次补上，单调钟不补。"""

    def __init__(self):
        self.t0 = time.monotonic()
        self.held = 0.0          # 累计停掉的时长
        self.paused_at = None
        self.until = None
        self.wall_at = None

    def pause(self, seconds):
        self.paused_at = time.monotonic()
        self.until = self.paused_at + seconds
        self.wall_at = time.time() + self.held

    def _resume(self):
        if self.paused_at is not None and time.monotonic() >= self.until:
            self.held += self.until - self.paused_at
            self.paused_at = None

    def monotonic(self):
        if self.paused_at is not None:
            if time.monotonic() < self.until:
                return self.paused_at - self.t0 - self.held
            self._resume()
        return time.monotonic() - self.t0 - self.held

    def time(self):
        if self.paused_at is not None and time.monotonic() < self.until:
            return self.wall_at
        self._resume()
        return time.time() + self.held


async def test_a_paused_machine_warns_even_though_the_loop_never_blocked(monkeypatch, caplog):
    dumps, clock = [], _Clock()
    monkeypatch.setattr(looplag, "time", clock)
    monkeypatch.setattr(looplag.faulthandler, "dump_traceback", lambda **kw: dumps.append(kw))
    with caplog.at_level(logging.WARNING, logger="osa.looplag"):
        task = asyncio.create_task(looplag.watch(limit_s=0.1, sample_s=0.02, again_s=0.5))
        await asyncio.sleep(0.1)          # 先把点打起来
        clock.pause(0.4)                  # 机器停 0,4 秒：循环、巡检线程都停
        await asyncio.sleep(0.45)         # 真时间过去，巡检在暂停中醒过、也在暂停后醒过
        await asyncio.sleep(0.1)
        task.cancel()
        with __import__("pytest").raises(asyncio.CancelledError):
            await task
    msgs = [r.message for r in caplog.records if "暂停" in r.message]
    assert msgs, f"整机被暂停时没有 WARNING：{[r.message for r in caplog.records]}"
    assert "事件循环本身没被堵" in msgs[0]
    assert dumps, "没有把栈打出来"
