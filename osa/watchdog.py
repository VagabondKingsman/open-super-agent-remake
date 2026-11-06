"""Watchdog：独立于 Worker 的定时巡检。发现超时、无进展、重复调用（死循环）或超预算时取消任务并通知。"""

from .i18n import s as _s
import asyncio
import time
from .config import CFG
from . import memory


async def watchdog():
    from .router import TASKS, cancel
    lim = CFG["limits"]
    while True:
        await asyncio.sleep(lim["watchdog_interval_s"])
        now = time.time()
        for t in list(TASKS.values()):
            if t.status != "running":
                continue
            if t.waiting_approval:  # 在等用户确认，不算超时或卡死
                t.last_progress = now
                continue
            reason = None
            if now - t.started - t.paused_s > lim["task_timeout_s"]:
                reason = _s('audit_68e625e03f', v0=lim['task_timeout_s'])
            elif now - t.last_progress > 180:
                reason = _s('audit_ab5193747b')
            elif len(t.recent_calls) >= 4 and len(set(t.recent_calls[-4:])) == 1:
                reason = _s('audit_bc864269ea')
            elif memory.tokens_today() > lim["daily_token_budget"]:
                reason = _s('audit_339ee90e46')
            if reason:
                cancel(t.id, f"Watchdog：{reason}")
