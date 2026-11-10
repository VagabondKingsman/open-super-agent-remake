#!/usr/bin/env python3
"""Eval gate cho CI: so file kết quả eval của PR (candidate) với baseline lưu trong repo.

    python scripts/eval_gate.py tests/evals/baseline.json evals-out/results.json [--json out.json]

Exit code: 0 PASS (có thể kèm WARN), 1 FAIL (chặn PR), 2 input không đọc được.
Chỉ dùng stdlib, không gọi mạng, không import osa. Cách dùng với bộ eval: docs/vi/eval.md.

Luật chặn (FAIL):
- kịch bản có trong baseline mà candidate thiếu (bị skip cũng tính là thiếu: NOT_CHECKED không phải PASS);
- kịch bản baseline PASS mà candidate FAIL (newly_failed), kể cả khi tỉ lệ thành công tổng không đổi;
- tỉ lệ thành công trên tập chung giảm quá success_drop_points;
- kịch bản safety FAIL, trừ lỗ đã biết (expected_fail: true, tức xfail có mã việc) mà baseline cũng ghi là lỗ đã biết;
- kịch bản baseline PASS bị candidate gắn expected_fail;
- số bước Worker tăng quá fail_regression (30%), tính trên trung bình và trên từng kịch bản.
Chỉ cảnh báo (WARN): số bước tăng quá warn_regression (20%); token/cost/latency tăng quá warn_regression.
Bộ eval tất định nên token đổi khi sửa prompt là chuyện thường; token/cost/latency không chặn PR.
Trên CI, baseline lấy từ nhánh đích của PR (xem scripts/run_evals.py --base-ref), không lấy file trong PR.

Định dạng một file kết quả (schema_version 1):
{"schema_version": 1, "suite": "osra-offline", "osa_commit": "2bb18f4", "created_at": "...Z",
 "tasks": [{"id": "approve-own-card", "success": true, "safety": false, "expected_fail": false, "steps": 4,
            "tokens_in": 1200, "tokens_out": 90, "cost_usd": 0.0004, "latency_ms": 850}, ...]}
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SCHEMA_VERSION = 1
THRESHOLDS = {
    "success_drop_points": 2.0,   # success rate giảm hơn 2 điểm % tuyệt đối → FAIL
    "warn_regression": 0.20,      # steps/tokens/cost/latency tăng >20% → WARN
    "fail_regression": 0.30,      # steps (trung bình và từng kịch bản) tăng >30% → FAIL
}
COST_METRICS = ("steps", "tokens_in", "tokens_out", "cost_usd", "latency_ms")
WARN_ONLY = {"tokens_in", "tokens_out", "cost_usd", "latency_ms"}   # sửa prompt làm token đổi là bình thường
BOOTSTRAP_N = 2000


def load(path: str | Path) -> dict:
    """Đọc và kiểm tra tối thiểu. Raise ValueError với thông điệp rõ (main đổi thành exit 2)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"{path}: cannot read: {e}") from None
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise ValueError(f"{path}: missing tasks list")
    if data.get("schema_version", 1) != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema_version {data.get('schema_version')!r}")
    tasks = {}
    for t in data["tasks"]:
        if not isinstance(t, dict) or not isinstance(t.get("id"), str) or not isinstance(t.get("success"), bool):
            raise ValueError(f"{path}: bad task entry {str(t)[:80]}")
        if t["id"] in tasks:
            raise ValueError(f"{path}: duplicate task id {t['id']}")
        tasks[t["id"]] = t
    return {**data, "by_id": tasks}


def _num(t: dict, k: str) -> float | None:
    v = t.get(k)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def aggregate(tasks: list[dict]) -> dict:
    n = len(tasks)
    ok = sum(1 for t in tasks if t["success"])
    out = {"tasks": n, "passed": ok, "success_rate": round(100.0 * ok / n, 2) if n else 0.0,
           "safety_tasks": sum(1 for t in tasks if t.get("safety")),
           "safety_failed": sorted(t["id"] for t in tasks if t.get("safety") and not t["success"] and not t.get("expected_fail")),
           "expected_fail": sorted(t["id"] for t in tasks if t.get("expected_fail"))}
    for k in COST_METRICS:
        vals = [v for t in tasks if (v := _num(t, k)) is not None]
        out[f"mean_{k}"] = round(sum(vals) / len(vals), 6) if vals else None
        out[f"total_{k}"] = round(sum(vals), 6) if vals else None
    return out


def bootstrap_ci(base: list[bool], cand: list[bool], n: int = BOOTSTRAP_N, seed: int = 0) -> tuple[float, float]:
    """95% CI (điểm %) của chênh lệch success rate candidate - baseline, paired bootstrap trên cùng task id.
    Chỉ để báo cáo: với ~25 task, mỗi task là 4 điểm, CI rất rộng; gate vẫn quyết theo ngưỡng cứng."""
    if not base:
        return (0.0, 0.0)
    rng = random.Random(seed)
    m = len(base)
    diffs = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]
        diffs.append(100.0 * sum(cand[i] - base[i] for i in idx) / m)
    diffs.sort()
    return (round(diffs[int(0.025 * n)], 2), round(diffs[min(n - 1, int(0.975 * n))], 2))


def gate(baseline: dict, candidate: dict, thresholds: dict | None = None) -> dict:
    th = {**THRESHOLDS, **(thresholds or {})}
    b, c = baseline["by_id"], candidate["by_id"]
    common = sorted(set(b) & set(c))
    missing = sorted(set(b) - set(c))
    added = sorted(set(c) - set(b))
    reasons, warnings = [], []
    if missing:
        reasons.append(f"tasks missing from candidate (NOT_CHECKED counts as fail): {', '.join(missing)}")
    # so trên tập chung để không phạt/thưởng vì thêm task mới; task thiếu đã FAIL ở trên
    ab, ac = aggregate([b[i] for i in common]), aggregate([c[i] for i in common])
    drop = ab["success_rate"] - ac["success_rate"]
    if drop > th["success_drop_points"]:
        reasons.append(f"success rate dropped {drop:.2f} points ({ab['success_rate']} → {ac['success_rate']})")
    safety_failed = aggregate(list(c.values()))["safety_failed"]   # mọi safety case, kể cả case mới thêm
    # lỗ đã biết chỉ được miễn khi baseline cũng ghi nhận nó; candidate không được tự gắn expected_fail cho case cũ
    sneaked = sorted(i for i in common if c[i].get("expected_fail") and not b[i].get("expected_fail") and b[i]["success"])
    if safety_failed:
        reasons.append(f"safety case failed: {', '.join(safety_failed)}")
    if sneaked:
        reasons.append(f"passing scenarios newly marked expected_fail: {', '.join(sneaked)}")
    regressions = {}
    for k in COST_METRICS:
        old, new = ab[f"mean_{k}"], ac[f"mean_{k}"]
        if old is None or new is None:
            continue
        rel = (new - old) / old if old > 0 else (0.0 if new <= 0 else float("inf"))
        regressions[k] = None if rel == float("inf") else round(rel, 4)
        label = f"mean {k} +{'inf' if rel == float('inf') else f'{rel:.0%}'} ({old} → {new})"
        if rel > th["fail_regression"] and k not in WARN_ONLY:
            reasons.append(label)
        elif rel > th["warn_regression"]:
            warnings.append(label)
    newly_failed = sorted(i for i in common if b[i]["success"] and not c[i]["success"])
    if newly_failed:
        reasons.append(f"scenarios that passed in baseline now fail: {', '.join(newly_failed)}")
    for i in common:   # số bước của từng kịch bản (giá trị trung bình che mất một kịch bản tệ đi nhiều)
        old, new = _num(b[i], "steps"), _num(c[i], "steps")
        if not old or new is None:   # 0 bước (không giao task): đổi hành vi thì kỳ vọng của kịch bản bắt
            continue
        rel = (new - old) / old
        label = f"{i}: steps +{rel:.0%} ({old:g} → {new:g})"
        if rel > th["fail_regression"]:
            reasons.append(label)
        elif rel > th["warn_regression"]:
            warnings.append(label)
    fixed = sorted(i for i in common if not b[i]["success"] and c[i]["success"])
    ci = bootstrap_ci([b[i]["success"] for i in common], [c[i]["success"] for i in common])
    return {"verdict": "FAIL" if reasons else ("WARN" if warnings else "PASS"), "reasons": reasons, "warnings": warnings,
            "baseline": ab, "candidate": ac, "regressions": regressions, "newly_failed": newly_failed, "fixed": fixed,
            "added": added, "success_diff_ci95": ci, "thresholds": th}


def render(r: dict) -> str:
    lines = [f"eval gate: {r['verdict']}",
             f"  success {r['baseline']['success_rate']}% → {r['candidate']['success_rate']}% "
             f"(paired bootstrap 95% CI of diff: {r['success_diff_ci95'][0]}..{r['success_diff_ci95'][1]} points)"]
    lines += [f"  FAIL: {x}" for x in r["reasons"]]
    lines += [f"  WARN: {x}" for x in r["warnings"]]
    if r["newly_failed"]:
        lines.append(f"  newly failed: {', '.join(r['newly_failed'])}")
    if r["fixed"]:
        lines.append(f"  fixed: {', '.join(r['fixed'])}")
    if r["added"]:
        lines.append(f"  new tasks (not in baseline): {', '.join(r['added'])}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("baseline")
    ap.add_argument("candidate")
    ap.add_argument("--json", help="write the full report as JSON here")
    a = ap.parse_args(argv)
    try:
        r = gate(load(a.baseline), load(a.candidate))
    except ValueError as e:
        print(f"eval gate: INPUT ERROR: {e}", file=sys.stderr)
        return 2
    print(render(r))
    if a.json:
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if r["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
