"""电脑的控制权：用户接手期间 Bot 的动作等着；交还后，依赖页面的动作不照原样做。"""
import asyncio

import pytest

from osa import approvals
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


# ---------- TIP-04b：任务窗口太小（510x267，页面截图只剩 500x136）就放大到 computer.width / height ----------
class FakeBrowserWS:
    def __init__(self, bounds: dict):
        self.bounds = dict(bounds)
        self.calls: list[tuple[str, dict]] = []

    def call(self, method: str, params: dict | None = None):
        self.calls.append((method, params or {}))
        if method == "Browser.getWindowBounds":
            return {"bounds": dict(self.bounds)}
        if method == "Browser.setWindowBounds":
            self.bounds.update(params["bounds"])
            return {}
        raise AssertionError(method)


def _ctx(bounds: dict):
    from osa.computer import cdp_helper
    ctx = object.__new__(cdp_helper.Ctx)
    ctx.b = FakeBrowserWS(bounds)
    return ctx


def test_small_task_window_is_enlarged(monkeypatch):
    from osa.computer import cdp_helper
    monkeypatch.setattr(cdp_helper.time, "sleep", lambda s: None)
    ctx = _ctx({"left": -5, "top": 10, "width": 510, "height": 267, "windowState": "normal"})
    assert ctx.fit(7, [1280, 800]) is True
    # 屏幕就是 1280x800：放大后的窗口贴着左上角，不能往下跑出屏幕（AUDIT-F4）
    assert ctx.b.bounds == {"left": 0, "top": 0, "width": 1280, "height": 800, "windowState": "normal"}
    sets = [p for m, p in ctx.b.calls if m == "Browser.setWindowBounds"]
    assert sets == [{"windowId": 7, "bounds": {"left": 0, "top": 0, "width": 1280, "height": 800}}]


def test_enlarged_window_clamped_on_screen(monkeypatch):
    """AUDIT-F4：小窗口在右下角（1000,600），放大到 1280x800 后整个窗口还在屏幕里。"""
    from osa.computer import cdp_helper
    monkeypatch.setattr(cdp_helper.time, "sleep", lambda s: None)
    ctx = _ctx({"left": 1000, "top": 600, "width": 510, "height": 267, "windowState": "normal"})
    assert ctx.fit(3, [1280, 800]) is True
    b = ctx.b.bounds
    assert b["left"] >= 0 and b["top"] >= 0
    assert b["left"] + b["width"] <= 1280 and b["top"] + b["height"] <= 800


def test_fit_respects_real_screen_smaller_than_settings(monkeypatch):
    """Live trên Instabox: màn hình VNC bị đổi thành 661x1619. Chỉ phóng tới bề ngang màn hình,
    lần sau không phóng lại nữa (trước đây mỗi thao tác đều setWindowBounds + chờ 0,3 giây)."""
    from osa.computer import cdp_helper
    monkeypatch.setattr(cdp_helper.time, "sleep", lambda s: None)
    ctx = _ctx({"left": 628, "top": 600, "width": 510, "height": 267, "windowState": "normal"})
    assert ctx.fit(5, [1280, 800], (661, 1619)) is True
    b = ctx.b.bounds
    assert (b["left"], b["width"], b["height"]) == (0, 661, 800)
    assert b["top"] + b["height"] <= 1619
    ctx.b.calls.clear()
    assert ctx.fit(5, [1280, 800], (661, 1619)) is False
    assert not [c for c in ctx.b.calls if c[0] == "Browser.setWindowBounds"]


def test_fit_bounds_keeps_position_when_it_fits():
    from osa.computer.cdp_helper import fit_bounds
    # 只是矮了：宽度够，位置不用动
    assert fit_bounds({"left": 0, "top": 0, "width": 1280, "height": 300}, 1280, 800) == \
        {"left": 0, "top": 0, "width": 1280, "height": 800}
    # 比屏幕还宽的窗口：贴左边
    assert fit_bounds({"left": 50, "top": 20, "width": 1400, "height": 200}, 1280, 800) == \
        {"left": 0, "top": 0, "width": 1400, "height": 800}
    # 负坐标（窗口一部分在屏幕左上外面）也拉回来
    assert fit_bounds({"left": -40, "top": -10, "width": 400, "height": 300}, 1920, 1080) == \
        {"left": 0, "top": 0, "width": 1920, "height": 1080}


def test_big_or_maximized_window_left_alone(monkeypatch):
    from osa.computer import cdp_helper
    monkeypatch.setattr(cdp_helper.time, "sleep", lambda s: None)
    ok = _ctx({"left": 0, "top": 0, "width": 1920, "height": 1032, "windowState": "normal"})
    assert ok.fit(1, [1280, 800]) is False and not [c for c in ok.b.calls if c[0] == "Browser.setWindowBounds"]
    maxed = _ctx({"left": 0, "top": 0, "width": 400, "height": 300, "windowState": "maximized"})
    assert maxed.fit(1, [1280, 800]) is False and not [c for c in maxed.b.calls if c[0] == "Browser.setWindowBounds"]
    mini = _ctx({"left": 0, "top": 0, "width": 400, "height": 300, "windowState": "minimized"})
    assert mini.fit(1, [1280, 800]) is True and mini.b.bounds["width"] == 1280 and mini.b.bounds["windowState"] == "normal"


def test_window_size_sent_off_host_only(monkeypatch):
    from osa.config import CFG
    monkeypatch.setitem(CFG, "computer", {**CFG["computer"], "width": 1280, "height": 800})
    c = FakeComputer()
    c.backend = "instabox"
    c.width, c.height = 1920, 1080
    c.users["t1"] = {"label": "t", "window": None}
    assert c._win("t1")["size"] == [1280, 800]
    assert c._win("chat-1", "open")["size"] == [1280, 800]
    c.width, c.height = 1024, 600   # 屏幕比设置的小：不超过屏幕
    assert c._win("t1")["size"] == [1024, 600]
    c.backend = "host"
    assert "size" not in c._win("t1")


async def test_waiting_for_you_does_not_hang_in_silence(monkeypatch):
    """B3：你接手电脑后一直不交还，Bot 不会一声不响地挂着——到点喊一声、报错，让任务能说清在等什么。"""
    from osa.config import CFG
    monkeypatch.setitem(CFG["limits"], "computer_wait_human_s", 0.1)
    said = []

    async def say(text):
        said.append(text)
    c = FakeComputer()
    c.progress = say
    c.takeover()
    with pytest.raises(ComputerError, match="你一直在用电脑"):
        await c.wait_for_control()
    assert said and "你还在用电脑" in said[0]

    said.clear()
    handed = asyncio.create_task(c.wait_for_control())
    await asyncio.sleep(0.02)
    c.handback()
    assert await handed is True and not said      # 交还了：等过，但不唠叨

    assert await c.wait_for_control() is False     # 没接手：不用等
    monkeypatch.setitem(CFG["limits"], "computer_wait_human_s", 0)
    c._handback.clear()
    with pytest.raises(asyncio.TimeoutError):      # 配成 0 当然按默认 120 秒算，不会立刻报错
        await asyncio.wait_for(c.wait_for_control(), 0.3)


async def test_tool_calls_attach_progress_so_a_wait_is_visible(monkeypatch):
    """B3 的另一半：进度说明真的挂到了电脑上（等用户交还、等机器开起来时才有东西可喊）。"""
    from types import SimpleNamespace
    from osa.computer import tools as ctools
    c = FakeComputer()
    monkeypatch.setattr(ctools, "get", lambda: c)
    seen = []

    async def exec_(cmd, timeout=120, stdin=None):
        seen.append(c.progress)
        return ExecResult(0, "ok\n", "")

    async def progress(text):
        pass

    c.exec = exec_
    approvals.shell_confirmed(3)   # B1：这个任务的终端已经确认过，不再弹卡片
    task = SimpleNamespace(id=3, bot_id=1, chat_id=1, goal="g", background=False)
    out, _ = await ctools.call(task, "computer_shell", {"cmd": "ls"}, progress)
    assert out.startswith("退出码 0")
    assert seen == [progress] and c.progress is None   # 执行期间挂着，执行完摘掉
    approvals.end_task(3)


def test_page_text_speaks_the_readers_language(monkeypatch):
    """B6：页面信息（滚动到哪、视口多高、哪几个元素打了勾 / 在屏幕外）跟着界面语言走，三种语言都对得上。"""
    from osa import i18n
    from osa.computer.tools import page_text
    d = {"title": "T", "url": "https://x", "elements": ['[1] button "B" (checked)', '[2] a "L" (offscreen)'],
         "text": "body", "dialog": False, "scroll": "0/10306", "vh": 669}
    want = {"zh": "（滚动 0/10306，视口高 669）", "en": "(scroll 0/10306, viewport height 669)",
            "vi": "(cuộn 0/10306, cao 669)"}
    marks = {"zh": ("（已选中）", "（屏幕外）"), "en": ("(checked)", "(offscreen)"), "vi": ("(đã chọn)", "(ngoài màn hình)")}
    for lang in want:
        monkeypatch.setattr(i18n, "_lang", lang)
        out = page_text(d)
        assert want[lang] in out and all(m in out for m in marks[lang]), (lang, out)
    monkeypatch.setattr(i18n, "_lang", "vi")
    assert "视口高" not in page_text(d) and "已选中" not in page_text(d)   # 不再漏中文
    assert "0/10306" in page_text({**d, "vh": None})   # 老脚本没给 vh 也能排版
