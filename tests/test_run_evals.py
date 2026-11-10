"""scripts/run_evals.py: CI so với baseline của nhánh đích, không với file trong PR. Offline, không chạy kịch bản."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("run_evals", ROOT / "scripts" / "run_evals.py")
rv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rv)
import eval_gate as eg  # noqa: E402


def _task(i, ok=True, safety=False, expected_fail=False, steps=4):
    return {"id": f"t{i:02d}", "success": ok, "safety": safety, "expected_fail": expected_fail, "steps": steps}


def _doc(tasks) -> str:
    return json.dumps({"schema_version": 1, "suite": "osar-offline", "tasks": tasks})


@pytest.fixture
def repo(tmp_path):
    """Repo git tạm có origin/main (đã có baseline) và origin/old (chưa có) như sau git fetch trên CI."""
    r = tmp_path / "repo"
    r.mkdir()

    def git(*a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=r, capture_output=True, text=True)
    git("init", "-q", "-b", "main")
    (r / "README").write_text("x")
    git("add", "."), git("commit", "-q", "-m", "old")
    git("update-ref", "refs/remotes/origin/old", "HEAD")
    (r / "tests" / "evals").mkdir(parents=True)
    (r / "tests" / "evals" / "baseline.json").write_text(_doc([_task(1), _task(2)]))
    git("add", "."), git("commit", "-q", "-m", "baseline")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    return git


def test_push_uses_committed_baseline(tmp_path, repo):
    assert rv.resolve_baseline(None, "tests/evals/baseline.json", tmp_path, git=repo) == ("tests/evals/baseline.json", "")


def test_pr_uses_target_branch_baseline(tmp_path, repo):
    path, notice = rv.resolve_baseline("main", "pr-baseline.json", tmp_path, git=repo)
    assert path == str(tmp_path / "base-baseline.json") and "origin/main" in notice
    assert [t["id"] for t in json.loads(Path(path).read_text())["tasks"]] == ["t01", "t02"]


def test_target_without_baseline_falls_back_with_notice(tmp_path, repo):
    path, notice = rv.resolve_baseline("old", "pr-baseline.json", tmp_path, git=repo)
    assert path == "pr-baseline.json" and "bootstrap" in notice and "origin/old" in notice


def test_missing_target_ref_is_an_error_not_a_fallback(tmp_path, repo):
    with pytest.raises(ValueError, match="origin/nope not found"):
        rv.resolve_baseline("nope", "pr-baseline.json", tmp_path, git=repo)


def test_pr_cannot_loosen_the_gate_through_its_own_baseline(tmp_path):
    """PR tự gắn expected_fail cho t02 trong baseline của nó: so với baseline của PR thì lọt, so với nhánh đích thì chặn."""
    target = tmp_path / "target.json"
    target.write_text(_doc([_task(1), _task(2, safety=True)]))
    own = tmp_path / "own.json"
    own.write_text(_doc([_task(1), _task(2, ok=False, safety=True, expected_fail=True)]))
    cand = tmp_path / "cand.json"
    cand.write_text(_doc([_task(1), _task(2, ok=False, safety=True, expected_fail=True)]))
    assert eg.gate(eg.load(own), eg.load(cand))["verdict"] == "PASS"
    r = eg.gate(eg.load(target), eg.load(cand))
    assert r["verdict"] == "FAIL" and any("newly marked expected_fail: t02" in x for x in r["reasons"])


def test_scorecard_shows_the_baseline_notice(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(_doc([_task(1)]))
    gate = eg.gate(eg.load(f), eg.load(f))
    res = {"osa_commit": "x", "created_at": "now", "tasks": [{"id": "t01", "area": "core", "outcome": "passed",
           "success": True, "safety": False, "known_gap": "", "failures": [], "steps": 4}]}
    md = rv.scorecard(res, gate, "origin/old has no tests/evals/baseline.json yet (bootstrap)")
    assert "> **Baseline:** origin/old has no tests/evals/baseline.json yet (bootstrap)" in md
    assert "eval gate: PASS" in md
