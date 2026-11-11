#!/usr/bin/env python3
"""Đọc log ra những lỗi lặp lại và gợi ý một kịch bản eval cho mỗi lỗi.

    python scripts/scenario_from_log.py [osa.log] [--min 2] [--json]

Mỗi dòng WARNING/ERROR được rút về một "dấu" (bỏ thời gian, số, id, đường dẫn tạm) để đếm.
Dấu nào gặp >= --min lần thì in ra một khung YAML cho tests/evals/scenarios/ (xem docs/vi/eval.md).
Dấu nào đã có kịch bản nhắc tới (notes có dòng "log: ...") thì bỏ qua, trừ khi --all.
Chỉ dùng stdlib, không cần import osa. Đây là mục 2 của vòng C trong docs/ke-hoach-super-bot.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_LOG = Path("/home/boxes/osa-data/logs/osa.log")
# 2026-11-11 06:45:10,377 I logger: message  |  2026-11-11 06:45:10 W osa.x: message  |  ERROR:    message
LINE = re.compile(r"^(?:(?P<date>\d{4}-\d\d-\d\d) (?P<time>\d\d:\d\d:\d\d)[,\d]* +(?P<level>[A-Z]) +)?"
                  r"(?:(?P<level2>ERROR|WARNING|CRITICAL):?\s+)?(?P<msg>.*)$")
WORDS = re.compile(r"[a-zà-ỹ0-9]+", re.I)
AREA = (  # 关键词 → area, dùng cho kịch bản gợi ý
    (("computer", "instabox", "vnc", "cdp", "chrome", "browser"), "computer"),
    (("telegram", "discord", "feishu", "dingtalk", "wecom", "channel"), "channels"),
    (("approval", "approve", "card"), "approval"),
    (("sandbox", "bwrap", "quick_code"), "sandbox"),
    (("provider", "stream", "openai", "429", "5xx", "timeout", "ttft"), "provider"),
    (("group", "handoff", "dm", "bot"), "multi-bot"),
    (("sqlite", "database", "db"), "storage"),
)


def level_of(raw: str) -> str:
    """W / E / I / D；uvicorn 那种 'ERROR:' 也算 E。"""
    m = LINE.match(raw.strip())
    if not m:
        return ""
    tag = (m.group("level") or m.group("level2") or "").upper()
    return {"W": "W", "WARNING": "W", "E": "E", "ERROR": "E", "CRITICAL": "E"}.get(tag, "")


def signature(raw: str) -> str:
    """去掉时间、数字、id、临时路径以后剩下的部分：同一个 lỗi 的几次看起来一样。"""
    m = LINE.match(raw.strip())
    text = m.group("msg") if m else raw
    text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<id>", text, flags=re.I)
    text = re.sub(r"/tmp/[^\s'\"]+", "<tmp>", text)
    text = re.sub(r"\b0x[0-9a-f]+\b", "<hex>", text, flags=re.I)
    text = re.sub(r"\d+(?:\.\d+)?", "<n>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:160]


def suggest(raw: str) -> dict:
    """一条日志行 → 建议的 kịch bản（id 留给写的人填）。"""
    low = raw.lower()
    area = next((a for words, a in AREA if any(w in low for w in words)), "general")
    sig = signature(raw)
    words = [w for w in WORDS.findall(sig.lower()) if w not in ("the", "a", "an", "in", "on", "of", "to")][:5]
    return {"area": area, "slug": "_".join(words) or "error", "signature": sig,
            "title": (sig.split(". ")[0] or "lỗi chưa rõ")[:110]}


def scan(lines, min_count: int = 2) -> list[dict]:
    """按 dấu đếm WARNING/ERROR；>= min_count 的按次数从多到少排。"""
    seen: dict[str, dict] = {}
    for n, raw in enumerate(lines, 1):
        raw = raw.rstrip("\n")
        lvl = level_of(raw)
        if lvl not in ("W", "E"):
            continue
        sig = signature(raw)
        if not sig:
            continue
        item = seen.setdefault(sig, {**suggest(raw), "count": 0, "first": n, "last": n,
                                     "levels": set(), "sample": ""})
        item["count"] += 1
        item["last"] = n
        item["levels"].add(lvl)
        item["sample"] = item["sample"] or raw.strip()[:200]
    out = [x for x in seen.values() if x["count"] >= min_count]
    for x in out:
        x["levels"] = "".join(sorted(x["levels"]))
        x["severity"] = "error" if "E" in x["levels"] else "warning"
    return sorted(out, key=lambda x: (-x["count"], x["first"]))


def skeleton(item: dict) -> str:
    return (f"# {item['count']}× {item['severity']} (dòng {item['first']}..{item['last']})\n"
            f"# {item['sample']}\n"
            f"id: e32_<việc>\n"
            f"title: {item['title']}\n"
            f"area: {item['area']}\n"
            f"bots: [BotA]\n"
            f"script:\n"
            f"  router:BotA:\n"
            f"    - \"...\"\n"
            f"input: {{to: BotA, text: \"...\"}}\n"
            f"expect:\n"
            f"  tasks: 0\n"
            f"notes: |\n"
            f"  log: {item['signature']}\n")


def covered(item: dict, scenarios: Path) -> bool:
    """dấu này đã có kịch bản nào nhắc tới chưa（notes 里写了 log: ...）。"""
    if not scenarios.is_dir():
        return False
    needle = item["signature"].lower()
    for p in scenarios.glob("*.yaml"):
        try:
            if needle in p.read_text(encoding="utf-8").lower():
                return True
        except OSError:
            continue
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lỗi lặp trong log → gợi ý kịch bản eval")
    ap.add_argument("log", nargs="?", default=str(DEFAULT_LOG))
    ap.add_argument("--min", type=int, default=2, help="gặp ít nhất mấy lần (mặc định 2)")
    ap.add_argument("--scenarios", default=str(Path(__file__).resolve().parent.parent / "tests/evals/scenarios"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="kể cả dấu đã có kịch bản nhắc tới")
    a = ap.parse_args(argv)
    try:
        lines = Path(a.log).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        print(f"không đọc được {a.log}: {e}", file=sys.stderr)
        return 2
    items = scan(lines, a.min)
    if not a.all:
        items = [x for x in items if not covered(x, Path(a.scenarios))]
    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return 0
    if not items:
        print(f"không có lỗi nào lặp >= {a.min} lần trong {a.log}")
        return 0
    print(f"{len(items)} lỗi lặp trong {a.log}:\n")
    for x in items:
        print(skeleton(x))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
