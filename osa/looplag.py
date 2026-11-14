"""事件循环的心跳巡检：循环被同步代码堵住时，把当时所有线程的栈打进日志。

2026-11-14 09:38 任务 #1610：模型调用在等流，进程却 11 分钟没有一行日志（连每 60 秒一次的机器轮询都停了），
Watchdog 只看到“900 秒没有进展”，取消任务，答案丢了。流的 60 秒上限救不了——循环被堵住时，计时器也跑不起来。
所以量心跳的活儿交给一个普通线程：异步这边每秒打一次点，线程发现点变旧就记 WARNING，并把主线程此刻的栈
（faulthandler 打全部线程）写进日志。一条 WARNING 加一份栈，比“900 秒没有进展”能查得多。
"""
import asyncio
import faulthandler
import logging
import sys
import threading
import time

from .config import CFG

log = logging.getLogger(__name__)


def lag_limit_s() -> float:
    """心跳超过这么多秒没动就算循环被堵（limits.loop_lag_s，默认 5；0 表示不查）。"""
    return max(0.0, float(CFG["limits"].get("loop_lag_s", 5) or 0))


def _dump() -> None:
    """把现在所有线程的栈打到 stderr（systemd 已把它接在同一个日志文件上）。打不出来也不能影响巡检。"""
    try:
        faulthandler.dump_traceback(file=sys.stderr)
    except Exception:   # noqa: BLE001
        log.warning("looplag: 打不出栈", exc_info=True)


def _probe(beat: dict, stop: threading.Event, limit_s: float | None, sample_s: float, again_s: float) -> None:
    dumped_at = None
    while not stop.wait(sample_s):
        limit = lag_limit_s() if limit_s is None else limit_s
        if not limit:
            continue
        stale = time.monotonic() - beat["t"]
        if stale <= limit:
            dumped_at = None if stale < limit / 2 else dumped_at
            continue
        if dumped_at is not None and stale - dumped_at < again_s:
            continue
        dumped_at = stale
        log.warning("事件循环被堵住 %.1f 秒（计时器、巡检、流上限在这期间都不走），下面是当时的栈", stale)
        _dump()


async def watch(limit_s: float | None = None, sample_s: float = 1.0, again_s: float = 60.0):
    """常驻巡检。limit_s 不给就看 limits.loop_lag_s（每轮现读，改了不用重启）。"""
    beat = {"t": time.monotonic()}
    stop = threading.Event()
    th = threading.Thread(target=_probe, args=(beat, stop, limit_s, sample_s, again_s), daemon=True, name="looplag")
    th.start()
    try:
        while True:
            await asyncio.sleep(min(sample_s, 1.0))
            beat["t"] = time.monotonic()
    finally:
        stop.set()
