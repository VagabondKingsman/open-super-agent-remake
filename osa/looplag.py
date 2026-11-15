"""事件循环的心跳巡检：循环被同步代码堵住时，把当时所有线程的栈打进日志。

2026-11-14 09:38 任务 #1610：模型调用在等流，进程却 11 分钟没有一行日志（连每 60 秒一次的机器轮询都停了），
Watchdog 只看到“900 秒没有进展”，取消任务，答案丢了。流的 60 秒上限救不了——循环被堵住时，计时器也跑不起来。
所以量心跳的活儿交给一个普通线程：异步这边每秒打一次点，线程发现点变旧就记 WARNING，并把主线程此刻的栈
（faulthandler 打全部线程）写进日志。一条 WARNING 加一份栈，比“900 秒没有进展”能查得多。

还有一个不同的病：整台机器被暂停（VM 被宿主冻住、休眠），这时事件循环没被堵，单调钟也不走，只看单调钟会
一条都不报。所以两个钟一起量，墙上时间明显多于单调钟时按“整机被暂停”记，并说明栈是事后打的。
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
        # 两个钟一起量：进程被同步代码堵住时两个钟一起走；整台机器被暂停（VM 被宿主冻住、休眠）时
        # 只有一个走——单调钟在暂停期间不累积，墙上时间却被补上。只看单调钟的话，2026-11-14 那种
        # 672 秒整机冻结压根不会报警：睡醒时 monotonic 只前进了几毫秒。
        stale = max(0.0, time.monotonic() - beat["t"])
        slept = max(0.0, time.time() - beat["wall"])
        if stale <= limit and slept <= limit:
            dumped_at = None if stale < limit / 2 else dumped_at
            continue
        if dumped_at is not None and max(stale, slept) - dumped_at < again_s:
            continue
        dumped_at = max(stale, slept)
        if slept - stale > limit:   # 墙上时间比单调钟多走的量本身超过阈值：不是时钟微调，是整机被停过
            # 栈是醒过来以后打的，看不出是谁堵的，只说明机器被停过
            log.warning("整台机器被暂停了 %.1f 秒（墙上时间走了这么多，单调钟只走 %.1f 秒；事件循环本身没被堵）。"
                        "下面的栈是恢复之后打的，不一定指向原因", slept, stale)
        else:
            log.warning("事件循环被堵住 %.1f 秒（计时器、巡检、流上限在这期间都不走），下面是当时的栈", stale)
        _dump()


async def watch(limit_s: float | None = None, sample_s: float = 1.0, again_s: float = 60.0):
    """常驻巡检。limit_s 不给就看 limits.loop_lag_s（每轮现读，改了不用重启）。"""
    beat = {"t": time.monotonic(), "wall": time.time()}
    stop = threading.Event()
    th = threading.Thread(target=_probe, args=(beat, stop, limit_s, sample_s, again_s), daemon=True, name="looplag")
    th.start()
    try:
        while True:
            await asyncio.sleep(min(sample_s, 1.0))
            beat["t"], beat["wall"] = time.monotonic(), time.time()
    finally:
        stop.set()
