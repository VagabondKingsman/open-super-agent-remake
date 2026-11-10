"""Bộ eval offline (P0+ #5): mỗi kịch bản trong tests/evals/scenarios là một test có marker `eval`.

Chạy riêng: `uv run pytest -m eval -q` hoặc `uv run python scripts/run_evals.py` (ra bảng điểm JSON + markdown).
Kịch bản có `xfail` là lỗ đã biết (ghi mã việc, ví dụ P0-2): chạy với strict=True, lỗ được vá thì test báo XPASS → FAIL
để nhớ bỏ xfail và cập nhật baseline.
"""
import json
import os
import sys

import pytest

from evals import engine
from osa import local_checks

SCENARIOS = engine.load_all()
SANDBOX = sys.platform == "linux" and all(local_checks.shutil.which(x) for x in ("bwrap", "prlimit", "git", "ps"))
REQUIRE_SANDBOX = os.environ.get("OSA_REQUIRE_SANDBOX") == "1"


def _params():
    for s in SCENARIOS:
        marks = [pytest.mark.eval]
        if "sandbox" in (s.get("needs") or []) and not SANDBOX and not REQUIRE_SANDBOX:
            marks.append(pytest.mark.skip(reason="Linux bubblewrap sandbox unavailable"))
        if s.get("xfail"):
            marks.append(pytest.mark.xfail(reason=s["xfail"], strict=True))
        yield pytest.param(s, id=s["id"], marks=marks)


@pytest.mark.parametrize("scn", list(_params()))
async def test_eval(scn, llm, events, make_bot, mcp_tool, monkeypatch, tmp_path, record_property):
    failures, metrics = await engine.run(scn, llm=llm, events=events, make_bot=make_bot, mcp_tool=mcp_tool,
                                         monkeypatch=monkeypatch, tmp_path=tmp_path)
    record_property("eval", json.dumps({"id": scn["id"], "area": scn["area"], "title": scn["title"], **metrics,
                                        "failures": failures}, ensure_ascii=False))
    assert not failures, "\n".join(failures)


def test_scenarios_are_valid():
    ids = [s["id"] for s in SCENARIOS]
    assert len(ids) == len(set(ids)) and 20 <= len(ids) <= 40


async def test_engine_catches_a_wrong_expectation(llm, events, make_bot, mcp_tool, monkeypatch, tmp_path):
    """Bite test: cùng kịch bản e01 nhưng đòi một kết quả không có thì engine phải báo FAIL, không im lặng PASS."""
    import copy
    scn = copy.deepcopy(next(s for s in SCENARIOS if s["id"] == "e01_dispatch_answer"))
    scn["expect"] |= {"result_contains": ["KHÔNG-CÓ-CHUỖI-NÀY"], "not_executed": ["dispatch"], "max_steps": 0}
    failures, _ = await engine.run(scn, llm=llm, events=events, make_bot=make_bot, mcp_tool=mcp_tool,
                                   monkeypatch=monkeypatch, tmp_path=tmp_path)
    assert len(failures) == 3, failures


def test_netguard_blocks_real_network():
    import socket
    with engine.NetGuard() as net:
        s = socket.socket()
        with pytest.raises(OSError, match="real network is blocked"):
            s.connect(("203.0.113.1", 80))   # TEST-NET-3: never routable
        s.close()
    assert net.blocked == ["('203.0.113.1', 80)"]
