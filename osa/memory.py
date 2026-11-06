"""会话记忆：SQLite 持久化。

Inline & Spill：最近 N 条消息直接放进上下文，更早的只留 ID + 摘要行；
Chain of Recall：模型可用 recall(id) 按需取回原文。
"""

from .i18n import s as _s, localize_task_goal
import json
import sqlite3
import time
from .config import CFG, ROOT

db_path = ROOT / CFG["memory"]["db"]
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.execute("""create table if not exists messages(
  id integer primary key, ts real, role text, content text, meta text)""")
conn.execute("""create table if not exists bots(
  id integer primary key, name text, avatar text, instructions text default '', is_primary integer default 0, created real)""")
conn.execute("""create table if not exists chats(
  id integer primary key, kind text, title text, bot_ids text, pinned integer default 0, updated real)""")
conn.execute("""create table if not exists settings(key text primary key, value text)""")
# v2 迁移：消息归属到对话
_cols = {r[1] for r in conn.execute("pragma table_info(messages)")}
if "chat_id" not in _cols:
    conn.execute("alter table messages add column chat_id integer")
    conn.execute("alter table messages add column bot_id integer")
conn.execute("create index if not exists messages_chat on messages(chat_id, id)")
conn.execute("""create table if not exists llm_usage(ts real, role text, model text, task_id integer,
  cache_hit integer, cache_miss integer, output integer, cost real)""")
conn.execute("create index if not exists llm_usage_task on llm_usage(task_id)")
# 后台任务的过程（每一步想了什么、调了什么工具、拿到什么），读写在 tasklog.py
conn.execute("""create table if not exists task_steps(
  id integer primary key, task_id integer, ts real, worker text default '', kind text, title text default '',
  body text default '', status text default 'done', dur real default 0, detail text default '')""")
conn.execute("create index if not exists task_steps_task on task_steps(task_id, id)")
conn.commit()


def add(role: str, content: str, chat_id: int, bot_id: int | None = None, **meta) -> int:
    now = time.time()
    cur = conn.execute("insert into messages(ts, role, content, meta, chat_id, bot_id) values(?,?,?,?,?,?)",
                       (now, role, content, json.dumps(meta, ensure_ascii=False), chat_id, bot_id))
    conn.execute("update chats set updated=? where id=?", (now, chat_id))
    conn.commit()
    return cur.lastrowid


def update_meta(msg_id: int, **fields):
    row = conn.execute("select meta from messages where id=?", (msg_id,)).fetchone()
    if row:
        meta = json.loads(row[0] or "{}") | fields
        conn.execute("update messages set meta=? where id=?", (json.dumps(meta, ensure_ascii=False), msg_id))
        conn.commit()


def page(chat_id: int, before: int | None = None, limit: int = 60) -> list[dict]:
    """前端翻页用：某个对话里 id < before 的最近 limit 条消息，按时间正序返回。"""
    rows = conn.execute("""select id, ts, role, content, meta, bot_id from messages
        where chat_id=? and id < ? order by id desc limit ?""", (chat_id, before or 1 << 62, limit)).fetchall()
    return [{"id": i, "ts": ts, "role": r, "content": c, "meta": json.loads(m or "{}"), "bot_id": b}
            for i, ts, r, c, m, b in reversed(rows)]


def recall(msg_id: int, chat_id: int) -> str:
    row = conn.execute("select role, content from messages where id=? and chat_id=?", (msg_id, chat_id)).fetchone()
    return f"[{row[0]}] {row[1]}" if row else _s('audit_272d30dee4', v0=msg_id)


def topic_start(chat_id: int) -> int:
    """最后一次“新话题”的消息 id；之前的消息不再带进上下文（长期记忆不受影响）。"""
    r = conn.execute("""select max(id) from messages where chat_id=? and role='task'
        and json_extract(meta, '$.kind')='reset'""", (chat_id,)).fetchone()
    return r[0] or 0


VIA = {"telegram": " Telegram", "feishu": _s('audit_a05c05ae01'), "dingtalk": _s('audit_32f35a70b3'), "wecom": _s('audit_c1983c6d12'), "discord": " Discord"}


def context(chat_id: int, viewer: int | None = None, me: int | None = None) -> list[dict]:
    """组装给 Router 的历史消息。viewer 是群聊里正在发言的 Bot：
    它自己的回复保持 assistant；别的 Bot 的发言、任务和交接都换成带名字的通知。私聊时 viewer 为空。
    me 是正在发言的 Bot（私聊也给），Bot 之间的私信按它的角度写成“谁私信了你 / 你回了谁”。"""
    n = CFG["memory"]["inline_messages"]
    rows = conn.execute("select id, role, content, meta, bot_id from messages where chat_id=? and id > ? order by id",
                        (chat_id, topic_start(chat_id))).fetchall()
    names = dict(conn.execute("select id, name from bots"))
    me = viewer if viewer is not None else me
    name = lambda b: names.get(b, _s('audit_ca59d8427a'))
    old, recent = rows[:-n], rows[-n:]
    msgs = []
    if old:
        def who(r, b):
            return name(b) if viewer is not None and r == "assistant" and b != viewer else r
        index = "\n".join(f"#{i} [{who(r, b)}] {c[:60].replace(chr(10), ' ')}" for i, r, c, _, b in old[-200:])
        msgs.append({"role": "system", "content": _s('audit_065c8e14cc') + index})
    for _, r, c, meta, b in recent:
        meta = json.loads(meta or "{}")
        others = viewer is not None and b != viewer
        if r == "task" and meta.get("kind") == "handoff" and viewer is not None:
            to = meta.get("to")
            if to == viewer:
                text = _s('audit_5c708e1a55', v0=name(b), v1=meta.get('note') or c)
            elif b == viewer:
                text = _s('audit_38de5df295', v0=name(to), v1=meta.get('note') or c)
            else:
                text = _s('audit_6188351719', v0=name(b), v1=name(to), v2=meta.get('note') or c)
            msgs.append({"role": "user", "content": text})
        elif r == "task" and meta.get("kind") in ("dm", "dm_reply"):
            msgs.append({"role": "user", "content": _dm_line(meta, c, b, me, name)})
        elif r == "task":  # 任务记录作为系统通知给 Router，避免它模仿这种格式
            whose = _s('audit_a329313b7c', v0=name(b)) if others and b else ""
            note = _s('audit_59cf2159cf', v0=whose) \
                if meta.get("kind") == "result" else _s('audit_6da8061d25', v0='；' + whose + _s('audit_3172b317f9') if whose else '')
            msgs.append({"role": "user", "content": note + c})
        elif r == "assistant" and others:
            msgs.append({"role": "user", "content": f"【{name(b)}】{c}"})
        elif r == "assistant" and "reasoning" in meta:
            # DeepSeek 思考模式：请求带工具时，历史回复的 reasoning_content 必须原样传回
            m = {"role": "assistant", "content": c}
            if meta["reasoning"] is not None:
                m["reasoning_content"] = meta["reasoning"]
            msgs.append(m)
        elif r == "assistant":
            # 旧记录没存思考内容，原样传回会被拒，改成通知形式
            msgs.append({"role": "user", "content": _s('audit_17283f795c', v0=c)})
        else:
            if meta.get("via"):   # 在聊天软件里发的：Router 据此不提网页上的按钮和面板
                c = _s('audit_dbd09cf563', v0=VIA.get(meta['via'], meta['via']), v1=c)
            if meta.get("skill_prompt"):   # /技能：把技能做法附在用户原话后面
                c = f"{c}\n\n{meta['skill_prompt']}"
            msgs.append({"role": "user", "content": c})
    return msgs


def _dm_line(meta: dict, c: str, sender: int | None, me: int | None, name) -> str:
    """Bot 之间的私信和回信（见 dm.py），按 me 的角度写。sender 是发信的 Bot，meta["to"] 是收信的。"""
    to = meta.get("to")
    if meta["kind"] == "dm":
        if to == me:
            return _s('audit_23e485b08a', v0=name(sender), v1=c)
        if sender == me:
            return _s('audit_c2d11efb0b', v0=name(to), v1=c)
        return _s('audit_1cec3d889b', v0=name(sender), v1=name(to), v2=c)
    if meta.get("sent"):   # 写回信的那一边留的记录，回信内容就是上面那条回复或任务结果
        return _s('audit_36e6727686', v0=_s('audit_5630b886f9') if sender == me else name(sender), v1=name(to))
    if meta.get("task_id") and meta.get("status") == "done":
        c = _s('audit_0fe7b6eff1', v0=meta['task_id'], v1=c)
    if to == me:
        return _s('audit_28d3946e44', v0=name(sender), v1=c)
    return _s('audit_d616e0b758', v0=name(sender), v1=name(to), v2=c)


def _is_peak(ts: float) -> bool:
    t = time.localtime(ts)  # 假定服务器在北京时间
    if t.tm_wday >= 5:
        return False
    hm = time.strftime("%H:%M", t)
    return any(a <= hm < b for a, b in (r.split("-") for r in CFG["pricing"]["peak_hours"]))


def record_usage(role: str, model: str, usage, task_id: int | None = None, provider: str | None = None):
    """记录一次模型调用的 token 和费用。usage 是 OpenAI 格式的 usage 对象；provider 不给就按角色的配置。"""
    if usage is None:
        return
    prompt = usage.prompt_tokens or 0
    hit = getattr(usage, "prompt_cache_hit_tokens", None)
    if hit is None:  # 非 DeepSeek 接口：尝试 OpenAI 的 cached_tokens 字段
        details = getattr(usage, "prompt_tokens_details", None)
        hit = getattr(details, "cached_tokens", 0) or 0
    miss, out = prompt - hit, usage.completion_tokens or 0
    now = time.time()
    from . import prices
    provider = provider or (CFG["roles"].get(role) or {}).get("provider")
    cost = prices.cost(provider, model, hit, miss, out, _is_peak(now))
    conn.execute("insert into llm_usage values(?,?,?,?,?,?,?,?)", (now, role, model, task_id, hit, miss, out, cost))
    conn.commit()


def tokens_today() -> int:
    return conn.execute("select coalesce(sum(cache_hit+cache_miss+output),0) from llm_usage where ts > ?",
                        (time.time() - 86400,)).fetchone()[0]


def usage_stats() -> dict:
    """费用面板用：今天、近 7 天、近 30 天的汇总，以及按角色、按任务、按天的拆分。"""
    now = time.time()
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))

    def total(since):
        r = conn.execute("""select coalesce(sum(cost),0), coalesce(sum(cache_hit),0), coalesce(sum(cache_miss),0),
            coalesce(sum(output),0), count(*) from llm_usage where ts >= ?""", (since,)).fetchone()
        return {"cost": round(r[0], 4), "cache_hit": r[1], "cache_miss": r[2], "output": r[3], "calls": r[4],
                "cache_rate": round(r[1] / (r[1] + r[2]), 3) if r[1] + r[2] else 0}

    by_role = conn.execute("""select role, model, sum(cost), sum(cache_hit+cache_miss+output) from llm_usage
        where ts >= ? group by role, model order by 3 desc""", (now - 30 * 86400,)).fetchall()
    by_task = conn.execute("""select u.task_id, sum(u.cost), sum(u.cache_hit+u.cache_miss+u.output), m.content
        from llm_usage u left join messages m on m.id = u.task_id where u.task_id is not null
        group by u.task_id order by u.task_id desc limit 20""").fetchall()
    by_day = conn.execute("""select date(ts, 'unixepoch', 'localtime') d, sum(cost) from llm_usage
        where ts >= ? group by d order by d""", (now - 30 * 86400,)).fetchall()
    return {
        "currency": CFG["pricing"]["currency"],
        "today": total(day0), "week": total(now - 7 * 86400), "month": total(now - 30 * 86400),
        "by_role": [{"role": r, "model": m, "cost": round(c, 4), "tokens": t} for r, m, c, t in by_role],
        "by_task": [{"id": i, "cost": round(c, 4), "tokens": t, "goal": localize_task_goal(g or "")[:60]}
                    for i, c, t, g in by_task],
        "by_day": [{"day": d, "cost": round(c, 4)} for d, c in by_day],
    }
