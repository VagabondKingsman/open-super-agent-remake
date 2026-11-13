"""Tự restart: đường HTTP gọi đúng request_restart (execv giữ nguyên PID, không cần quyền)."""
import httpx

from osa import backup, server
from osa.config import CFG


def http():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://127.0.0.1")


async def test_restart_route_sets_the_flag(monkeypatch):
    asked = []
    monkeypatch.setitem(backup.__dict__, "RESTART", False)
    monkeypatch.setattr(backup, "request_restart", lambda delay=0.5: asked.append(delay))
    async with http() as c:
        r = await c.post("/api/system/restart")
    assert r.status_code == 200 and r.json() == {"restarting": True}
    assert asked and asked[0] > 0        # có chờ một nhịp để câu trả lời kịp về


async def test_restart_route_needs_a_session(monkeypatch):
    monkeypatch.setenv("OSA_PASSWORD", "x")   # bật đăng nhập
    async with http() as c:
        r = await c.post("/api/system/restart", follow_redirects=False)
    assert r.status_code in (401, 403, 302)
