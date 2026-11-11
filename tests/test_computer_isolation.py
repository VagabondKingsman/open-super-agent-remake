"""B4: one Chromium profile per task. Two tasks on the same computer must not see each other's cookies, and a finished
task's profile is thrown away (the next task starts clean)."""
from types import SimpleNamespace

import pytest

from osa.computer import cdp_helper as cdp
from osa.computer.base import Computer, ExecResult


class FakeBrowser(Computer):
    backend = "local"

    def __init__(self, bot_id: int = 1):
        super().__init__(bot_id)
        self.ops: list[dict] = []
        self.contexts_made = 0

    async def status(self) -> dict:
        return {"state": "running"}

    async def start(self):
        pass

    async def exec(self, cmd: str, timeout: int = 120, stdin: str | None = None) -> ExecResult:
        return ExecResult(0, "", "")

    async def _helper_run(self, payload: dict) -> dict:
        self.ops.append(payload)
        if payload["op"] == "window":
            if not payload["win"].get("isolate"):     # 脚本不隔离时返回空 context（同 cdp_helper.Ctx）
                return {"window": 100, "browser": "b1", "context": "", "ok": True}
            self.contexts_made += 1
            ctx = payload["win"].get("context") or f"ctx-{self.contexts_made}"
            return {"window": 100 + self.contexts_made, "browser": "b1", "context": ctx, "ok": True}
        return {"window": payload.get("win", {}).get("id") or 100, "browser": "b1",
                "context": payload.get("win", {}).get("context", ""), "ok": True}


def task(key: str, label: str = ""):
    return key, label or f"task {key}"


async def test_two_tasks_get_their_own_profile(monkeypatch):
    c = FakeBrowser()
    for key in ("9", "10"):
        await c.claim(key, f"task {key}")
        await c.browser("open", key=key, url="https://example.com")
    wins = [o["win"] for o in c.ops if o["op"] == "window"]
    assert [w["isolate"] for w in wins] == [True, True]
    assert [w["context"] for w in wins] == ["", ""]                 # 两个任务第一次都是空：各开各的
    assert c.contexts == {"9": "ctx-1", "10": "ctx-2"}              # 互不相同
    # 之后的动作带着自己的 profile
    await c.browser("read", key="9")
    last = [o for o in c.ops if o["op"] == "read"][-1]
    assert last["win"]["context"] == "ctx-1"


async def test_a_finished_task_takes_its_profile_with_it():
    c = FakeBrowser()
    await c.claim("9", "task 9")
    await c.browser("open", key="9", url="https://example.com")
    await c.release("9")
    await __import__("asyncio").gather(*[])                            # 让后台的关闭跑一会儿
    import asyncio
    for _ in range(20):
        if any(o["op"] == "close_context" for o in c.ops):
            break
        await asyncio.sleep(0.01)
    closed = [o for o in c.ops if o["op"] == "close_context"]
    assert closed and closed[0]["context"] == "ctx-1" and "9" not in c.contexts


async def test_your_own_computer_is_not_isolated(monkeypatch):
    """本机电脑上不隔离：那里的 Chrome 就是给你用你登录过的网站的。"""
    c = FakeBrowser()
    c.backend = "host"
    await c.claim("9", "task 9")
    await c.browser("open", key="9", url="https://example.com")
    assert [o for o in c.ops if o["op"] == "window"][0]["win"]["isolate"] is False
    assert not c.contexts


async def test_isolation_can_be_turned_off(monkeypatch):
    from osa.config import CFG
    monkeypatch.setitem(CFG["computer"], "isolate_tasks", False)
    c = FakeBrowser()
    await c.claim("9", "task 9")
    await c.browser("open", key="9", url="https://example.com")
    assert [o for o in c.ops if o["op"] == "window"][0]["win"]["isolate"] is False


def test_the_window_is_created_inside_that_profile(monkeypatch):
    """cdp_helper：新窗口开在这个任务的 profile 里；profile 被浏览器重开弄没了就换一个新的（不让人做不了事）。"""
    calls = []

    class B:
        def call(self, method, params=None):
            calls.append((method, params or {}))
            if method == "Target.createTarget":
                if params.get("browserContextId") == "gone":
                    raise RuntimeError("Failed to find browser context")
                return {"targetId": "t1"}
            if method == "Target.createBrowserContext":
                return {"browserContextId": "fresh"}
            if method == "Browser.getWindowForTarget":
                return {"windowId": 7}
            return {}

    monkeypatch.setattr(cdp, "_targets", lambda timeout=2: [{"id": "t1", "url": "about:blank"}])
    ctx = cdp.Ctx.__new__(cdp.Ctx)
    ctx.b = B()
    ctx.context = "c1"
    t, w = ctx.new_window(None, "c1")
    assert w == 7 and t["id"] == "t1"
    assert calls[0] == ("Target.createTarget", {"url": "about:blank", "newWindow": True, "browserContextId": "c1"})

    calls.clear()
    ctx.context = "gone"
    ctx.new_window(None, "gone")                     # 记着的 profile 没了：新建一个再开窗口
    assert ("Target.createBrowserContext", {"disposeOnDetach": False}) in calls
    made = [p for m, p in calls if m == "Target.createTarget"]
    assert made[-1]["browserContextId"] == "fresh" and ctx.context == "fresh"
