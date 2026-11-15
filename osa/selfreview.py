"""Tự duyệt (C54): định kỳ đọc dấu vết refusal của chính mình rồi viết lại bài học.

Không có vòng này thì C53 chỉ là "tình cờ gặp refusal trong lúc rảnh": một dấu vết nằm đó
cho tới khi bị dọn, không ai đọc. Ở đây Bot tự đọc, tự rút ra hình dạng phải giao, và ghi
vào chính instructions của mình bằng dòng ngắn (khối có hạn, xem freedom.LESSONS_MAX).

Chỉ chạy khi đáng chạy: có ít nhất MIN_NEW dấu vết mới kể từ lần duyệt trước, và cách lần
trước đủ lâu. Mỗi Bot duyệt riêng, nên một Bot hỏng không kéo cả hàng.
"""
import asyncio
import logging
import re
import time

from . import freedom, traces
from .config import CFG
from .memory import conn
from .providers import brief, client, create_chat

log = logging.getLogger(__name__)

INTERVAL = 6 * 3600      # 两次 duyệt cách nhau ít nhất chừng này
MIN_NEW = 3              # 至少这么多新痕迹才值得一次模型调用

PROMPT = ("Dưới đây là các lượt gần đây bị model từ chối trong việc của mày. Viết lại thành bài học ngắn: "
          "mỗi hình dạng việc lấy MỘT dòng `- <khoá>: <làm thẳng thế nào, mở đầu bằng gì>`, tối đa 6 dòng, "
          "khoá 1-4 chữ có dấu, không giải thích, không chào. Chỉ viết dòng bài học.\n\n{spots}")

conn.execute("create table if not exists review_state(bot_id integer primary key, last real not null default 0, seen integer not null default 0)")


def _state(bot_id: int) -> tuple[float, int]:
    r = conn.execute("select last, seen from review_state where bot_id=?", (bot_id,)).fetchone()
    return (r[0], r[1]) if r else (0.0, 0)


def due(bot_id: int, now: float | None = None) -> bool:
    """现在该不该给这个 Bot 跑一次：够新、够久、而且真有新痕迹。"""
    last, seen = _state(bot_id)
    now = now or time.time()
    if now - last < INTERVAL:
        return False
    total = conn.execute("select count(*) from traces where bot_id=?", (bot_id,)).fetchone()[0]
    return total >= MIN_NEW and total > seen


def parse(text: str) -> list[tuple[str, str]]:
    """模型那段 -> [(khoá, dòng)]; 只收 dạng `- khoá: …`, khoá ngắn, bỏ trùng."""
    out, seen = [], set()
    for raw in (text or "").splitlines():
        line = raw.strip().lstrip("-•* ").strip()
        key, sep, body = line.partition(":")
        key, body = key.strip().lower(), body.strip()
        if not sep or not body or not key or len(key) > 40 or key in seen:
            continue
        if re.fullmatch(r"[\w .+/-]{1,40}", key, re.UNICODE) is None:
            continue
        seen.add(key)
        out.append((key, f"- {key}: {body[:160]}"))
    return out[:6]


async def review(bot: dict) -> list[str]:
    """Một lượt tự duyệt. Trả về những dòng đã ghi (rỗng nếu không có gì/ không gọi được)."""
    spots = traces.summary(bot["id"], limit=14)
    if spots and len(spots.splitlines()) < MIN_NEW:
        return []
    fb = freedom.fallback()
    if not fb:
        return []
    prov, model, kw = fb
    body = [{"role": "system", "content": freedom.MINIMAL},
            {"role": "user", "content": PROMPT.format(spots=spots)}]
    out = ""
    try:
        stream = await create_chat(client(prov), model=model, messages=body, stream=True, **kw)
        async for chunk in stream:
            if chunk.choices and (d := chunk.choices[0].delta) is not None and getattr(d, "content", None):
                out += d.content
    except Exception as e:  # noqa: BLE001 - duyệt không được thì thôi, dấu vết vẫn còn đó
        log.warning("self review for bot %s failed (%s)", bot["id"], brief(e))
        return []
    lines = parse(out)
    for key, line in lines:
        freedom.write_lesson(bot, line, key)
        log.info("bot %s learned: %s", bot["id"], line[:120])
    return [line for _, line in lines]


def mark(bot_id: int) -> None:
    """Ghi nhận đã duyệt: mốc thời gian và số dấu vết đã thấy."""
    total = conn.execute("select count(*) from traces where bot_id=?", (bot_id,)).fetchone()[0]
    conn.execute("insert or replace into review_state(bot_id, last, seen) values(?,?,?)", (bot_id, time.time(), total))
    conn.commit()


async def sweep() -> list[str]:
    """Một vòng: mỗi Bot tới hạn thì duyệt một lần. Trả về toàn bộ dòng đã ghi."""
    if not freedom.on():
        return []
    from . import bots
    wrote: list[str] = []
    for b in bots.list_bots():
        if not due(b["id"]):
            continue
        try:
            wrote += await review(b)
        finally:
            mark(b["id"])      # duyệt hỏng cũng đánh dấu: không gọi lại cùng một chỗ mỗi vòng
    return wrote


async def loop() -> None:
    """Chạy mãi: chờ INTERVAL rồi quét một lần (lần đầu quét sớm, một phút sau khi bật)."""
    n = CFG.get("self_review")
    if n is False:
        return
    await asyncio.sleep(60)
    while True:
        try:
            if got := await sweep():
                log.info("self review wrote %s lesson(s)", len(got))
        except Exception:
            log.exception("self review sweep failed")
        await asyncio.sleep(INTERVAL)
