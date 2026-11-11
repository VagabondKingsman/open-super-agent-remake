"""C8：任务跑久了，早先的工具结果把每一步的上下文撑大（线上实测：每步平均 49k token，
一周 6 $ 几乎全在 worker 的角色上）。只留最近几条完整，其余截短；不到阈值时一个字不动，
免得改了前缀，模型服务的缓存每次都落空。"""
import pytest

from osa import worker
from osa.config import CFG


def tool(i: int, size: int) -> dict:
    return {"role": "tool", "tool_call_id": f"c{i}", "content": f"out {i}: " + "x" * size}


def history(n: int, size: int) -> list[dict]:
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "goal"}]
    for i in range(n):
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"id": f"c{i}"}]})
        msgs.append(tool(i, size))
    return msgs


def test_nothing_changes_below_the_threshold():
    msgs = history(3, 5000)
    before = [dict(m) for m in msgs]
    assert worker._compact_tools(msgs) == 0
    assert msgs == before


def test_old_outputs_are_shortened_and_recent_ones_kept():
    msgs = history(13, 5000)                     # 13 × 5005 字：超过 60000
    cut = worker._compact_tools(msgs)
    assert cut > 0
    tools = [m for m in msgs if m["role"] == "tool"]
    keep = int(CFG["limits"].get("worker_keep_full_tools", 3))
    assert [len(t["content"]) > 4000 for t in tools[-keep:]] == [True] * keep
    assert all(len(t["content"]) < 2000 for t in tools[:-keep])
    assert "shortened" in tools[0]["content"]


def test_compact_is_idempotent():
    msgs = history(13, 5000)
    worker._compact_tools(msgs)
    snapshot = [dict(m) for m in msgs]
    assert worker._compact_tools(msgs) == 0
    assert msgs == snapshot


def test_only_the_long_ones_are_touched():
    msgs = history(3, 5000)
    msgs.append({"role": "tool", "tool_call_id": "short", "content": "ok"})
    worker._compact_tools(msgs)
    assert msgs[-1]["content"] == "ok"
