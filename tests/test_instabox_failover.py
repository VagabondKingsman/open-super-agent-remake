"""B5: when the machine we were using disappears, the computer moves to another one of ours (a couple of API calls,
well under 10 s) or creates a fresh one, and the role is recorded in the machine's metadata."""
import json
import re
import time

import httpx
import pytest

from osa import computer
from osa.computer import instabox
from osa.computer.base import ComputerError
from osa.config import CFG
from osa.memory import conn


class Box:
    """一台假的 Instabox 账号：machines 里有什么就回什么，记下每次请求。"""

    def __init__(self, *ids, dead=(), state="running"):
        self.machines = {i: {"id": i, "name": i, "state": state, "template": "agent-browser", "createdAt": "2026-01-01",
                             "metadata": {"app": "open-super-agent", "role": "primary"}} for i in ids}
        self.dead = set(dead)          # 这些 id 已经没了（404）
        self.calls: list[tuple[str, str]] = []
        self.patched: dict[str, dict] = {}
        self.created: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        p, method = request.url.path, request.method
        self.calls.append((method, p))
        if (m := re.fullmatch(r"/v1/machines/([^/]+)(/.*)?", p)) and (m[1] in self.dead or m[1] not in self.machines):
            return self._json({"error": {"code": "machine_not_found", "message": "no such machine"}}, 404)
        if p == "/v1/machines" and method == "GET":
            return self._json({"machines": list(self.machines.values())})
        if p == "/v1/machines" and method == "POST":
            body = json.loads(request.content or b"{}")
            self.created.append(body)
            mid = f"new{len(self.created)}"
            self.machines[mid] = {"id": mid, "state": "running", "metadata": body.get("metadata") or {}}
            return self._json({"id": "op1", "state": "succeeded", "machineId": mid})
        if m := re.fullmatch(r"/v1/machines/([^/]+)", p):
            mid = m[1]
            if mid in self.dead or mid not in self.machines:
                return self._json({"error": {"code": "machine_not_found", "message": "no such machine"}}, 404)
            if method == "PATCH":
                md = json.loads(request.content or b"{}").get("metadata") or {}
                self.patched[mid] = md
                self.machines[mid]["metadata"] = md
            return self._json(self.machines[mid])
        if p.endswith("/desktop"):
            return self._json({"installed": True, "state": "running"})
        if re.fullmatch(r"/v1/machines/[^/]+/exec", p):
            return self._json({"exitCode": 0, "stdout": "1280x800", "stderr": ""})
        if p.endswith(("/start", "/resume", "/wake", "/suspend")):
            return self._json({"id": "op", "state": "succeeded"})
        return self._json({})

    @staticmethod
    def _json(body, code=200):
        return httpx.Response(code, json=body)


@pytest.fixture
def clean(monkeypatch):
    monkeypatch.delenv("INSTABOX_API_KEY", raising=False)
    monkeypatch.delenv("OSA_DESKTOP", raising=False)
    monkeypatch.setitem(CFG.setdefault("computer", {}), "enabled", True)
    monkeypatch.setitem(CFG["computer"], "backend", "instabox")
    monkeypatch.setattr(computer, "_computers", {})
    conn.execute("delete from computers")
    conn.commit()
    yield
    conn.execute("delete from computers")
    conn.commit()


def fake(monkeypatch, box: Box):
    real = httpx.AsyncClient
    monkeypatch.setattr(instabox.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(box.handler), **kw))
    monkeypatch.setenv("INSTABOX_API_KEY", "k")


def remember(mid: str):
    conn.execute("delete from computers")
    conn.execute("insert into computers(bot_id, backend, ref) values(0, 'instabox', ?)", (mid,))
    conn.commit()


def saved() -> str | None:
    r = conn.execute("select ref from computers where bot_id=0 and backend='instabox'").fetchone()
    return r[0] if r else None


async def test_the_primary_dying_moves_to_the_other_machine_quickly(clean, monkeypatch):
    box = Box("m1", "m2", dead={"m1"})
    fake(monkeypatch, box)
    remember("m1")
    c = instabox.InstaboxComputer(0)
    t0 = time.monotonic()
    await c.start()
    took = time.monotonic() - t0
    assert saved() == "m2" and took < 5          # 换一台：列表 + 记住，几秒内
    assert box.patched.get("m2", {}).get("role") == "primary"    # metadata.role 记下来
    assert not box.created                       # 有现成的机器就不新建
    assert len([c for c in box.calls if c[0] == "PATCH"]) == 1


async def test_with_no_other_machine_a_new_one_is_created_and_marked_primary(clean, monkeypatch):
    box = Box("m1", dead={"m1"})
    fake(monkeypatch, box)
    remember("m1")
    c = instabox.InstaboxComputer(0)
    await c.start()
    assert box.created and box.created[0]["metadata"]["role"] == "primary"
    assert saved() == "new1"


async def test_the_second_machine_is_the_one_that_is_still_running(clean, monkeypatch):
    box = Box("m1", "m2", "m3", dead={"m1"})
    box.machines["m2"]["state"] = "stopped"
    box.machines["m3"]["state"] = "suspended"
    fake(monkeypatch, box)
    remember("m1")
    c = instabox.InstaboxComputer(0)
    await c.start()
    assert saved() == "m3"           # 挂起的比停了的先恢复（要快）


async def test_a_command_after_the_machine_vanished_still_runs(clean, monkeypatch):
    """在机器上跑命令时才 404：换一台再跑一遍（模型看不到 404）。"""
    box = Box("m1", "m2", dead={"m1"})
    fake(monkeypatch, box)
    remember("m1")
    c = instabox.InstaboxComputer(0)
    r = await c.exec("echo hi")
    assert r.exit_code == 0 and saved() == "m2"


async def test_a_pinned_machine_that_is_gone_says_so(clean, monkeypatch):
    box = Box("m1", "m2", dead={"m1"})
    fake(monkeypatch, box)
    c = instabox.InstaboxComputer(0, fixed_machine="m1")
    monkeypatch.setitem(CFG["computer"], "instabox_machine", "m1")
    with pytest.raises(ComputerError, match="instabox_machine"):
        await c.start()
    assert not box.created


async def test_the_picker_shows_which_machine_is_primary(clean, monkeypatch):
    box = Box("m1", "m2")
    box.machines["m2"]["metadata"]["role"] = "backup"
    fake(monkeypatch, box)
    remember("m1")
    c = instabox.InstaboxComputer(0)
    rows = {m["id"]: m for m in await c.list_machines()}
    assert rows["m1"]["role"] == "primary" and rows["m2"]["role"] == "backup" and rows["m1"]["current"]
