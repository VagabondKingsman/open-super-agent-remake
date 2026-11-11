#!/usr/bin/env python3
"""Một trang báo cáo tuần từ /api/observe (osa/observe.py) và kết quả eval.

    python scripts/weekly_report.py                 # tuần vừa rồi, in ra màn hình
    python scripts/weekly_report.py --range 30d --out bao-cao.md
    python scripts/weekly_report.py --evals /tmp/evals-results.json

Đọc thẳng cơ sở dữ liệu của osa (cùng chỗ config.yaml chỉ), không cần đăng nhập web.
Số liệu: chi phí, token, số lần gọi, lỗi, ttft, tốc độ, task, tool hay lỗi, việc cần xem lại.
So với kỳ trước cùng độ dài: tăng > 20% thì đánh dấu. Mục eval chỉ có khi truyền --evals.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

UP = 1.20   # kỳ này hơn kỳ trước 20% thì ghi "tăng"


def _f(v, suffix="", nd=2):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{nd}f}{suffix}"
    return f"{v:,}{suffix}"


def _delta(now_v, before_v, *, worse_up: bool = True) -> str:
    """kỳ trước so với bây giờ；数字变小是好还是坏由 worse_up 决定。"""
    if now_v is None or before_v in (None, 0):
        return ""
    change = (now_v - before_v) / before_v
    if abs(change) < 0.05:
        return " ( như kỳ trước)"
    bad = (change > 0) == worse_up
    pct = f"{change * 100:+.0f}%"
    return f" ⚠️ {pct}" if bad and abs(change) >= (UP - 1) else f" ({pct})"


def page(s: dict, evals: dict | None = None, title: str | None = None) -> str:
    """Trang markdown từ stats() của observe (và bản kết quả eval nếu có)."""
    k, p = s["kpi"], s.get("prev") or {}
    start = time.strftime("%Y-%m-%d", time.localtime(s["start"]))
    end = time.strftime("%Y-%m-%d", time.localtime(s["end"]))
    out = [f"# {title or 'Báo cáo tuần'} {start} → {end}", ""]
    rows = [
        ("Chi phí", _f(k.get("cost"), " " + s.get("currency", "$"), 4), _f(p.get("cost"), "", 4),
         _delta(k.get("cost"), p.get("cost"))),
        ("Token vào", _f(k.get("input")), _f(p.get("input")), _delta(k.get("input"), p.get("input"))),
        ("Token ra", _f(k.get("output")), _f(p.get("output")), _delta(k.get("output"), p.get("output"))),
        ("Gọi model", _f(k.get("calls")), _f(p.get("calls")), ""),
        ("Lỗi gọi model", _f(k.get("errors")), _f(p.get("errors")), _delta(k.get("errors"), p.get("errors"))),
        ("Cache hit", _f((k.get("cache_rate") or 0) * 100, "%", 0), _f((p.get("cache_rate") or 0) * 100, "%", 0), ""),
        ("First token (router)", _f(k.get("ttft"), " ms", 0), _f(p.get("ttft"), " ms", 0),
         _delta(k.get("ttft"), p.get("ttft"))),
        ("Tốc độ ra", _f(k.get("speed"), " tok/s", 1), _f(p.get("speed"), " tok/s", 1), ""),
        ("Task", f"{_f(k.get('tasks'))} (xong {_f(k.get('done'))}, hỏng {_f(k.get('failed'))})", _f(p.get("tasks")), ""),
        ("Task thành công", _f(None if k.get("success") is None else k["success"] * 100, "%", 0),
         _f(None if p.get("success") is None else p["success"] * 100, "%", 0), ""),
        ("Gọi tool (lỗi)", f"{_f(k.get('tool_calls'))} ({_f(k.get('tool_errors'))})", "—", ""),
    ]
    out.append("| | kỳ này | kỳ trước |")
    out.append("|---|---|---|")
    for label, now_s, before_s, delta in rows:
        out.append(f"| {label} | {now_s}{delta} | {before_s} |")
    out.append("")

    if models := s.get("models") or []:
        out += ["## Model tốn nhiều nhất", "", "| model | vai trò gọi | $ | token | lỗi |", "|---|---|---|---|---|"]
        for m in models[:5]:
            out.append(f"| {m.get('model')} | {m.get('provider') or '—'} | {_f(m.get('cost'), '', 4)} | "
                       f"{_f(m.get('tokens'))} | {_f(m.get('errors'))} |")
        out.append("")
    if tools := [t for t in (s.get("tools") or []) if t.get("errors")]:
        out += ["## Tool có lỗi", "", "| tool | gọi | lỗi |", "|---|---|---|"]
        for t in tools[:8]:
            out.append(f"| {t.get('name')} | {_f(t.get('calls'))} | {_f(t.get('errors'))} |")
        out.append("")
    problems = s.get("problems") or []
    out += ["## Việc cần xem lại", ""]
    if not problems:
        out.append("Không có gì hỏng trong kỳ này.")
    for x in problems[:10]:
        what = x.get("title") or x.get("error") or x.get("name") or x.get("kind")
        out.append(f"- **{x.get('kind')}** ×{x.get('count') or 1}: {str(what)[:140]}")
    out.append("")

    if evals:
        tasks = evals.get("tasks") or []
        ok = [t for t in tasks if t.get("success")]
        out += ["## Eval", "", f"- {len(ok)}/{len(tasks)} kịch bản đạt"
                + (f" (commit {evals.get('osa_commit')})" if evals.get("osa_commit") else "")]
        for t in [t for t in tasks if not t.get("success")][:8]:
            out.append(f"- ❌ {t.get('id')} — {t.get('area') or ''}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _env_file(path: Path):
    """把 .env 里还没设的变量读进环境（和 scripts/osa-start.sh 一样）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Báo cáo tuần từ observe + eval")
    ap.add_argument("--range", default="7d", help="7d（mặc định）, 24h, 30d …")
    ap.add_argument("--tz", type=int, default=0, help="múi giờ tính theo phút (mặc định 0)")
    ap.add_argument("--evals", help="file kết quả eval (tuỳ chọn)")
    ap.add_argument("--out", help="ghi ra file thay vì in")
    ap.add_argument("--title")
    a = ap.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:   # 从别的目录运行脚本时也能 import osa
        sys.path.insert(0, str(root))
    _env_file(root / ".env")       # 服务器上的数据库在 OSA_DATA_DIR 里，值在 .env
    try:
        from osa import observe
    except Exception as e:   # 没有 osa 的环境（CI 只跑脚本）也要说清楚
        print(f"không import được osa.observe: {e}", file=sys.stderr)
        return 2
    stats = observe.stats(a.range, a.tz)
    evals = None
    if a.evals:
        try:
            evals = json.loads(Path(a.evals).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"không đọc được {a.evals}: {e}", file=sys.stderr)
            return 2
    body = page(stats, evals, a.title)
    if a.out:
        Path(a.out).write_text(body, encoding="utf-8")
        print(f"đã ghi {a.out}")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
