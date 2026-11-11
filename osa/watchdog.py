"""Watchdog：独立于 Worker 的定时巡检。发现超时、无进展、重复调用（死循环）或超预算时取消任务并通知。"""
import asyncio
import logging
import time
from .config import CFG
from . import i18n, memory

log = logging.getLogger(__name__)


def no_progress_s() -> float:
    """多久没有进展才算卡住。必须**长于**最长的流界限（first chunk 170 秒 / 头 120 秒），
    否则流刚要重来，任务先被取消了：任务 247 的 189 秒就是这样——上限比 C19 的 120 秒头更短，
    重来还没开始就被 Watchdog 收走。"""
    return float(CFG["limits"].get("no_progress_s", 300) or 300)


def _stuck_loop(task) -> bool:
    """按每个 Worker 自己的历史看。Heavy 并行时不能把三个人的第一次调用拼成一次死循环。"""
    histories = list((getattr(task, "repeat_history", None) or {}).values()) or [getattr(task, "recent_calls", [])]
    return any(len(h) >= 4 and len(set(h[-4:])) == 1 for h in histories)


async def watchdog():
    from .router import TASKS, cancel
    lim = CFG["limits"]
    while True:
        await asyncio.sleep(lim["watchdog_interval_s"])
        now = time.time()
        for t in list(TASKS.values()):
            try:   # per task: one failure must not skip the other tasks or end the loop
                if t.status != "running":
                    continue
                if t.waiting_approval:  # 在等用户确认，不算超时或卡死
                    t.last_progress = now
                    continue
                reason = None
                if now - t.started - t.paused_s > lim["task_timeout_s"]:
                    reason = i18n.t("运行超过 {n} 秒", n=lim["task_timeout_s"])
                elif now - t.last_progress > no_progress_s():
                    reason = i18n.t("{n} 秒没有进展", n=f"{no_progress_s():g}")
                elif _stuck_loop(t):
                    reason = i18n.t("连续重复同一个工具调用，疑似死循环")
                elif memory.tokens_today() > lim["daily_token_budget"]:
                    reason = i18n.t("今日 token 预算用完")
                if reason:
                    cancel(t.id, i18n.t("Watchdog：{reason}", reason=reason))
            except Exception:
                log.exception("watchdog: checking task %s failed", getattr(t, "id", "?"))
