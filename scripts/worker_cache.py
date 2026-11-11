#!/usr/bin/env python3
"""Worker cache: the numbers, and the reason behind them (C18).

  .venv/bin/python scripts/worker_cache.py                  # mọi lần gọi worker đã ghi
  .venv/bin/python scripts/worker_cache.py --since 1794392000
  .venv/bin/python scripts/worker_cache.py --bodies /home/boxes/osa-data/prompts2

Phần đầu trả lời "miss bao nhiêu %". Phần --bodies trả lời câu mà cache_hit không nói được:
request này có phải phần MỞ RỘNG NGUYÊN VĂN của request trước hay không, và nếu không thì
tin đầu tiên khác nhau là tin nào (đó là chỗ tiền cache bị mất). Bodies do prompt-dump ghi:
  printf '<thư mục>' > $OSA_DATA_DIR/prompt-dump
"""
import argparse
import glob
import json
import os
import sqlite3

DB = os.path.join(os.environ.get("OSA_DATA_DIR", "/home/boxes/osa-data"), "osa.db")
WORKER_MARK = "You are the Worker executing a task"


def db_report(since, role):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "select task_id, count(*), sum(cache_hit), sum(cache_miss), sum(cost),"
        " sum(case when cache_hit <= 1152 and cache_miss > 0 then 1 else 0 end)"
        " from llm_calls where role=? and ts>=? group by task_id order by task_id", (role, since)).fetchall()
    if not rows:
        print(f"không có lần gọi nào của {role} từ {since}")
        return
    print(f"{'task':>6} {'calls':>5} {'hit':>9} {'miss':>9} {'miss%':>6} {'$':>8} {'1152-only':>9}")
    th = tm = tc = tb = 0
    for task, n, hit, miss, cost, only in rows:
        hit, miss, cost, only = hit or 0, miss or 0, cost or 0.0, only or 0
        th, tm, tc, tb = th + hit, tm + miss, tc + cost, tb + only
        pct = 100.0 * miss / (hit + miss) if hit + miss else 0.0
        print(f"{str(task):>6} {n:>5} {hit:>9} {miss:>9} {pct:>5.1f}% {cost:>8.4f} {only:>9}")
    pct = 100.0 * tm / (th + tm) if th + tm else 0.0
    print(f"{'TỔNG':>6} {sum(r[1] for r in rows):>5} {th:>9} {tm:>9} {pct:>5.1f}% {tc:>8.4f} {tb:>9}")


def body_kind(body):
    msgs = body.get("messages") or []
    first = msgs[0].get("content") if msgs else ""
    text = first if isinstance(first, str) else json.dumps(first)
    return "worker" if WORKER_MARK in text[:600] else "router"


def size(msgs):
    return sum(len(m.get("content") or "") if isinstance(m.get("content"), str) else len(json.dumps(m.get("content") or "")) for m in msgs)


def first_difference(a, b):
    """index tin đầu tiên khác nhau giữa hai body (None = b là phần mở rộng của a)."""
    for i, m in enumerate(a):
        if i >= len(b):
            return i
        if json.dumps(m, sort_keys=True, ensure_ascii=False) != json.dumps(b[i], sort_keys=True, ensure_ascii=False):
            return i
    return None


def bodies_report(directory, kind):
    """So từng cặp body LIỀN NHAU TRONG CÙNG MỘT TASK (nhiều task chạy song song thì nhóm theo mục tiêu)."""
    chains = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        try:
            body = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if body_kind(body) != kind:
            continue
        msgs = body.get("messages") or []
        goal = json.dumps(msgs[1].get("content"), ensure_ascii=False) if len(msgs) > 1 else ""
        chains.setdefault(goal, []).append((path, msgs))
    for goal, chain in chains.items():
        label = goal[:64] + "…" if len(goal) > 64 else goal
        print(f"\n== {label}  ({len(chain)} body)")
        _chain(chain)


def _chain(chain):
    prev = None
    hit = miss = 0
    for path, msgs in chain:
        if prev is None:
            print(f"{os.path.basename(path)[:16]}  bắt đầu ({len(msgs)} tin, {size(msgs)} ký tự)")
        else:
            at = first_difference(prev[1], msgs)
            kept = len(prev[1]) if at is None else at
            if at is None:
                hit += 1
                print(f"{os.path.basename(path)[:16]}  nối tiếp ✓  {len(msgs)} tin, {size(msgs)} ký tự")
            else:
                miss += 1
                print(f"{os.path.basename(path)[:16]}  ĐỨT ở tin {at} (giữ {kept}/{len(prev[1])})  {len(msgs)} tin, {size(msgs)} ký tự")
                a, b = prev[1][at], msgs[at] if at < len(msgs) else {}
                print(f"    trước: {json.dumps(a, ensure_ascii=False)[:160]}")
                print(f"    sau  : {json.dumps(b, ensure_ascii=False)[:160]}")
        prev = (path, msgs)
    if hit + miss:
        print(f"\n{hit} nối tiếp / {miss} đứt ({100.0 * miss / (hit + miss):.0f}% đứt)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=float, default=0)
    ap.add_argument("--role", default="worker")
    ap.add_argument("--bodies")
    ap.add_argument("--kind", default="worker", choices=["worker", "router"])
    a = ap.parse_args()
    if a.bodies:
        bodies_report(a.bodies, a.kind)
    else:
        db_report(a.since, a.role)


if __name__ == "__main__":
    main()
