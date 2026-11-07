#!/usr/bin/env python3
"""retro_rubric.py · Engine chấm điểm Retro Rubric 5 chiều & điều phối đệ quy tự tối ưu.

Công cụ tất định hỗ trợ vòng lặp BUILD ⇄ RETRO RUBRIC trong Vibecode Kit:
  - Chấm điểm 5 chiều (R1: Spec, R2: Runtime/Test, R3: Edge-Case, R4: Hygiene/Blast-Radius, R5: Anti-Repeat).
  - Bắt buộc đúc kết bài học (RETRO-ID: Symptom -> Root Cause -> Guardrail + Test) sau mỗi vòng thử sai.
  - Chặn việc chạy vòng thử mới nếu vòng trước FAIL mà chưa ghi nhận quy tắc RETRO-ID.
  - Tự động kích hoạt Cầu chì (Circuit Breaker) khi chạm trần 3 vòng đệ quy liên tiếp chưa đạt chuẩn.
  - Chạy kiểm tra tự động toàn bộ các lệnh test chặn hồi quy (verify-guardrails).

Cách dùng:
  python3 retro_rubric.py init <project_dir> [--max-iterations 3]
  python3 retro_rubric.py evaluate <project_dir> --tip TIP-001 --r1 2 --r2 0 --r3 1 --r4 2 --r5 2 [--notes "..."]
  python3 retro_rubric.py learn <project_dir> --tip TIP-001 --symptom "..." --cause "..." --guardrail "..." [--test-cmd "..."]
  python3 retro_rubric.py verify-guardrails <project_dir>
  python3 retro_rubric.py report <project_dir> [--tip TIP-001]
  python3 retro_rubric.py selftest
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

STATE_FILENAME = "retro_rubric_state.json"
DIMENSIONS = {
    "r1": "R1 (Spec & Contract Fidelity)",
    "r2": "R2 (Runtime & Test Integrity)",
    "r3": "R3 (Edge-Case & Resilience)",
    "r4": "R4 (Blast-Radius, Hygiene & Pragmatic YAGNI)",
    "r5": "R5 (Anti-Repeat Discipline)",
}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _state_path(project_dir: Path) -> Path:
    vibe_dir = project_dir / ".vibecode"
    if vibe_dir.is_dir():
        return vibe_dir / STATE_FILENAME
    return project_dir / STATE_FILENAME


def load_state(project_dir: Path) -> dict:
    p = _state_path(project_dir)
    if not p.exists():
        return {
            "created_at": _now(),
            "max_iterations": 3,
            "pass_threshold": 9,
            "tips": {},
            "guardrails": [],
        }
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(project_dir: Path, state: dict) -> Path:
    p = _state_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def cmd_init(args) -> int:
    proj = Path(args.project_dir).resolve()
    proj.mkdir(parents=True, exist_ok=True)
    vibe_dir = proj / ".vibecode"
    vibe_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "created_at": _now(),
        "max_iterations": args.max_iterations,
        "pass_threshold": args.pass_threshold,
        "tips": {},
        "guardrails": [],
    }
    p = save_state(proj, state)
    print(f"RETRO RUBRIC INIT · max_iterations={args.max_iterations} · pass_threshold={args.pass_threshold}/10 → {p}")
    return 0


def cmd_evaluate(args) -> int:
    proj = Path(args.project_dir).resolve()
    state = load_state(proj)
    max_iter = state.get("max_iterations", 3)
    threshold = state.get("pass_threshold", 9)

    tip_state = state["tips"].setdefault(args.tip, {
        "status": "IN_PROGRESS",
        "iterations": [],
        "pending_lesson_from_iteration": None,
    })

    # Rule: If previous iteration failed, agent MUST record a RETRO-ID lesson before running next evaluation
    pending = tip_state.get("pending_lesson_from_iteration")
    if pending is not None:
        print(f"BLOCKED [MISSING_RETRO_LESSON] · {args.tip} vòng #{pending} bị trượt nhưng chưa đúc kết bài học RETRO-ID.")
        print(f"→ Bắt buộc chạy: python3 retro_rubric.py learn <project_dir> --tip {args.tip} --symptom ... --cause ... --guardrail ...")
        return 2

    scores = {"r1": args.r1, "r2": args.r2, "r3": args.r3, "r4": args.r4, "r5": args.r5}
    total = sum(scores.values())
    failed_dims = [k.upper() for k, v in scores.items() if v == 0]
    warn_dims = [k.upper() for k, v in scores.items() if v == 1]
    passed = (len(failed_dims) == 0) and (total >= threshold)

    iter_num = len(tip_state["iterations"]) + 1
    entry = {
        "iteration": iter_num,
        "timestamp": _now(),
        "scores": scores,
        "total": total,
        "failed_dimensions": failed_dims,
        "warn_dimensions": warn_dims,
        "notes": args.notes or "",
        "verdict": "PASS" if passed else ("ESCALATE" if iter_num >= max_iter else "RETRY"),
    }
    tip_state["iterations"].append(entry)

    if passed:
        tip_state["status"] = "PASSED"
        tip_state["pending_lesson_from_iteration"] = None
        save_state(proj, state)
        print(f"RETRO RUBRIC PASS ✓ · {args.tip} (Vòng #{iter_num}) · Điểm: {total}/10 · Khóa {len(state['guardrails'])} quy tắc RETRO-ID.")
        return 0

    # Failed the gate
    tip_state["pending_lesson_from_iteration"] = iter_num
    if iter_num >= max_iter:
        tip_state["status"] = "CIRCUIT_BREAKER_ESCALATED"
        save_state(proj, state)
        print(f"CIRCUIT BREAKER TRIPPED ✗ · {args.tip} đã chạm trần {max_iter} vòng đệ quy (Điểm vòng #{iter_num}: {total}/10, FAIL={failed_dims}).")
        print("→ Dừng tự sửa mò. Hãy ghi nhận bài học cuối và xuất Escalation Report (Level 2/3) cho Chủ thầu / Con người.")
        return 3

    tip_state["status"] = "NEEDS_RETRO_RETRY"
    save_state(proj, state)
    print(f"RETRO RUBRIC RETRY ↻ · {args.tip} (Vòng #{iter_num}/{max_iter}) chưa đạt chuẩn · Điểm: {total}/10 (Ngưỡng: {threshold}/10, FAIL={failed_dims}).")
    print(f"→ Bước tiếp theo bắt buộc: chạy lệnh 'learn' để trích xuất quy tắc RETRO-ID trước khi build vòng #{iter_num + 1}.")
    return 2


def cmd_learn(args) -> int:
    proj = Path(args.project_dir).resolve()
    state = load_state(proj)
    retro_id = f"RETRO-{len(state['guardrails']) + 1:02d}"
    rule = {
        "id": retro_id,
        "tip": args.tip,
        "created_at": _now(),
        "symptom": args.symptom.strip(),
        "root_cause": args.cause.strip(),
        "guardrail": args.guardrail.strip(),
        "test_cmd": (args.test_cmd or "").strip() or None,
    }
    state["guardrails"].append(rule)
    if args.tip in state["tips"]:
        state["tips"][args.tip]["pending_lesson_from_iteration"] = None
    save_state(proj, state)
    print(f"ĐÃ ĐÚC KẾT {retro_id} ({args.tip}) · Mở khóa vòng build tiếp theo.")
    print(f"  · Triệu chứng : {rule['symptom']}")
    print(f"  · Nguyên nhân : {rule['root_cause']}")
    print(f"  · Quy tắc chặn: {rule['guardrail']}")
    return 0


def cmd_verify_guardrails(args) -> int:
    proj = Path(args.project_dir).resolve()
    state = load_state(proj)
    guardrails = state.get("guardrails", [])
    if not guardrails:
        print("RETRO GUARDRAILS · Chưa có quy tắc RETRO-ID nào được ghi nhận (0 rules).")
        return 0

    failed = 0
    print("═" * 64)
    print(f"KIỂM TRA HỒI QUY RETRO GUARDRAILS · Tổng số: {len(guardrails)} quy tắc")
    print("═" * 64)
    for g in guardrails:
        cmd = g.get("test_cmd")
        if not cmd:
            print(f"  ✓ [DECLARATIVE] {g['id']} ({g['tip']}): {g['guardrail']}")
            continue
        proc = subprocess.run(cmd, shell=True, cwd=str(proj), capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"  ✓ [TEST PASS]   {g['id']} ({g['tip']}): {g['guardrail']} (`{cmd}`)")
        else:
            failed += 1
            print(f"  ✗ [REGRESSION]  {g['id']} ({g['tip']}) bị phá vỡ! (`{cmd}` → exit {proc.returncode})")
    print("─" * 64)
    if failed:
        print(f"FAIL · {failed} quy tắc RETRO-ID bị vi phạm (R5 = 0). Phải sửa trước khi qua cổng!")
        return 2
    print("PASS · 100% quy tắc RETRO-ID được bảo toàn (R5 = 2/2).")
    return 0


def cmd_report(args) -> int:
    proj = Path(args.project_dir).resolve()
    state = load_state(proj)
    tips = state.get("tips", {})
    target_tips = [args.tip] if args.tip and args.tip in tips else list(tips.keys())

    lines = ["## RETRO RUBRIC SCORECARD & RECURSIVE LOG", ""]
    if not target_tips:
        lines.append("_Chưa có dữ liệu chạy thử nào được ghi nhận._")
    for tid in target_tips:
        tinfo = tips[tid]
        lines.append(f"### {tid} · Trạng thái: `{tinfo['status']}`")
        lines.append("| Vòng thử | R1 (Spec) | R2 (Runtime) | R3 (Edge) | R4 (Hygiene) | R5 (No-Repeat) | Tổng | Kết quả | Ghi chú |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for it in tinfo.get("iterations", []):
            sc = it["scores"]
            lines.append(
                f"| Vòng #{it['iteration']} | {sc['r1']}/2 | {sc['r2']}/2 | {sc['r3']}/2 | {sc['r4']}/2 | {sc['r5']}/2 "
                f"| **{it['total']}/10** | `{it['verdict']}` | {it.get('notes', '')} |"
            )
        lines.append("")

    guardrails = state.get("guardrails", [])
    lines.append(f"### Quy tắc Phòng ngừa Đã Đúc kết (Active Retro Guardrails: {len(guardrails)})")
    if not guardrails:
        lines.append("- Không phát sinh lỗi cần đệ quy (First-pass clean).")
    else:
        for g in guardrails:
            lines.append(f"- **{g['id']}** (*từ {g['tip']}*): **Triệu chứng:** {g['symptom']} → **Nguyên nhân gốc:** {g['root_cause']} → **Quy tắc chặn:** {g['guardrail']}")
    print("\n".join(lines))
    return 0


def cmd_selftest(_args) -> int:
    with tempfile.TemporaryDirectory(prefix="retro_selftest_") as tmp:
        p = Path(tmp)
        # 1. Init
        assert cmd_init(argparse.Namespace(project_dir=str(p), max_iterations=3, pass_threshold=9)) == 0
        # 2. Iteration #1 fails R2 (Runtime=0) -> must return exit 2 (RETRY)
        rc1 = cmd_evaluate(argparse.Namespace(
            project_dir=str(p), tip="TIP-001", r1=2, r2=0, r3=1, r4=2, r5=2, notes="Null payload crash"
        ))
        assert rc1 == 2, f"Expected exit 2 on failed rubric, got {rc1}"
        # 3. Attempting Iteration #2 WITHOUT calling 'learn' must be blocked (exit 2)
        rc_blocked = cmd_evaluate(argparse.Namespace(
            project_dir=str(p), tip="TIP-001", r1=2, r2=2, r3=2, r4=2, r5=2, notes="Tried to skip learn"
        ))
        assert rc_blocked == 2, "Expected block when RETRO lesson not recorded"
        # 4. Record lesson via 'learn' with a runnable regression test command
        rc_learn = cmd_learn(argparse.Namespace(
            project_dir=str(p),
            tip="TIP-001",
            symptom="Crash khi payload rỗng",
            cause="Thiếu kiểm tra mảng mặc định",
            guardrail="Luôn chuẩn hóa mảng rỗng và kiểm tra bằng unit test",
            test_cmd="python3 -c 'assert isinstance([], list)'",
        ))
        assert rc_learn == 0
        # 5. Verify guardrails pass
        assert cmd_verify_guardrails(argparse.Namespace(project_dir=str(p))) == 0
        # 6. Iteration #2 passes all dimensions (10/10) -> exit 0
        rc2 = cmd_evaluate(argparse.Namespace(
            project_dir=str(p), tip="TIP-001", r1=2, r2=2, r3=2, r4=2, r5=2, notes="All tests & RETRO-01 green"
        ))
        assert rc2 == 0
        # 7. Test Circuit Breaker on TIP-002 (3 consecutive failures -> exit 3)
        for i in range(1, 4):
            rc_fail = cmd_evaluate(argparse.Namespace(
                project_dir=str(p), tip="TIP-002", r1=2, r2=0, r3=1, r4=2, r5=2, notes=f"Fail #{i}"
            ))
            if i < 3:
                assert rc_fail == 2
                cmd_learn(argparse.Namespace(
                    project_dir=str(p), tip="TIP-002",
                    symptom=f"Lỗi thử #{i}", cause="Chưa rõ", guardrail=f"Rule #{i}", test_cmd=None
                ))
            else:
                assert rc_fail == 3, f"Expected circuit breaker exit 3 on 3rd failure, got {rc_fail}"
    print("RETRO RUBRIC SELFTEST: TẤT CẢ CỔNG ĐỆ QUY & CẦU CHÌ HOẠT ĐỘNG CHUẨN ✓")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Engine chấm điểm Retro Rubric & Đệ quy tối ưu (Vibecode Kit)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Khởi tạo trạng thái Retro Rubric cho dự án")
    p_init.add_argument("project_dir")
    p_init.add_argument("--max-iterations", type=int, default=3)
    p_init.add_argument("--pass-threshold", type=int, default=9)

    p_eval = sub.add_parser("evaluate", help="Chấm điểm 1 vòng chạy thử theo 5 chiều R1..R5")
    p_eval.add_argument("project_dir")
    p_eval.add_argument("--tip", required=True)
    for dim in ("r1", "r2", "r3", "r4", "r5"):
        p_eval.add_argument(f"--{dim}", type=int, choices=[0, 1, 2], required=True)
    p_eval.add_argument("--notes", default="")

    p_learn = sub.add_parser("learn", help="Đúc kết quy tắc RETRO-ID sau vòng thử sai để mở khóa vòng kế tiếp")
    p_learn.add_argument("project_dir")
    p_learn.add_argument("--tip", required=True)
    p_learn.add_argument("--symptom", required=True)
    p_learn.add_argument("--cause", required=True)
    p_learn.add_argument("--guardrail", required=True)
    p_learn.add_argument("--test-cmd", default="")

    p_ver = sub.add_parser("verify-guardrails", help="Chạy kiểm tra toàn bộ các test chặn hồi quy RETRO-ID")
    p_ver.add_argument("project_dir")

    p_rep = sub.add_parser("report", help="Xuất bảng điểm và nhật ký đệ quy ra định dạng Markdown")
    p_rep.add_argument("project_dir")
    p_rep.add_argument("--tip", default="")

    sub.add_parser("selftest", help="Chạy kiểm thử tự động các cổng đệ quy và cầu chì")

    args = ap.parse_args()
    dispatch = {
        "init": cmd_init,
        "evaluate": cmd_evaluate,
        "learn": cmd_learn,
        "verify-guardrails": cmd_verify_guardrails,
        "report": cmd_report,
        "selftest": cmd_selftest,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
