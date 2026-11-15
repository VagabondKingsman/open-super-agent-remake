"""B2: the live picture. When the computer side drops, the page hears about it at once (close 1011, overlay within
2 s) instead of staring at a frozen screen; when the page goes away, the computer side is released."""
import asyncio
import io
import time

import pytest

from osa import server
from osa.computer import instabox


class FakeSock:
    """网页那一头。recv 由测试往 q 里放；“断开”就是放一个 None。"""

    def __init__(self):
        self.q: asyncio.Queue = asyncio.Queue()
        self.sent: list[bytes] = []
        self.closed: tuple | None = None
        self.actions = 0

    async def receive(self):
        m = await self.q.get()
        return {"type": "websocket.disconnect"} if m is None else {"type": "websocket.receive", "bytes": m}

    async def send_bytes(self, data: bytes):
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = (code, reason, time.monotonic())


def bridge(sock, frames, actions=None):
    """把 _vnc_bridge 接在一个“电脑那头”的假通道上：frames 放完就断（还是别的错由 drop 决定）。"""
    released = []

    async def recv():
        if frames:
            return frames.pop(0)
        raise ConnectionError("电脑那边断了")

    async def send(data: bytes):
        pass

    async def close():
        released.append(time.monotonic())

    return server._vnc_bridge(sock, recv, send, close, on_action=actions), released


async def test_computer_side_drop_closes_the_page_at_once():
    sock = FakeSock()
    t0 = time.monotonic()
    task, released = bridge(sock, [b"frame1", b"frame2"])
    await asyncio.wait_for(task, 2)
    assert sock.sent == [b"frame1", b"frame2"]
    assert sock.closed and sock.closed[0] == 1011 and "computer disconnected" in sock.closed[1]
    assert sock.closed[2] - t0 < 2 and released    # 网页那边马上就能显示“断开了”


async def test_page_going_away_releases_the_computer_side():
    sock = FakeSock()
    frames = []

    async def recv():
        await asyncio.sleep(10)      # 电脑那头一直没话
        return b""

    released = []

    async def close():
        released.append(True)

    task = asyncio.create_task(server._vnc_bridge(sock, recv, lambda d: None, close))
    await asyncio.sleep(0.05)
    await sock.q.put(None)           # 网页关了
    await asyncio.wait_for(task, 2)
    assert released and sock.closed and sock.closed[0] == 1000   # 正常关，不是“断线”


async def test_frames_from_the_page_reach_the_computer_and_count_as_use():
    sock = FakeSock()
    seen, actions = [], []

    async def recv():
        await asyncio.sleep(10)

    async def send(data):
        seen.append(data)

    task = asyncio.create_task(server._vnc_bridge(sock, recv, send, lambda: None, on_action=lambda: actions.append(1)))
    await asyncio.sleep(0.02)
    await sock.q.put(b"mouse-click")
    await sock.q.put(b"key")
    await asyncio.sleep(0.05)
    await sock.q.put(None)
    await asyncio.wait_for(task, 2)
    assert seen == [b"mouse-click", b"key"] and actions == [1, 1]   # 你一动，电脑就不算“没人用”


async def test_instabox_vnc_link_has_a_heartbeat(monkeypatch):
    """云端那条连接设了 ping：网断了（NAT 超时、机器重启）20 秒内就发现，而不是永远等下去。"""
    seen = {}

    class FakeWS:
        async def recv(self):
            return b""

        async def send(self, data):
            pass

        async def close(self):
            pass

    async def fake_connect(url, **kw):
        seen.update(kw, url=url)
        return FakeWS()

    monkeypatch.setenv("INSTABOX_API_KEY", "k")
    monkeypatch.setattr(instabox.websockets, "connect", fake_connect)
    c = instabox.InstaboxComputer(1, fixed_machine="m1")
    recv, send, close = await c.open_vnc()
    assert seen["ping_interval"] == 20 and seen["ping_timeout"] and seen["close_timeout"]
    assert seen["url"].startswith("ws") and seen["url"].endswith("/v1/machines/m1/vnc")


class FakeProc:
    """电脑那头的转发进程：stdout 先给版本（或者一直不给），stderr 留着报错。"""

    def __init__(self, banner=b"RFB 003.008\n", err=b"", hang=False):
        self.banner, self.err, self.hang = banner, err, hang
        self.returncode = None
        self.done = False
        self.stdin = io.BytesIO()
        self.stdout = self._out()
        self.stderr = self._err()

    def _out(self):
        class Out:
            def __init__(self, owner):
                self.owner = owner
                self.done = False

            async def read(self, n):
                if self.owner.hang:
                    await asyncio.sleep(10)
                if self.owner.done:
                    return b""
                self.owner.done = True
                return self.owner.banner
        return Out(self)

    def _err(self):
        class Err:
            def __init__(self, owner):
                self.owner = owner
                self.done = False

            async def read(self):
                if self.done:
                    return b""
                self.done = True
                return self.owner.err
        return Err(self)

    def kill(self):
        self.returncode = -9

    async def wait(self):
        return self.returncode


async def test_open_vnc_wakes_a_paused_computer(monkeypatch):
    """电脑闲置被暂停着：先叫醒再连，别让 docker exec 一直挂着。"""
    from osa.computer import local

    calls = []

    async def fake_run(*args, **kw):
        calls.append(args)
        return (0, "", "")

    async def fake_status(self):
        return {"state": "paused"}

    async def fake_spawn(*args, **kw):
        return FakeProc()

    monkeypatch.setattr(local, "_run", fake_run)
    monkeypatch.setattr(local.LocalComputer, "status", fake_status)
    monkeypatch.setattr(local.asyncio, "create_subprocess_exec", fake_spawn)
    c = local.LocalComputer(1)
    recv, _send, _close = await c.open_vnc()
    assert ("docker", "unpause", c.name) in calls
    assert await recv() == b"RFB 003.008\n"


async def test_open_vnc_says_why_there_is_no_picture(monkeypatch):
    """转发进程起不来（容器被暂停着）：十秒内报错并说明，而不是让网页一直等、画面一直不动。"""
    from osa.computer import local

    async def fake_status(self):
        return {"state": "running"}

    async def fake_spawn(*args, **kw):
        return FakeProc(hang=True, err=b"Error: Container is paused, unpause the container before exec\n")

    monkeypatch.setattr(local.LocalComputer, "status", fake_status)
    monkeypatch.setattr(local.asyncio, "create_subprocess_exec", fake_spawn)
    monkeypatch.setattr(local, "VNC_FIRST_S", 0.05)
    c = local.LocalComputer(1)
    with pytest.raises(ConnectionError) as e:
        await c.open_vnc()
    assert "paused" in str(e.value)


async def test_idle_pauser_leaves_a_watched_computer_alone(monkeypatch):
    """网页正连着画面的时候不暂停：一暂停画面就停在原处，人还以为连着呢。"""
    from osa import computer as comp

    class FakeComputer:
        auto_pause = True
        controller = "bot"
        last_used = 0          # 早该暂停了
        viewers = 0
        paused = 0

        async def pause(self):
            self.paused += 1

    c = FakeComputer()
    monkeypatch.setattr(comp, "_computers", {1: c})
    monkeypatch.setattr(comp, "CFG", {"computer": {"idle_pause_s": 1}})
    real_sleep = asyncio.sleep

    async def fast_sleep(t):   # 巡检里的 60 秒等不起
        await real_sleep(0 if t > 5 else t)

    monkeypatch.setattr(comp.asyncio, "sleep", fast_sleep)
    c.viewers = 1              # 有人正看着画面
    task = asyncio.create_task(comp.idle_pauser())
    await real_sleep(0.05)
    assert c.paused == 0
    c.viewers = 0              # 人都走了
    await real_sleep(0.05)
    task.cancel()
    assert c.paused > 0          # 人都走了才会暂停


async def test_the_page_counts_as_a_viewer_until_it_closes(monkeypatch):
    """连着画面的人记在电脑上（idle_pauser 看这个数），页面关了要还回去。"""
    from osa import server

    class FakePc:
        viewers = 0
        last_used = 0

        async def start(self):
            pass

        async def open_vnc(self):
            async def recv():
                await asyncio.sleep(10)
            async def send(_d):
                pass
            async def close():
                pass
            return recv, send, close

    class Sock(FakeSock):
        headers = {"sec-websocket-protocol": "binary"}

        async def accept(self, subprotocol=None):
            self.subprotocol = subprotocol

    pc = FakePc()
    monkeypatch.setattr(server.computer, "get", lambda bot_id: pc)
    sock = Sock()
    task = asyncio.create_task(server.pc_vnc(sock, 1))
    await asyncio.sleep(0.05)
    assert pc.viewers == 1 and sock.subprotocol == "binary"
    await sock.q.put(None)          # 页面关了
    await asyncio.wait_for(task, 2)
    assert pc.viewers == 0 and sock.closed[0] == 1000
