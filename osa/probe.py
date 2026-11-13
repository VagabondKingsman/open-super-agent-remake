"""C38: 让一个 bot 去量另一个 bot —— 发一条私信，等它回，把原话拿回来。

训练循环（skill train-bot）要的是“同一句话，改前改后”的真实答复；这是那条通路。

回信由 dm.answer 直接交给这里登记着的等待者（take），不再走普通的回信唤醒，所以：
- 拿回来的是它的原话，而不是“X replied (…), starts: …”那种包装过的一句 —— is_refusal 只认行首，包装会把拒绝挡在外面；
- 这一轮不会因为这次测量多出一轮付费的回复（以前回信一到又叫醒提问的 Bot 说一遍，用户看到两条）；
- 等不靠消息的 role：dm.answer 存的是 task 行（kind=dm_reply），不是 assistant，按 role='assistant' 永远等不到。

要量的就是提问者自己（自己训练自己）时，换一个 Bot 去问：它这一轮正拿着自己路由的锁，唤不动自己。
"""
import asyncio

from . import bots, dm

_waiting: dict[int, list[asyncio.Future]] = {}   # 回信的 Bot -> 等着的人，先问先得


def _register(bot_id: int) -> asyncio.Future:
    fut = asyncio.get_running_loop().create_future()
    _waiting.setdefault(bot_id, []).append(fut)
    return fut


def _drop(bot_id: int, fut: asyncio.Future) -> None:
    queue = _waiting.get(bot_id) or []
    if fut in queue:
        queue.remove(fut)
    if not queue:
        _waiting.pop(bot_id, None)


def take(bot_id: int, text: str) -> bool:
    """dm.answer 记下回信之后问一句：有人在等这个 Bot 的这一封吗？

    有就交出去并返回 True —— 那就不必再排一轮回复；没有返回 False，照旧排。"""
    queue = _waiting.get(bot_id)
    while queue:
        fut = queue.pop(0)
        if not fut.done():
            fut.set_result(text)
            if not queue:
                _waiting.pop(bot_id, None)
            return True
    _waiting.pop(bot_id, None)
    return False


def excerpt(text: str, limit: int = 280) -> str:
    """只回摘录：整段塞回路由器，模型会把它原样贴进答复（实测一次 60 秒、上千字符）。"""
    said = (text or "").strip()
    head = said[:limit].replace(chr(10), " ")
    return head + ("" if len(said) <= limit else f" …(+{len(said) - limit} chars)")


def _asker(to: dict, sender: int) -> int:
    """由谁去问。问的就是提问者自己时换一个 Bot：自己这一轮拿着锁，叫不动自己（见文件头）。"""
    if to["id"] != sender:
        return sender
    for b in bots.list_bots():
        if b["id"] != to["id"]:
            return b["id"]
    return sender


async def probe(sender: int, chat_id: int, name: str, text: str, timeout_s: int = 60,
                excerpted: bool = True) -> str:
    """我（sender）在 chat_id 里问 name 一句，等它回信；返回它的原话（excerpted=True 时是摘录）。"""
    to = bots.by_name(name)
    if not to:
        return f"Not probed: no bot named {name}"
    text = (text or "").strip()
    if not text:
        return "Not probed: the question is empty"
    who = _asker(to, sender)
    fut = _register(to["id"])
    try:
        await dm.send(who, to, text, chat_id, None, 0)
        try:
            said = await asyncio.wait_for(fut, timeout=max(10, int(timeout_s)))
        except asyncio.TimeoutError:
            return (f"Probed {name} but no reply came back within {timeout_s}s; "
                    "the reply will arrive in this chat when it does.")
        return excerpt(said) if excerpted else said.strip()
    finally:
        _drop(to["id"], fut)
