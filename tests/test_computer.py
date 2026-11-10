"""电脑的控制权：用户接手期间 Bot 的动作等着；交还后，依赖页面的动作不照原样做。"""
import asyncio

import pytest

from osa.computer.base import Computer, ComputerError, ExecResult


class FakeComputer(Computer):
    """不连真的电脑：浏览器控制脚本收到的动作记在 ops 里。"""
    backend = "fake"

    def __init__(self):
        super().__init__(0)
        self.ops: list[str] = []

    async def status(self) -> dict:
        return {"state": "running"}

    async def start(self):
        pass

    async def exec(self, cmd: str, timeout: int = 120, stdin: str | None = None) -> ExecResult:
        return ExecResult(0, "", "")

    async def _helper_run(self, payload: dict) -> dict:
        self.ops.append(payload["op"])
        return {"window": 1, "browser": "b1", "ok": True}


async def test_page_actions_are_not_replayed_after_handback():
    c = FakeComputer()
    await c.browser("snapshot", key="chat-1")
    c.takeover()
    click = asyncio.create_task(c.browser("click", key="chat-1", ref=3))
    typing = asyncio.create_task(c.browser("type", key="chat-1", ref=4, text="你好"))
    read = asyncio.create_task(c.browser("read", key="chat-1"))
    opening = asyncio.create_task(c.browser("open", key="chat-1", url="https://example.com"))
    await asyncio.sleep(0.05)
    assert not any(t.done() for t in (click, typing, read, opening))   # 你接手期间都等着
    assert c.ops == ["window", "snapshot"]

    c.handback()
    for t in (click, typing):
        with pytest.raises(ComputerError, match="用户刚接手过电脑"):
            await t
    await read       # 只读的照常做
    await opening    # 打开网址不看当前页面，照常做
    assert "click" not in c.ops and "type" not in c.ops
    assert "read" in c.ops and "open" in c.ops

    await c.browser("click", key="chat-1", ref=3)   # 没人接手时照常做
    assert c.ops[-1] == "click"


async def test_human_actions_go_through_while_holding_control():
    c = FakeComputer()
    c.takeover()
    await asyncio.wait_for(c.browser("front", key="chat-1", as_human=True), 1)   # 你自己点的“看这个”不用等
    assert c.ops[-1] == "front"
    c.handback()


# ---------- B4：Worker 在 Instabox / Docker 上也能看整个屏幕 ----------
class ShotComputer(FakeComputer):
    backend = "instabox"

    def __init__(self):
        super().__init__()
        self.calls: list[str] = []

    async def page_shot(self, key: str) -> bytes:
        self.calls.append("page_shot")
        return _png(500, 136)

    async def look(self):
        self.calls.append("look")
        return _png(1280, 800), "Example Domain - Chromium"

    async def claim(self, *a, **kw):
        pass


def _png(w: int, h: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + w.to_bytes(4, "big") + h.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"


async def _noop(_):
    pass


class _Task:
    id, bot_id, background = 1, 1, False


async def test_worker_screenshot_screen_flag_uses_whole_screen(monkeypatch):
    from osa.computer import tools as ctools
    c = ShotComputer()
    monkeypatch.setattr(ctools, "get", lambda: c)
    text, png = await ctools.call(_Task(), "computer_screenshot", {"screen": True}, _noop, key="1")
    assert c.calls == ["look"] and "whole screen" in text and "Example Domain" in text
    msg = ctools.image_message(png)
    assert "1280x800" in msg["content"][0]["text"] and "do not click" in msg["content"][0]["text"]

    text, png = await ctools.call(_Task(), "computer_screenshot", {}, _noop, key="1")
    assert c.calls == ["look", "page_shot"] and "current page" in text
    assert "click coordinates use this size" in ctools.image_message(png)["content"][0]["text"]


def test_screen_flag_only_offered_off_host():
    from osa.computer import tools as ctools
    c = ShotComputer()
    s = next(x for x in ctools.schemas(c) if x["function"]["name"] == "computer_screenshot")
    assert "screen" in s["function"]["parameters"]["properties"]
    host = ShotComputer()
    host.backend = "host"
    host.shell_enabled = lambda: False
    host.desktop_enabled = lambda: False
    s = next(x for x in ctools.schemas(host) if x["function"]["name"] == "computer_screenshot")
    assert "screen" not in s["function"]["parameters"]["properties"] and "screen=true" not in s["function"]["description"]


async def test_host_ignores_screen_flag(monkeypatch):
    from osa.computer import tools as ctools
    c = ShotComputer()
    c.backend = "host"
    monkeypatch.setattr(ctools, "get", lambda: c)
    text, _ = await ctools.call(_Task(), "computer_screenshot", {"screen": True}, _noop, key="1")
    assert c.calls == ["page_shot"] and "current page" in text
