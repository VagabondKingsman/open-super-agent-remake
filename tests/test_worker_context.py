"""C8：任务跑久了，早先的工具结果把每一步的上下文撑大（线上实测：每步平均 49k token，
一周 6 $ 几乎全在 worker 的角色上）。只留最近几条完整，其余截短；不到阈值时一个字不动，
免得改了前缀，模型服务的缓存每次都落空。"""
import pytest

from osa import worker
from osa.config import CFG


def test_a_result_cap_uses_the_whole_room_while_there_is_some(monkeypatch):
    """C23：地方够用时一个字也不少给（worker_result_chars 就是上限）。"""
    monkeypatch.setitem(CFG["limits"], "worker_compact_chars", 60000)
    monkeypatch.setitem(CFG["limits"], "worker_result_chars", 3000)
    assert worker._result_cap(0, 20, CFG["limits"]) == 3000


def test_the_cap_shrinks_as_the_task_fills_so_no_step_rewrites_the_prefix(monkeypatch):
    """C23：线上任务 314 在第 5 次调用时正文被 _compact_tools 改了一次，30k 全部重读。
    结果按“还剩多少地方、还剩几步”截短之后，每一步的正文都只是上一步的延长，一次都不改。"""
    monkeypatch.setitem(CFG["limits"], "worker_compact_chars", 20000)
    monkeypatch.setitem(CFG["limits"], "worker_result_chars", 3000)
    monkeypatch.setitem(CFG["limits"], "worker_tiny_tool_chars", 200)
    lim = CFG["limits"]
    msgs = history(0, 0)
    spent = 0
    for step in range(20):
        cap = worker._result_cap(spent, 20 - step, lim)
        text = worker._cut_result("y" * 5000, cap)
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"id": f"c{step}"}]})
        msgs.append({"role": "tool", "tool_call_id": f"c{step}", "content": text})
        spent += len(text)
        assert worker._compact_tools(msgs) == 0, f"第 {step} 步改了前面的前缀"
    assert 0 < spent <= 20000
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
    assert tools[0]["content"].rstrip().endswith("(earlier result omitted; call the tool again if you need it)") \
        or "shortened" in tools[0]["content"]


def test_huge_results_are_collapsed_so_later_steps_do_not_break():
    """C21：5–8k 字的结果很常见（task_steps 里 163/364），最近三条本身就比 goal 长，
    只截到 1500 字永远到不了 goal —— 那时最老的收成一行，一次到底，后面十几步都是原样追加。"""
    goal = int(CFG["limits"].get("worker_compact_to_chars", 20000))
    msgs = history(13, 5000)
    worker._compact_tools(msgs)
    total = sum(len(m["content"]) for m in msgs if m["role"] == "tool")
    assert total <= goal
    for step in range(3):        # 后面几步只追加，一个字都不改
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"id": f"n{step}"}]})
        msgs.append(tool(200 + step, 5000))
        assert worker._compact_tools(msgs) == 0


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

def test_a_pass_leaves_headroom_so_later_steps_keep_the_cache(monkeypatch):
    """C18：一次截短要截到目标以下。否则下一步又超、又截一条，每一步都改了前缀，
    模型服务的缓存每一步都落空（线上任务 106、102 就是这样）。"""
    monkeypatch.setitem(CFG["limits"], "worker_compact_chars", 20000)
    monkeypatch.setitem(CFG["limits"], "worker_compact_to_chars", 8000)
    monkeypatch.setitem(CFG["limits"], "worker_keep_full_tools", 2)
    monkeypatch.setitem(CFG["limits"], "worker_old_tool_chars", 500)
    msgs = history(12, 3000)                      # 12 × 3005 = 36060 字
    assert worker._compact_tools(msgs) > 0
    total = sum(len(m["content"]) for m in msgs if m["role"] == "tool")
    assert total < 20000                           # 阈值以下，留出了余量
    for step in range(2):                          # 后面两步：历史一个字都不该动
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"id": f"n{step}"}]})
        msgs.append(tool(100 + step, 3000))
        assert worker._compact_tools(msgs) == 0, "下一步不该再改前缀"


def test_a_shortened_result_is_not_shortened_twice(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "worker_compact_chars", 4000)
    monkeypatch.setitem(CFG["limits"], "worker_compact_to_chars", 1000)
    monkeypatch.setitem(CFG["limits"], "worker_keep_full_tools", 1)
    monkeypatch.setitem(CFG["limits"], "worker_old_tool_chars", 100)
    msgs = history(6, 2000)
    worker._compact_tools(msgs)
    first = [m["content"] for m in msgs if m["role"] == "tool"]
    assert all(c.endswith(worker.SHORTENED) for c in first[:-1])     # 早的截短，标记只出现一次
    assert not any(c.endswith(worker.SHORTENED + worker.SHORTENED) for c in first)
    assert first[-1] == tool(5, 2000)["content"]                     # 最近一条保持原样


def test_screenshots_are_dropped_in_batches_not_one_by_one():
    """C18：每来一张新截图就换掉一张，等于每一步都改前缀。攒够一批再换。"""
    from osa.computer import tools as ctools
    msgs = []
    for i in range(4):                                   # 前几张：一张都不动
        msgs.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"p{i}"}}]})
        assert ctools.prune_images(msgs, keep=2, batch=4) == 0
    for i in range(4, 7):                                # 第 7 张到了才动手，且只留最近 2 张
        msgs.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"p{i}"}}]})
        ctools.prune_images(msgs, keep=2, batch=4)
    pics = [m for m in msgs if isinstance(m["content"], list)]
    assert len(pics) == 2
    assert pics[-1]["content"][0]["image_url"]["url"] == "p6"
    assert msgs[0]["content"] == "(an earlier screenshot was omitted)"
