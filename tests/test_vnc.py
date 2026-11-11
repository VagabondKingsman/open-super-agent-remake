"""B2: the live picture. When the computer side drops, the page hears about it at once (close 1011, overlay within
2 s) instead of staring at a frozen screen; when the page goes away, the computer side is released."""
import asyncio
import time

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
