"""回归：审计发现的两个 P0（2026-11-11）。

1. 没实现的 /api/* 曾经被 spa 兜底路由吞掉，回 200 + 首页 HTML，客户端分不清
   “接口不存在”和“成功”。
2. 虚拟机空闲挂起（409 machine_not_running）时，exec/read_file 直接把英文原文
   抛给模型；shell()/browser() 却会自动 start()。
"""
import pytest

from osa import server
from osa.computer.base import ComputerError
from osa.computer.instabox import ExecResult, InstaboxComputer


async def test_unknown_api_path_is_json_404():
    r = await server.spa("api/definitely-not-here")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


async def test_spa_still_serves_the_app():
    r = await server.spa("")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_wake_retry_starts_a_suspended_machine(monkeypatch):
    c = InstaboxComputer(1, fixed_machine="m-1")
    woke = []

    async def fake_exec_once(cmd, timeout=120, stdin=None):
        if not woke:                     # 第一枪：机器睡着
            raise ComputerError("Instabox 409 machine_not_running: machine is suspended")
        return ExecResult(0, "ok", "", False)

    async def fake_start():
        woke.append(True)

    monkeypatch.setattr(c, "_exec_once", fake_exec_once)
    monkeypatch.setattr(c, "start", fake_start)

    import asyncio

    r = asyncio.get_event_loop().run_until_complete(c.exec("ls"))
    assert woke == [True]
    assert r.stdout == "ok"


def test_wake_retry_leaves_other_errors_alone(monkeypatch):
    c = InstaboxComputer(1, fixed_machine="m-1")

    async def boom(cmd, timeout=120, stdin=None):
        raise ComputerError("Instabox 500 upstream exploded")

    async def never():
        raise AssertionError("不该叫醒机器")

    monkeypatch.setattr(c, "_exec_once", boom)
    monkeypatch.setattr(c, "start", never)

    import asyncio

    with pytest.raises(ComputerError, match="upstream"):
        asyncio.get_event_loop().run_until_complete(c.exec("ls"))
