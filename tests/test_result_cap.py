"""C22：工具结果在“刚回来”的时候就截短，而不是过几步再去改已经发出去的那条。

改已经发出去的正文 = 从那条起整个 body 重读一遍（模型服务的缓存按“原样延长”命中）；只改刚回来的
这条，则是零断点。模拟（scripts/compact_sim.py，22 步、真实结果尺寸、真实单价 $0,50/$2,02 每 Mtok）：
每个任务 $0,1499（C21 两层压缩，0,9 次断点）→ $0,1180（cap=3000，0 次断点）。
"""
from osa import worker


def test_a_short_result_is_untouched():
    assert worker._cut_result("Exit code 0", 3000) == "Exit code 0"


def test_a_long_result_keeps_the_head_and_the_tail():
    out = "HEAD" + "x" * 10000 + "Traceback: ZeroDivisionError"
    cut = worker._cut_result(out, 3000)
    assert cut.startswith("HEAD")
    assert cut.endswith("Traceback: ZeroDivisionError")   # 错误写在最后几行：留尾才看得到
    assert f"{len(out) - 3000} chars cut here" in cut     # 切掉多少，模型看得见
    assert len(cut) < 3000 + 200                         # 只多出标记本身


def test_zero_and_tiny_caps_mean_no_cap():
    big = "y" * 5000
    assert worker._cut_result(big, 0) == big
    assert worker._cut_result(big, 100) == big           # 太小的上限会把结果切成噪声


def test_cut_count_matches_what_was_removed():
    out = "a" * 2000 + "b" * 4000
    cut = worker._cut_result(out, 3000)
    removed = 6000 - (len(cut) - len(worker.CUT.format(n=3000)))
    assert removed == 3000


def test_appending_a_capped_result_never_rewrites_earlier_messages():
    """缓存的性质，不是风格问题：前一次请求的每一条都要原封不动地留在下一次里。"""
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "goal"}]
    for step in range(12):
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"id": f"c{step}"}]})
        before = [dict(m) for m in msgs]
        msgs.append({"role": "tool", "tool_call_id": f"c{step}",
                     "content": worker._cut_result("z" * 9000, 3000)})
        assert msgs[:-1] == before                      # 原样延长
