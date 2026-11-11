"""Which compaction policy keeps the provider's cache: simulate a task, count prefix breaks, price them.

A task appends one tool result per step; before each call the worker compacts old results. Every
compaction rewrites a message that was already sent, and the provider then re-reads everything from
the first changed message (cache_hit ~= tokens before it). This script runs the old policy (C8,
git 8568453^), the current one (C18) and a candidate (two tiers) over the tool-result sizes measured
in this project's own task_steps, and prints breaks and dollars per 30-step task.

Run:  .venv/bin/python scripts/compact_sim.py [--tasks 200] [--steps 30]
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MARK = "\n… (shortened to keep the context small; call the tool again if you need the rest)"
TINY = "\n… (earlier result omitted; call the tool again if you need it)"
HIT_PRICE, MISS_PRICE = 0.50 / 1e6, 2.02 / 1e6      # $/token, đo 11/11 (C13–C17)
CHARS_PER_TOKEN = 4.0
# 每条工具结果的字数：本机 task_steps 里实测的分布（<1k: 101, 1–2.5k: 42, 2.5–5k: 58, 5–8k: 163）
SIZES = [(326, 0.28), (1767, 0.12), (3534, 0.16), (5927, 0.44)]
SYSTEM_CHARS, GOAL_CHARS, SAY_CHARS = 8732, 300, 120
KEEP, OLD_CHARS, COMPACT_AT, GOAL = 3, 1500, 60000, 20000


FIXED = 0


def sizes(rng, steps):
    if FIXED:
        return [FIXED] * steps
    pool = [s for s, w in SIZES for _ in range(int(w * 100))]
    return [rng.choice(pool) for _ in range(steps)]


def old_cut(msgs):
    """C8: 只有“长结果”的总量过线才动手，一次把所有非最近的长结果都截到 1500 字。"""
    long_ones = [i for i, m in enumerate(msgs) if m["role"] == "tool" and len(m["content"]) > OLD_CHARS]
    if len(long_ones) <= KEEP:
        return
    if sum(len(msgs[i]["content"]) for i in long_ones) <= COMPACT_AT:
        return
    for i in long_ones[:-KEEP] if KEEP else long_ones:
        c = msgs[i]["content"]
        if len(c) > OLD_CHARS:
            msgs[i]["content"] = c[:OLD_CHARS] + MARK


def new_cut(msgs):
    """C18: 一次截到 goal 以下，为后面的步留出余量。"""
    tools = [i for i, m in enumerate(msgs) if m["role"] == "tool"]
    total = sum(len(msgs[i]["content"]) for i in tools)
    if total <= COMPACT_AT:
        return
    for i in tools[:-KEEP] if KEEP else tools:
        c = msgs[i]["content"]
        if len(c) <= OLD_CHARS or c.endswith(MARK):
            continue
        msgs[i]["content"] = c[:OLD_CHARS] + MARK
        total -= len(c) - len(msgs[i]["content"])
        if total <= GOAL:
            break


def tiered_cut(msgs):
    """候选 C21: 截到 1500 字还不够时，把最老的那些再收成一行，直到真的到 goal 以下。"""
    tools = [i for i, m in enumerate(msgs) if m["role"] == "tool"]
    total = sum(len(msgs[i]["content"]) for i in tools)
    if total <= COMPACT_AT:
        return
    for i in tools[:-KEEP] if KEEP else tools:
        c = msgs[i]["content"]
        if len(c) <= OLD_CHARS or c.endswith(MARK):
            continue
        msgs[i]["content"] = c[:OLD_CHARS] + MARK
        total -= len(c) - len(msgs[i]["content"])
        if total <= GOAL:
            break
    for i in tools[:-KEEP] if KEEP else tools:          # 还是太胖：最老的收成一行
        c = msgs[i]["content"]
        if len(c) <= len(TINY) + 50 or c.endswith(TINY):
            continue
        msgs[i]["content"] = TINY
        total -= len(c) - len(TINY)
        if total <= GOAL:
            break


def run(policy, steps, rng):
    msgs = [{"role": "system", "content": "x" * SYSTEM_CHARS},
            {"role": "user", "content": "y" * GOAL_CHARS}]
    prev, breaks, cost, miss_tokens = None, 0, 0.0, 0
    for size in sizes(rng, steps):
        msgs.append({"role": "assistant", "content": "z" * SAY_CHARS})
        msgs.append({"role": "tool", "content": "Exit code 0\n" + "a" * size})
        policy(msgs)
        body = [m["content"] for m in msgs]
        total_tokens = sum(len(c) for c in body) / CHARS_PER_TOKEN
        kept = 0
        if prev is not None:
            at = next((i for i, (a, b) in enumerate(zip(prev, body)) if a != b), None)
            if at is None:            # phần mở rộng nguyên văn: nhà cung cấp phục vụ cả body trước
                kept = sum(len(c) for c in prev) / CHARS_PER_TOKEN
            else:                     # có tin đã gửi bị sửa: đọc lại từ chỗ đó
                breaks += 1
                kept = sum(len(c) for c in prev[:at]) / CHARS_PER_TOKEN
        missed = total_tokens - kept
        cost += kept * HIT_PRICE + missed * MISS_PRICE
        miss_tokens += missed
        prev = body
    return breaks, cost, miss_tokens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=int, default=200)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--fixed", type=int, default=0, help="mọi kết quả tool dài đúng chừng này ký tự")
    a = ap.parse_args()
    global FIXED
    FIXED = a.fixed
    for name, policy in (("C8  cũ", old_cut), ("C18 hiện tại", new_cut), ("C21 hai tầng", tiered_cut)):
        rng = random.Random(7)
        rows = [run(policy, a.steps, rng) for _ in range(a.tasks)]
        breaks = sum(r[0] for r in rows) / a.tasks
        cost = sum(r[1] for r in rows) / a.tasks
        miss = sum(r[2] for r in rows) / a.tasks
        print(f"{name:<14} breaks/task {breaks:5.1f}   miss {miss:8.0f} tok   ${cost:6.4f}/task")


if __name__ == "__main__":
    main()
