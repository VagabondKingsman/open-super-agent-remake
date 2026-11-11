"""Does the provider's cache serve an *extension* of a body it just saw? The worker's exact pattern.

Builds a growing conversation (system + goal + N pairs of assistant/tool results, ~2000 tokens each)
and sends it step by step, the way memory.keep_tail does in a task. For each step print
cached/prompt tokens: a working cache gives near-100% of the previous step's body.

Run:  .venv/bin/python scripts/cache_extend_probe.py [--steps 8] [--size 8000]
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from osa import providers  # noqa: E402

SYSTEM = ("You are the Worker executing a task. Every step appends one tool result; never restate it. "
          "Answer in one short sentence.")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--size", type=int, default=8000, help="characters per tool result")
    a = ap.parse_args()
    client = providers.client("xai")
    model = "grok-4.7"
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "Đếm các bước đã chạy."}]
    prev = 0
    for step in range(1, a.steps + 1):
        msgs.append({"role": "assistant", "content": f"Bước {step}."})
        msgs.append({"role": "user", "content": "Exit code 0\n" + "a" * a.size})
        r = await client.chat.completions.create(model=model, messages=msgs[:],
                                                 max_tokens=8, stream=False)
        u = r.usage
        d = getattr(u, "prompt_tokens_details", None)
        cached = getattr(d, "cached_tokens", 0) or 0
        print(f"bước {step}: prompt {u.prompt_tokens:>7} cached {cached:>7} "
              f"({100.0 * cached / max(1, u.prompt_tokens):>5.1f}%)  trước đó {prev}")
        prev = u.prompt_tokens


if __name__ == "__main__":
    asyncio.run(main())
