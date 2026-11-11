"""B7: listing a folder is one round trip, not three, and the same folder is not fetched twice in a row."""
import asyncio
import time

import httpx
import pytest

from osa import computer, library
from osa.computer import instabox
from osa.config import CFG
from osa.memory import conn


class Box:
    """一台假的 Instabox：exec 要 0.2 秒（像真的 API 一样），记下每条命令。"""

    def __init__(self, latency: float = 0.0, files: str = "f\t10\t1700000000\ta.txt\n"):
        self.latency, self.files, self.cmds = latency, files, []

    async def handler(self, request: httpx.Request) -> httpx.Response:
        import json
        p = request.url.path
        if p == "/v1/machines" and request.method == "GET":
            return httpx.Response(200, json={"machines": [{"id": "m1", "state": "running",
                                                           "metadata": {"app": "open-super-agent"}}]})
        if p.endswith("/exec"):
            cmd = json.loads(request.content or b"{}").get("cmd", "")
            self.cmds.append(cmd)
            await asyncio.sleep(self.latency)   # 假装的网络 + 机器里的时间（异步：两个命令才能真的同时跑）
            out = self.files if "find" in cmd else ("" if "[ -e" in cmd else "1280x800")
            return httpx.Response(200, json={"exitCode": 0, "stdout": out, "stderr": ""})
        if p.endswith("/desktop"):
            return httpx.Response(200, json={"installed": True})
        return httpx.Response(200, json={})


@pytest.fixture
def clean(monkeypatch):
    monkeypatch.setenv("INSTABOX_API_KEY", "k")
    monkeypatch.setitem(CFG.setdefault("computer", {}), "enabled", True)
    monkeypatch.setitem(CFG["computer"], "backend", "instabox")
    monkeypatch.setattr(computer, "_computers", {})
    conn.execute("delete from computers")
    conn.execute("insert into computers(bot_id, backend, ref) values(0, 'instabox', 'm1')")
    conn.commit()
    yield
    conn.execute("delete from computers")
    conn.commit()


def fake(monkeypatch, box: Box):
    real = httpx.AsyncClient
    monkeypatch.setattr(instabox.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(box.handler), **kw))


async def test_the_same_folder_is_asked_once(clean, monkeypatch):
    box = Box()
    fake(monkeypatch, box)
    c = instabox.InstaboxComputer(0)
    first = await c.ls("/data/workspace")
    again = await c.ls("/data/workspace")
    assert first == again and len(box.cmds) == 1          # 第二次是缓存，没有新命令
    await c.write_bytes("/data/workspace/b.txt", b"x")      # 写了文件：刚才那份列表不算了
    await c.ls("/data/workspace")
    assert len([x for x in box.cmds if "find" in x]) == 2


async def test_the_cache_expires(clean, monkeypatch):
    box = Box()
    fake(monkeypatch, box)
    c = instabox.InstaboxComputer(0)
    await c.ls("/data/workspace")
    c._ls_cache[("m1", "/data/workspace")] = (time.monotonic() - 10, [])
    await c.ls("/data/workspace")
    assert len([x for x in box.cmds if "find" in x]) == 2


async def test_the_files_page_costs_one_round_trip(clean, monkeypatch):
    """打开资料库：先问“电脑开没开”、再列目录、再取置顶文件的现状 = 三个来回；现在是一个（置顶的另算，且同时跑）。"""
    from starlette.testclient import TestClient
    from osa import server

    box = Box(latency=0.2)
    fake(monkeypatch, box)
    c = instabox.InstaboxComputer(0)
    monkeypatch.setattr(computer, "get", lambda *a, **k: c)
    monkeypatch.setattr(library, "pins", lambda: [])
    client = TestClient(server.app, base_url="http://127.0.0.1:8765")
    t0 = time.monotonic()
    r = client.get("/api/files")
    took = time.monotonic() - t0
    assert r.status_code == 200 and r.json()["running"]
    assert len(box.cmds) == 1, box.cmds            # 只列了一次目录，没有先问状态
    assert took < 0.35, took                        # 一个来回的时间，不是三个


async def test_a_two_command_page_waits_once(clean, monkeypatch):
    """列目录 + 置顶文件的现状：两个命令一起跑，等的时间是一次的。"""
    from osa import server

    box = Box(latency=0.2)
    fake(monkeypatch, box)
    c = instabox.InstaboxComputer(0)
    monkeypatch.setattr(library, "pins", lambda: ["/data/workspace/a.txt"])   # 有置顶文件：两个命令
    t0 = time.monotonic()
    await server._listing(c, "/data/workspace")
    took = time.monotonic() - t0
    assert len(box.cmds) == 2 and took < 0.35, (box.cmds, took)


async def test_a_stopped_computer_still_answers_the_page(clean, monkeypatch):
    from starlette.testclient import TestClient
    from osa import server

    class Dead(instabox.InstaboxComputer):
        async def status(self):
            return {"state": "none", "detail": ""}

        async def ls(self, path):
            raise computer.ComputerError("电脑还没创建")

    c = Dead(0)
    monkeypatch.setattr(computer, "get", lambda *a, **k: c)
    client = TestClient(server.app, base_url="http://127.0.0.1:8765")
    r = client.get("/api/files")
    assert r.status_code == 200 and r.json()["running"] is False and r.json()["state"] in ("none", "stopped", "error")
