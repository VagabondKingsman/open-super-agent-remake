"""把重启推后到「没有一轮对话、没有任务在跑」的时候。

重启会掐掉正在跑的一轮：Bot 的答复只发了一半，Worker 的步骤停在中间。等它闲下来再换进程就没有这个损失，
代价只是多等一会儿（上限见 max_wait）。判「忙」看两处：Router 每一轮握着的锁，和正在跑的任务。
"""
import asyncio
import time

QUIET = 8.0          # 要连续安静这么久才算闲：两轮之间、任务收尾的空档不算
POLL = 2.0


def busy() -> bool:
    """有没有在一轮对话里，或有没有任务在跑。"""
    from . import router as rt
    if any(t.status == "running" for t in rt.TASKS.values()):
        return True
    return any(getattr(r, "lock", None) is not None and r.lock.locked() for r in rt.RUNTIMES.values())


def waiting() -> dict:
    """给界面和脚本看的一句话：还有几个任务、几轮对话在跑。"""
    from . import router as rt
    tasks = [t.id for t in rt.TASKS.values() if t.status == "running"]
    turns = [b for b, r in rt.RUNTIMES.items() if r.lock.locked()]
    return {"busy": bool(tasks or turns), "tasks": tasks, "turns": turns}


async def wait_until_idle(max_wait: float = 1800.0) -> bool:
    """安静下来返回 True；等到 max_wait 还忙着返回 False（调用方决定要不要照样重启）。"""
    end = time.monotonic() + max_wait
    quiet_since = None
    while time.monotonic() < end:
        if busy():
            quiet_since = None
        elif quiet_since is None:
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since >= QUIET:
            return True
        await asyncio.sleep(POLL)
    return False
