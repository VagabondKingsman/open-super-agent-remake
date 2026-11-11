"""How does the provider's prompt cache actually behave? A direct experiment, no app in the way.

Three requests with a long shared prefix:
  A  the reference request,
  B  byte-identical to A                       -> if the cache works at all, this is a full hit,
  C  same prefix, one sentence changed near the top  -> how much of a hit survives a head change,
  D  same prefix, changed at the very end           -> should keep nearly everything.
Run:  XAI_API_KEY=... .venv/bin/python scripts/cache_probe.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from osa import providers  # noqa: E402

FILLER = ("The maintenance log records that the pump was inspected, the valve was reseated, and the reading was "
          "written down twice so the second person could check it. ") * 8
PAD = ("\n".join(f"Step {i}: {FILLER}" for i in range(1, 26)))   # ~10k tokens of stable text


async def call(client, model: str, head: str, tail: str) -> dict:
    r = await client.chat.completions.create(
        model=model, messages=[{"role": "system", "content": head + PAD},
                               {"role": "user", "content": tail}],
        max_tokens=8, stream=False)
    u = r.usage
    d = getattr(u, "prompt_tokens_details", None)
    return {"prompt": u.prompt_tokens, "cached": getattr(d, "cached_tokens", 0) or 0, "out": u.completion_tokens}


async def main() -> None:
    client = providers.client(os.environ.get("OSA_AB_PROVIDER", "xai"))
    model = os.environ.get("OSA_AB_MODEL", "grok-4.7")
    head = "You are a maintenance assistant. Answer in one word.\n"
    rows = []
    for label, h, tail in (
            ("A  reference", head, "Say OK."),
            ("B  identical", head, "Say OK."),
            ("C  head changed", head.replace("maintenance", "repair"), "Say OK."),
            ("D  tail changed", head, "Say FINE."),
            ("E  identical again", head, "Say FINE.")):
        r = await call(client, model, h, tail)
        rows.append((label, r))
        print(f"{label:18s} prompt={r['prompt']:6d} cached={r['cached']:6d} "
              f"({100 * r['cached'] / max(1, r['prompt']):5.1f}%) out={r['out']}")


if __name__ == "__main__":
    asyncio.run(main())
