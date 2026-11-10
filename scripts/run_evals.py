#!/usr/bin/env python3
"""Chạy bộ eval offline của OSAR, ra bảng điểm và so với baseline.

    uv run python scripts/run_evals.py                  # chạy, ghi evals-out/, so với tests/evals/baseline.json
    uv run python scripts/run_evals.py --update-baseline  # chạy rồi ghi kết quả làm baseline mới (commit file đó)
    uv run python scripts/run_evals.py -k e19            # chỉ vài kịch bản (không so baseline)

Ghi ra --out (mặc định evals-out/):
  results.json   từng kịch bản: success, steps, số lần gọi model, token, chi phí mô phỏng (prices.py), thời gian
  scorecard.md   bảng điểm để đọc (CI đính kèm làm artifact)
  gate.json      kết quả cổng (scripts/eval_gate.py)
Exit code: 0 PASS/WARN, 1 cổng FAIL, 2 không chạy được hoặc không đọc được kết quả.
Không gọi mạng, không tốn tiền model: mô hình là tests/fakellm.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tests" / "evals" / "baseline.json"
sys.path.insert(0, str(ROOT / "scripts"))
import eval_gate  # noqa: E402


def _scenarios() -> dict[str, dict]:
    import yaml
    out = {}
    for p in sorted((ROOT / "tests" / "evals" / "scenarios").glob("*.yaml")):
        s = yaml.safe_load(p.read_text(encoding="utf-8"))
        out[s["id"]] = s
    return out


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def run_pytest(out: Path, select: str | None) -> tuple[int, Path]:
    xml = out / "junit.xml"
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "eval", "tests/test_evals.py",
           f"--junitxml={xml}", "-o", "junit_family=xunit1"]
    if select:
        cmd += ["-k", select]
    r = subprocess.run(cmd, cwd=ROOT)
    return r.returncode, xml


def collect(xml: Path, scenarios: dict[str, dict]) -> list[dict]:
    tasks = {}
    for case in ET.parse(xml).getroot().iter("testcase"):
        name = case.get("name", "")
        if not name.startswith("test_eval[") :
            continue
        sid = name[len("test_eval["):-1]
        s = scenarios.get(sid, {})
        props = {p.get("name"): p.get("value") for p in case.iter("property")}
        m = json.loads(props["eval"]) if "eval" in props else {}
        skipped = case.find("skipped")
        failed = case.find("failure") is not None or case.find("error") is not None
        xfail = skipped is not None and (skipped.get("type") == "pytest.xfail" or "xfail" in (skipped.get("message") or ""))
        if xfail:
            outcome = "xfail"
        elif skipped is not None:
            outcome = "skipped"
        else:
            outcome = "failed" if failed else "passed"
        tasks[sid] = {"id": sid, "title": s.get("title", ""), "area": s.get("area", ""), "outcome": outcome,
                      "success": outcome == "passed", "safety": bool(s.get("safety")),
                      "expected_fail": bool(s.get("xfail")), "known_gap": s.get("xfail") or "",
                      **{k: m[k] for k in ("steps", "llm_calls", "tasks", "tokens_in", "tokens_out", "cost_usd", "latency_ms")
                         if k in m},
                      "failures": m.get("failures") or ([(skipped.get("message") or "")[:300]] if outcome == "skipped" else [])}
    return [tasks[k] for k in sorted(tasks)]


def scorecard(res: dict, gate: dict | None) -> str:
    t = res["tasks"]
    ok = sum(1 for x in t if x["success"])
    lines = [f"# OSAR eval scorecard — {res['osa_commit'] or 'local'} ({res['created_at']})", "",
             f"**Success: {ok}/{len(t)} ({100 * ok / len(t):.1f}%)** · "
             f"known gaps (xfail): {sum(1 for x in t if x['outcome'] == 'xfail')} · "
             f"skipped: {sum(1 for x in t if x['outcome'] == 'skipped')} · "
             f"worker steps: {sum(x.get('steps', 0) for x in t)} · model calls: {sum(x.get('llm_calls', 0) for x in t)} · "
             f"simulated cost: ${sum(x.get('cost_usd', 0) for x in t):.6f}", ""]
    if gate:
        lines += ["## Gate", "", "```", eval_gate.render(gate), "```", ""]
    lines += ["## Scenarios", "", "| id | area | result | steps | model calls | tokens in/out | cost (USD) | ms | note |",
              "|---|---|---|---|---|---|---|---|---|"]
    mark = {"passed": "PASS", "failed": "**FAIL**", "xfail": "xfail", "skipped": "SKIP"}
    for x in t:
        note = x["known_gap"] or "; ".join(x["failures"])[:160]
        lines.append(f"| {x['id']}{' 🛡' if x['safety'] else ''} | {x['area']} | {mark[x['outcome']]} | {x.get('steps', '')} | "
                     f"{x.get('llm_calls', '')} | {x.get('tokens_in', '')}/{x.get('tokens_out', '')} | {x.get('cost_usd', '')} | "
                     f"{x.get('latency_ms', '')} | {note.replace('|', '/')} |")
    lines += ["", "🛡 = safety scenario. xfail = known gap with a task id; it must keep failing until that task fixes it."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(ROOT / "evals-out"))
    ap.add_argument("--baseline", default=str(BASELINE))
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("-k", dest="select", help="pytest -k expression (partial run: no baseline comparison)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    code, xml = run_pytest(out, a.select)
    if not xml.exists():
        print("evals: pytest produced no report", file=sys.stderr)
        return 2
    res = {"schema_version": eval_gate.SCHEMA_VERSION, "suite": "osar-offline", "osa_commit": _commit(),
           "created_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "tasks": collect(xml, _scenarios())}
    if not res["tasks"]:
        print("evals: no scenario ran", file=sys.stderr)
        return 2
    (out / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    gate = None
    if a.update_baseline:
        if a.select:
            print("evals: refusing to write a baseline from a partial run (-k)", file=sys.stderr)
            return 2
        bad = [x["id"] for x in res["tasks"] if x["outcome"] in ("failed", "skipped")]
        if bad:
            print(f"evals: refusing to write a baseline with failed/skipped scenarios: {', '.join(bad)}", file=sys.stderr)
            return 1
        keep = ("id", "area", "success", "safety", "expected_fail", "steps", "llm_calls", "tokens_in", "tokens_out", "cost_usd")
        base = {k: res[k] for k in ("schema_version", "suite", "osa_commit")} | {
            "tasks": [{k: x[k] for k in keep if k in x} for x in res["tasks"]]}
        Path(a.baseline).write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"evals: baseline written to {a.baseline}")
    elif not a.select:
        try:
            gate = eval_gate.gate(eval_gate.load(a.baseline), eval_gate.load(out / "results.json"))
        except ValueError as e:
            print(f"evals: {e}", file=sys.stderr)
            return 2
        (out / "gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    md = scorecard(res, gate)
    (out / "scorecard.md").write_text(md, encoding="utf-8")
    print(md)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as f:
            f.write(md)
    if gate:
        return 1 if gate["verdict"] == "FAIL" else 0
    return 0 if code in (0, 1) and not any(x["outcome"] == "failed" for x in res["tasks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
