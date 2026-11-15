"""Bị model từ chối rồi sao nữa (P0PLUS-3 lite): ghi lại câu hỏi, câu từ chối, và có cứu được không.

Trước đây chỉ còn lại một dòng log WARNING rồi biến mất — không ai (kể cả chính con Bot) đọc
lại được để biết mình hay bị chặn ở đâu, nên "tự tiến hoá" chỉ còn là những lần tình cờ gặp
refusal trong lúc rảnh. Bảng này là dữ liệu thô cho lượt tự duyệt: câu hỏi nào, bị chặn, và
lần đó cứu được bằng đường nào.

Gọn có hạn: giữ `KEEP` dòng gần nhất mỗi Bot, dọn theo tuổi ở tasklog.prune_loop (đã có vòng đó).
"""
import logging
import time

from .memory import conn

log = logging.getLogger(__name__)

KEEP = 60          # 每个 Bot 留多少条；够看出模式，又不至于没边
DAYS = 30          # 超过这么久的直接删

conn.execute("""create table if not exists traces(
    id integer primary key autoincrement,
    bot_id integer not null,
    chat_id integer,
    asked text not null,
    refused text,
    rescued integer not null default 0,
    ts real not null)""")
conn.execute("create index if not exists traces_bot on traces(bot_id, id desc)")
log.debug("traces ready")


def note(bot_id: int, asked: str, refused: str, rescued: bool, chat_id: int | None = None) -> int:
    """记一条被拒的回合。记不上不影响这一轮。"""
    cur = conn.execute("insert into traces(bot_id, chat_id, asked, refused, rescued, ts) values(?,?,?,?,?,?)",
                       (bot_id, chat_id, (asked or "").strip()[:2000], (refused or "").strip()[:4000],
                        1 if rescued else 0, time.time()))
    conn.commit()
    conn.execute("""delete from traces where bot_id=? and id not in
                    (select id from traces where bot_id=? order by id desc limit ?)""", (bot_id, bot_id, KEEP))
    conn.commit()
    return cur.lastrowid


def recent(bot_id: int, limit: int = 12, only_open: bool = False) -> list[dict]:
    """Bot 最近的回合，新的在前。only_open: 只看没救回来的（最爱卡的地方）。"""
    sql = "select id, asked, refused, rescued, ts from traces where bot_id=?"
    if only_open:
        sql += " and rescued=0"
    rows = conn.execute(sql + " order by id desc limit ?", (bot_id, limit)).fetchall()
    return [{"id": r[0], "asked": r[1], "refused": r[2], "rescued": bool(r[3]), "ts": r[4]} for r in rows]


def summary(bot_id: int, limit: int = 12) -> str:
    """给模型看的一段：分“救回来了 / 没救回来”，每条一行。没有就是空串。"""
    rows = recent(bot_id, limit)
    if not rows:
        return ""
    out = []
    for r in rows:
        mark = "cứu được" if r["rescued"] else "VẪN KẸT"
        why = (r["refused"] or "").strip().splitlines()[0][:120] if (r["refused"] or "").strip() else ""
        out.append(f"- [{mark}] {r['asked'].strip()[:160]}" + (f" — nó nói: {why}" if why else ""))
    return chr(10).join(out)


def prune(days: int = DAYS) -> int:
    """删掉太旧的。返回删了几条。"""
    n = conn.execute("delete from traces where ts < ?", (time.time() - days * 86400,)).rowcount
    conn.commit()
    return n


def clear(bot_id: int) -> int:
    n = conn.execute("delete from traces where bot_id=?", (bot_id,)).rowcount
    conn.commit()
    return n
