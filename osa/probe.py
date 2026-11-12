"""C38: 让一个 bot 去量另一个 bot —— 发一条私信，等它回，把原话拿回来。

训练循环（skill train-bot）要的是“同一句话，改前改后”的真实答复；这是那条通路。
"""
import asyncio
import time

from . import bots, dm, memory


async def probe(sender: int, chat_id: int, name: str, text: str, timeout_s: int = 60) -> str:
    """我（sender）在 chat_id 里问 name 一句，等它回信；返回它的原话。"""
    to = bots.by_name(name)
    if not to:
        return f"Not probed: no bot named {name}"
    if to["id"] == sender:
        return "Not probed: that is you; ask yourself in a different way"
    text = (text or "").strip()
    if not text:
        return "Not probed: the question is empty"
    mark = memory.conn.execute("select coalesce(max(id), 0) from messages where chat_id=?", (chat_id,)).fetchone()[0]
    await dm.send(sender, to, text, chat_id, None, 0)
    deadline = time.monotonic() + max(10, int(timeout_s))
    while time.monotonic() < deadline:
        await asyncio.sleep(1.5)
        row = memory.conn.execute(
            "select content from messages where chat_id=? and id>? and role='assistant' "
            "and meta like '%\"kind\": \"dm_reply\"%' order by id desc limit 1", (chat_id, mark)).fetchone()
        if row and (row[0] or "").strip():
            return row[0].strip()
    return (f"Probed {name} but no reply came back within {timeout_s}s; the reply will arrive in this chat when it does.")
