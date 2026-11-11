#!/usr/bin/env python
"""Replay saved request bodies in order and print what the provider says was cached.

For a body that is a verbatim extension of the one before, the provider should report the
whole earlier request as a hit. Real turns report 1152, so replaying the pair says whether
the bodies or the traffic is to blame. `--nostream` sends them as plain calls instead.
"""
import json, sys
from openai import OpenAI

key = ""
for line in open("/home/boxes/osa/.env"):
    if line.startswith("XAI_API_KEY="):
        key = line.split("=", 1)[1].strip().strip('"')
c = OpenAI(base_url="https://api.x.ai/v1", api_key=key, max_retries=0)
stream = "--nostream" not in sys.argv
files = [a for a in sys.argv[1:] if a.endswith(".json")]

for f in files:
    b = json.load(open(f))
    b.pop("ts", None)
    usage = None
    if stream:
        b["stream"] = True
        b["stream_options"] = {"include_usage": True}
        n = 0
        for ch in c.chat.completions.create(**b):
            if ch.usage:
                usage = ch.usage
            n += 1
    else:
        b.pop("stream_options", None)
        usage = c.chat.completions.create(**b).usage
    d = usage.prompt_tokens_details
    print(f"{f.split('/')[-1][:32]:34} msgs={len(b['messages']):3} stream={stream!s:5} "
          f"hit={getattr(d,'cached_tokens',0):6} total={usage.prompt_tokens:6} out={usage.completion_tokens}")
