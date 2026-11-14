#!/usr/bin/env python
"""Does xAI share a prompt cache across requests unless they share a conversation id?

The service's own numbers say a turn's first call is cold (1152 cached tokens) while its
second call, a second later, is warm. Two verifications of the body (scripts/cache_extend_probe.py)
show the second turn's body is a verbatim extension of the first, so the body is not the reason.

Here the same body goes twice, twice: once with an identical `x-grok-conv-id`, once with none.
"""
import _paths, json, os, sys, time
from openai import OpenAI

body = json.load(open(sys.argv[1]))
body.pop("ts", None)
key = ""
for line in open(_paths.ROOT / ".env"):
    if line.startswith("XAI_API_KEY="):
        key = line.split("=", 1)[1].strip().strip('"')
c = OpenAI(base_url="https://api.x.ai/v1", api_key=key, max_retries=0)
body.pop("stream_options", None)


def one(headers=None, label=""):
    t = time.time()
    r = c.chat.completions.create(**body, extra_headers=headers or {})
    d = r.usage.prompt_tokens_details
    print(f"{label:28} hit={getattr(d, 'cached_tokens', 0):6} miss={r.usage.prompt_tokens:6} "
          f"out={r.usage.completion_tokens:4} {time.time()-t:5.1f}s")
    return r


conv = {"x-grok-conv-id": "osa-probe-1"}
one(conv, "with conv id   #1")
one(conv, "with conv id   #2")
time.sleep(20)
one(conv, "with conv id   #3 (20s)")
one(None, "no conv id     #1")
one(None, "no conv id     #2")
