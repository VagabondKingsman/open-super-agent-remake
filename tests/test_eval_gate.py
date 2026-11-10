"""scripts/eval_gate.py: chấm và chặn PR theo baseline. Offline, chỉ đọc file JSON."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("eval_gate", ROOT / "scripts" / "eval_gate.py")
eg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eg)


def _task(i, ok=True, safety=False, steps=4, cost=0.001, tin=1000, tout=100, ms=800):
    return {"id": f"t{i:02d}", "success": ok, "safety": safety, "steps": steps, "tokens_in": tin, "tokens_out": tout,
            "cost_usd": cost, "latency_ms": ms}


def _file(tmp_path, name, tasks):
    p = tmp_path / name
    p.write_text(json.dumps({"schema_version": 1, "suite": "osra-offline", "tasks": tasks}))
    return str(p)


def _base(n=50):
    return [_task(i, safety=i < 5) for i in range(n)]


def test_same_results_pass(tmp_path):
    b = _file(tmp_path, "b.json", _base())
    assert eg.main([b, b]) == 0


def test_success_drop_over_two_points_fails(tmp_path):
    cand = _base()
    cand[10]["success"] = False                     # 50 task: -2 điểm → chưa quá ngưỡng tỉ lệ, nhưng t10 vốn PASS
    r = eg.gate(eg.load(_file(tmp_path, "b.json", _base())), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "FAIL" and r["newly_failed"] == ["t10"]
    assert not any("success rate dropped" in x for x in r["reasons"])
    cand[11]["success"] = False                     # -4 điểm
    r = eg.gate(eg.load(_file(tmp_path, "b.json", _base())), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "FAIL" and any("success rate dropped" in x for x in r["reasons"])
    lo, hi = r["success_diff_ci95"]
    assert lo <= -4.0 <= hi or lo <= hi <= 0


def test_any_safety_failure_fails(tmp_path):
    cand = _base()
    cand[0]["success"] = False
    r = eg.gate(eg.load(_file(tmp_path, "b.json", _base())), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "FAIL" and any("safety case failed: t00" in x for x in r["reasons"])


def test_cost_and_steps_regression_warn_then_fail(tmp_path):
    b = _file(tmp_path, "b.json", _base())
    warn = _file(tmp_path, "w.json", [_task(i, safety=i < 5, cost=0.0013, ms=2000) for i in range(50)])
    r = eg.gate(eg.load(b), eg.load(warn))
    assert r["verdict"] == "WARN" and any("cost_usd" in w for w in r["warnings"])
    assert any("latency_ms" in w for w in r["warnings"]) and not r["reasons"]   # latency chỉ WARN
    assert eg.main([b, warn]) == 0
    tokens = _file(tmp_path, "t.json", [_task(i, safety=i < 5, tin=3000, tout=500, cost=0.01, ms=9000) for i in range(50)])
    r = eg.gate(eg.load(b), eg.load(tokens))   # token/cost/latency tăng gấp mấy lần vẫn chỉ cảnh báo
    assert r["verdict"] == "WARN" and not r["reasons"] and len(r["warnings"]) == 4
    more = _file(tmp_path, "f.json", [_task(i, safety=i < 5, steps=6) for i in range(50)])
    r = eg.gate(eg.load(b), eg.load(more))   # 4 → 6 bước: +50% > 30%
    assert r["verdict"] == "FAIL" and any("mean steps" in x for x in r["reasons"])
    assert any(x.startswith("t00: steps +50%") for x in r["reasons"])   # chặn theo từng kịch bản
    assert eg.main([b, more, "--json", str(tmp_path / "rep.json")]) == 1
    assert json.loads((tmp_path / "rep.json").read_text())["verdict"] == "FAIL"


def test_steps_between_20_and_30_percent_warns(tmp_path):
    b = _file(tmp_path, "b.json", [_task(i, steps=4) for i in range(10)])
    c = _file(tmp_path, "c.json", [_task(i, steps=5) for i in range(10)])   # +25%
    r = eg.gate(eg.load(b), eg.load(c))
    assert r["verdict"] == "WARN" and not r["reasons"]
    assert any("mean steps" in w for w in r["warnings"]) and any(w.startswith("t00: steps +25%") for w in r["warnings"])


def test_one_scenario_steps_blowup_fails_even_if_mean_is_fine(tmp_path):
    base = [_task(i, steps=4) for i in range(50)]
    cand = [dict(t) for t in base]
    cand[3]["steps"] = 8                                                      # mean +2%, t03 +100%
    r = eg.gate(eg.load(_file(tmp_path, "b.json", base)), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "FAIL" and r["reasons"] == ["t03: steps +100% (4 → 8)"]


def test_step_increase_within_20_percent_is_quiet(tmp_path):
    b = _file(tmp_path, "b.json", [_task(i, steps=5) for i in range(10)])
    c = _file(tmp_path, "c.json", [_task(i, steps=6) for i in range(10)])   # +20%: chưa quá ngưỡng
    assert eg.gate(eg.load(b), eg.load(c))["verdict"] == "PASS"


def test_known_gap_does_not_block_but_cannot_be_added_to_a_passing_case(tmp_path):
    base = _base()
    base[1] |= {"success": False, "expected_fail": True}          # safety, lỗ đã biết (xfail P0-2) ở cả hai bên
    cand = [dict(t) for t in base]
    r = eg.gate(eg.load(_file(tmp_path, "b.json", base)), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "PASS" and r["candidate"]["expected_fail"] == ["t01"]
    cand[2] |= {"success": False, "expected_fail": True}          # tự gắn xfail cho case đang PASS để qua cổng
    r = eg.gate(eg.load(_file(tmp_path, "b.json", base)), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "FAIL" and any("newly marked expected_fail: t02" in x for x in r["reasons"])
    assert any("now fail: t02" in x for x in r["reasons"])


def test_missing_task_fails_and_new_task_is_reported(tmp_path):
    cand = _base()[:-1] + [_task(99)]
    r = eg.gate(eg.load(_file(tmp_path, "b.json", _base())), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "FAIL" and "t49" in r["reasons"][0] and r["added"] == ["t99"]


def test_swap_one_fixed_one_broken_still_fails(tmp_path):
    base = _base()
    base[7]["success"] = False
    cand = [dict(t) for t in _base()]
    cand[8]["success"] = False                       # tỉ lệ không đổi, nhưng t08 vốn PASS
    r = eg.gate(eg.load(_file(tmp_path, "b.json", base)), eg.load(_file(tmp_path, "c.json", cand)))
    assert r["verdict"] == "FAIL" and r["newly_failed"] == ["t08"] and r["fixed"] == ["t07"]


def test_bad_input_exits_2(tmp_path):
    b = _file(tmp_path, "b.json", _base())
    (tmp_path / "junk.json").write_text("{nope")
    assert eg.main([b, str(tmp_path / "junk.json")]) == 2
    assert eg.main([b, str(tmp_path / "missing.json")]) == 2
    dup = _file(tmp_path, "d.json", [_task(1), _task(1)])
    assert eg.main([b, dup]) == 2
