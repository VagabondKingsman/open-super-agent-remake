"""任务计时用的钟：整台机器被暂停时（VM 被宿主冻住、休眠）也不走。

`time.time()` 跟着墙上时间走。这台箱 2026-11-15 一天里被冻了十几次（最长 38 分钟，`looplag` 逐条记了）：
一觉醒来，`now - last_progress` 一下多出一个小时，Watchdog 把所有在跑的任务一起取消，全都不该取消。
所以超时、间隔这类“任务跑了多久”一律用这个钟；要给人看的时刻（几点了、过期时间）仍旧用 `time.time()`。
"""
import time


def now() -> float:
    return time.monotonic()


def gap(a: float, b: float) -> float:
    """两个时刻隔了多久（秒），负数取 0：钟换过、数从旧版本继承来时别给出负的用时。"""
    return max(0.0, b - a)
