"""同一个问题连问 N 次，量答复的形状：有没有真代码、有没有跑（walk=.locked）、有没有要钱、有没有删原文。

    .venv/bin/python scripts/probe_run.py <chat_id> <N> <tag>     # 结果一行一次，正文落到 /tmp/r-<tag>-<i>.txt

每次先 POST /api/chats/{id}/reset（新话题），再往那个对话发同一句；只认那个 chat 里此后第一条 assistant 正文。
"""
import json, sys, asyncio, time, urllib.request, urllib.parse, http.cookiejar, re, sqlite3, websockets
