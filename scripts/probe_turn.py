#!/usr/bin/env python
"""Đo một turn thật qua /ws: mở socket, gửi tin, in mốc thời gian từng frame.

    .venv/bin/python scripts/probe_turn.py "câu hỏi" [chat_id]

Cookie: /tmp/ck. Dùng cho A2 (ttft trước/sau khi sửa prompt), A3 (frame tool), A4 (telemetry).
"""
import asyncio
import json
import sys
import time

import websockets


def cookie() -> str:
    for line in open("/tmp/ck"):
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        elif line.startswith("#") or not line.strip():
            continue
        f = line.split("\t")
        if len(f) >= 7 and f[5] in ("osa_session", "session"):
            return f"{f[5]}={f[6].strip()}"
    raise SystemExit("no session cookie in /tmp/ck")


async def main(text: str, chat_id: int) -> None:
    jar = cookie()
    t0 = time.monotonic()
    frames = []
    async with websockets.connect("ws://127.0.0.1:8765/ws",
                                  additional_headers={"Cookie": jar}) as ws:
        opened = time.monotonic()
        await ws.send(json.dumps({"type": "send", "chat_id": chat_id, "text": text}))
        first = {}
        kinds = {}
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=120)
            except asyncio.TimeoutError:
                break
            try:
                m = json.loads(raw)
            except Exception:
                continue
            t = time.monotonic() - t0
            kind = m.get("type")
            kinds[kind] = kinds.get(kind, 0) + 1
            if kind == "stream":
                key = "thinking" if m.get("thinking") else "delta"
                first.setdefault(key, round(t, 2))
            if kind == "message" and (m.get("message") or {}).get("role") == "user":
                continue   # 自己那条消息的回声，不是回答
            if kind in ("message", "error"):
                msg = m.get("message") or {}
                frames.append({"t": round(t, 2), "type": kind,
                               "thought_s": (msg.get("meta") or {}).get("thought_s"),
                               "text": (msg.get("content") or "")[:80]})
                break
    print(json.dumps({"open_s": round(opened - t0, 3), "chat": chat_id,
                      "first_thinking_s": first.get("thinking"),
                      "first_delta_s": first.get("delta"),
                      "total_s": round(time.monotonic() - t0, 2),
                      "frames_by_type": kinds, "tail": frames}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "17*23 bằng mấy?",
                     int(sys.argv[2]) if len(sys.argv) > 2 else 1))
