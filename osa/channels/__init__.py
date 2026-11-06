"""聊天软件接入：在 Telegram、飞书、钉钉、企业微信、Discord 里和 Bot 对话。

- 一个连接 = 聊天软件里的一个机器人账号（Telegram 的 bot token、飞书和钉钉的自建应用、企业微信的智能机器人、
  Discord 的应用），绑定这边的一个对话
  （某个 Bot 的私聊或一个群聊）。在聊天软件里说的话和网页上是同一个对话，记录两边都看得到。
- 只和配对过的那个人说话：添加后生成 6 位配对码（30 分钟内有效），在聊天软件里发给机器人，这个私聊就成了“主人”；
  之后别人发来的消息一律不理。配对码输错 10 次作废。
- 进：文字走和网页一样的入口（handle）；文件和图片存到电脑的 uploads 目录，消息里带上路径；/new、/stop、/help 是命令。
  “允许 #12”“拒绝 #12”这样的话等于点卡片上的按钮（钉钉的卡片没有回调按钮，靠它）。
- 出：监听界面事件（on_event）。Bot 的回复、任务结果、取消、交接发到聊天软件；确认和“请你帮忙”变成带按钮的卡片，
  点按钮就处理确认；不管在哪边处理的，卡片都会更新成结果（改不了卡片的平台发一条结果）。所有发送按顺序排队（outbox），不会乱序。
- 密钥存在保险库（channel_<id>），表里只记名字和不敏感的配置。
- 收消息用长轮询（Telegram）和长连接（其余几家），不需要公网地址。同一个机器人账号只能有一处在收消息。
"""

from ..i18n import s as _s, task_dispatch_goal, task_result_body
import asyncio
import json
import re
import secrets
import time
from .. import approvals, bots, memory, vault
from . import fmt

conn = memory.conn
conn.execute("""create table if not exists channels(
  id integer primary key, kind text, name text default '', config text default '{}', chat_id integer,
  peer text default '', peer_name text default '', pair_code text default '', pair_expires real default 0,
  pair_fails integer default 0, enabled integer default 1, created real)""")
conn.commit()

PAIR_TTL = 30 * 60
PAIR_MAX_FAILS = 10
HELP = _s('audit_d3f2e2e0d3')

# 由 server 设置
handle = None      # async (chat, text, via) -> None：和网页发消息走同一个入口
reset = None       # async (chat_id) -> None：新话题
handback = None    # async (bot_id) -> None：交还电脑（“请你帮忙”处理完了）
notify = None      # async (event) -> None

RUNNING: dict[int, "Channel"] = {}
_COLS = "id, kind, name, config, chat_id, peer, peer_name, pair_code, pair_expires, pair_fails, enabled, created"


# ---------- 存储 ----------
def _row(r) -> dict:
    keys = [k.strip() for k in _COLS.split(",")]
    d = dict(zip(keys, r))
    d["config"] = json.loads(d["config"] or "{}")
    return d


def rows() -> list[dict]:
    return [_row(r) for r in conn.execute(f"select {_COLS} from channels order by id")]


def row(cid: int) -> dict | None:
    r = conn.execute(f"select {_COLS} from channels where id=?", (cid,)).fetchone()
    return _row(r) if r else None


def secret_name(cid: int) -> str:
    return f"channel_{cid}"


def public_url() -> str:
    """网页的地址，用来把消息里的 /library/pages/3 这类链接补全。"""
    r = conn.execute("select value from settings where key='public_url'").fetchone()
    return r[0] if r else ""


def set_public_url(url: str):
    url = (url or "").strip().rstrip("/")
    if url and not re.fullmatch(r"https?://[^\s/]+(/[^\s]*)?", url):
        raise ValueError(_s('audit_c1c03f9e8c'))
    conn.execute("insert or replace into settings values('public_url', ?)", (url,))
    conn.commit()


def public(r: dict) -> dict:
    ch = RUNNING.get(r["id"])
    cls = PLATFORMS[r["kind"]]
    out = {"id": r["id"], "kind": r["kind"], "title": cls.title, "name": r["name"], "chat_id": r["chat_id"],
           "enabled": bool(r["enabled"]), "state": (ch.state if ch else "connecting") if r["enabled"] else "off",
           "error": ch.error if ch and r["enabled"] else "", "paired": bool(r["peer"]), "peer_name": r["peer_name"],
           "created": r["created"]}
    if not r["peer"]:
        ok = bool(r["pair_code"]) and r["pair_expires"] > time.time() and r["pair_fails"] < PAIR_MAX_FAILS
        out |= {"pair_code": r["pair_code"] if ok else "", "pair_expires": r["pair_expires"] if ok else 0,
                "pair_link": cls.pair_link(r) if ok else "", "setup_link": cls.setup_link(r) if ok else ""}
    return out


def list_public() -> list[dict]:
    return [public(r) for r in rows()]


def changed():
    if notify:
        asyncio.create_task(notify({"type": "channels_changed"}))


def _refresh(cid: int):
    if (ch := RUNNING.get(cid)) and (r := row(cid)):
        ch.row = r


# ---------- 增删改 ----------
async def create(kind: str, fields: dict, chat_id: int) -> dict:
    cls = PLATFORMS.get(kind)
    if not cls:
        raise ValueError(_s('audit_5edbda34c8', v0=kind))
    if not bots.chat(chat_id):
        raise ValueError(_s('audit_f922a43cce'))
    info = await cls.check(fields)
    for r in rows():
        if r["kind"] == kind and cls.same(r, info):
            raise ValueError(_s('audit_a8cc42fa01', v0=r['name']))
    cur = conn.execute("insert into channels(kind, name, config, chat_id, created) values(?,?,?,?,?)",
                       (kind, info["name"], json.dumps(info["config"], ensure_ascii=False), chat_id, time.time()))
    conn.commit()
    cid = cur.lastrowid
    vault.put(secret_name(cid), info["secret"])
    new_pair_code(cid)
    _launch(row(cid))
    changed()
    return public(row(cid))


def new_pair_code(cid: int):
    """重新配对：清掉原来的主人，生成新的配对码。"""
    code = f"{secrets.randbelow(10 ** 6):06d}"
    conn.execute("update channels set peer='', peer_name='', pair_code=?, pair_expires=?, pair_fails=0 where id=?",
                 (code, time.time() + PAIR_TTL, cid))
    conn.commit()
    _refresh(cid)


async def update(cid: int, data: dict) -> dict:
    r = row(cid)
    if not r:
        raise ValueError(_s('audit_3fa01e3844'))
    if "chat_id" in data:
        if not bots.chat(int(data["chat_id"])):
            raise ValueError(_s('audit_f922a43cce'))
        conn.execute("update channels set chat_id=? where id=?", (int(data["chat_id"]), cid))
    if "enabled" in data:
        conn.execute("update channels set enabled=? where id=?", (int(bool(data["enabled"])), cid))
    conn.commit()
    r = row(cid)
    if "enabled" in data:
        if r["enabled"]:
            _launch(r)
        else:
            _stop_one(cid)
    _refresh(cid)
    if "chat_id" in data and (ch := RUNNING.get(cid)) and r["peer"]:
        ch.say(_s('audit_752153f9cd', v0=_chat_title(r['chat_id'])))
    changed()
    return public(r)


def delete(cid: int):
    _stop_one(cid)
    vault.delete(secret_name(cid))
    conn.execute("delete from channels where id=?", (cid,))
    conn.commit()
    changed()


def chat_removed(chat_id: int):
    """绑定的 Bot 或群聊被删了：改成和主 Bot 对话。"""
    to = bots.primary()["chat_id"]
    for r in rows():
        if r["chat_id"] == chat_id:
            conn.execute("update channels set chat_id=? where id=?", (to, r["id"]))
            conn.commit()
            _refresh(r["id"])
            if (ch := RUNNING.get(r["id"])) and r["peer"]:
                ch.say(_s('audit_ee5b6f29e2', v0=_chat_title(to)))
    changed()


# ---------- 启停 ----------
def _launch(r: dict):
    _stop_one(r["id"])
    ch = PLATFORMS[r["kind"]](r, vault.get(secret_name(r["id"])) or "")
    RUNNING[r["id"]] = ch
    ch.launch()


def _stop_one(cid: int) -> "Channel | None":
    if ch := RUNNING.pop(cid, None):
        ch.close()
    return ch


async def start():
    for r in rows():
        if r["enabled"]:
            _launch(r)


async def stop():
    for cid in list(RUNNING):
        if ch := _stop_one(cid):
            await ch.closer


# ---------- 界面事件 → 聊天软件 ----------
def on_event(event: dict):
    """server.broadcast 每个事件都会调用这里；只排队，不在这里等网络。"""
    for ch in list(RUNNING.values()):
        try:
            ch.consider(event)
        except Exception as e:
            print(_s('audit_708657b9bd', v0=ch.id, v1=e), flush=True)


def _bot_name(bot_id) -> str:
    b = bots.get(bot_id) if bot_id else None
    return b["name"] if b else "Bot"


def _chat_title(chat_id) -> str:
    c = bots.chat(chat_id) if chat_id else None
    return (c["title"] if c else "") or _s('audit_254ec753e7')


def _duration(s) -> str:
    s = int(s or 0)
    return _s('audit_0cc05a38ad', v0=s) if s < 60 else _s('audit_2a94e5c93f', v0=s // 60, v1=s % 60) if s < 3600 else _s('audit_f7c13500d5', v0=s // 3600, v1=s % 3600 // 60)


def _absolute(md: str) -> str:
    """把站内链接补成完整地址，聊天软件里才点得开。"""
    base = public_url()
    if not base:
        return md
    md = re.sub(r"\]\((/(?!/)[^)\s]*)\)", lambda m: f"]({base}{m[1]})", md)
    return re.sub(r"(?<![\w\]\(/.:])(/(?:library/pages|s)/[\w-]+)", lambda m: base + m[1], md)


def render(m: dict, group: bool) -> str | None:
    """一条界面消息在聊天软件里怎么说；不用发的返回 None。用户自己的消息不回显。"""
    meta, role = m.get("meta") or {}, m.get("role")
    content = (m.get("content") or "").strip()
    name = _bot_name(m.get("bot_id"))
    if role == "assistant":
        return (f"**{name}**\n" if group else "") + content if content else None
    if role != "task":
        return None
    kind = meta.get("kind")
    if kind == "result":
        tid, status = meta.get("task_id"), meta.get("status")
        body = task_result_body(content)
        d = conn.execute("select content from messages where id=?", (tid,)).fetchone()
        routine = re.match(r"\[(?:定时任务|Lịch|Routine) ([^\]]+)\]", task_dispatch_goal(d[0])) if d else None
        what = _s('audit_a36df7ed52', v0=routine[1]) if routine else _s('audit_2196019947', v0=tid)
        head = _s('audit_2c32b91e31', v0=what) if status == "done" else _s('audit_3d849b225e', v0=what) if status == "failed" else _s('audit_aa1ff6eb0f', v0=what)
        if meta.get("elapsed"):
            head += _s('audit_a70a462981', v0=_duration(meta['elapsed']))
        return f"**{head}**" + (f" · {name}" if group else "") + f"\n\n{body}"
    if kind == "cancel":
        return "⏹ " + content.strip("[]")
    if kind == "handoff":
        return f"{name} → {_bot_name(meta.get('to'))}：{meta.get('note') or content}"
    if kind == "dm":
        return _s('audit_2ca49acc44', v0=name, v1=_bot_name(meta.get('to')), v2=content)
    if kind == "dm_reply":
        return None if meta.get("sent") else _s('audit_0a30d79caa', v0=name, v1=content)
    if kind == "note":
        return "ℹ️ " + content.strip("[]")
    return None


def card_for(ev: dict) -> dict:
    """确认请求 → 卡片（各平台自己画按钮）。"""
    who = _bot_name(ev.get("bot_id"))
    origin = ""
    if ev.get("origin_chat_id") and ev["origin_chat_id"] != ev.get("chat_id"):
        origin = _s('audit_e9369cc865', v0=_chat_title(ev['origin_chat_id']))
    url = public_url()
    if ev.get("kind") == "help":
        try:
            reason = (lambda a: a.get("reason") or a.get("需要你做的事"))(json.loads(ev.get("args") or "{}")) or ev.get("args")
        except ValueError:
            reason = ev.get("args")
        return {"id": ev["id"], "kind": "help", "title": _s('audit_c7383835da', v0=who),
                "body": _s('audit_86f2f421a1', v0=reason, v1=ev.get('task_id'), v2=origin),
                "buttons": [(_s('audit_4b148c5a9e'), "done", "primary"), (_s('audit_3e14941fa3'), "fail", "")],
                "link": (_s('audit_6bc71fac88'), f"{url}/?chat={ev.get('chat_id')}") if url else None, "done": ""}
    tool, args = ev.get("tool") or "", (ev.get("args") or "")[:800]
    goal = re.sub(r"\s+", " ", ev.get("goal") or "")
    when = ""
    if ev.get("expires"):
        when = _s('audit_8844f535fa', v0=time.strftime('%H:%M', time.localtime(ev['expires'])))
    buttons = [(_s('audit_0273f6d38d'), "ok", "primary"), (_s('audit_03e210a66d'), "no", "danger")]
    if tool == "ask_approval":   # Worker 自己要求确认的一步：直接写要做的事；“总是允许”对它没有意义
        try:
            what = (lambda a: a.get("action") or a.get("操作"))(json.loads(args)) or args
        except ValueError:
            what = args
        body = _s('audit_18baf282ea', v0=what, v1=ev.get('task_id'), v2=goal, v3=origin, v4=when)
    else:
        app, _, name = tool.rpartition("__")
        body = _s('audit_9e193a0913', v0=_s('audit_802e64482e') + app + _s('audit_246cfa4efb') if app else '', v1=name, v2=ev.get('task_id'), v3=goal, v4=origin, v5=when, v6=args)
        buttons.append((_s('audit_a0f2085856'), "always", ""))
    return {"id": ev["id"], "kind": "approval", "title": _s('audit_134ee617ba', v0=who), "body": body,
            "buttons": buttons, "link": None, "done": ""}


# 打字代替按按钮：“允许 #12”“拒绝 12”。钉钉卡片上的链接点一下就发出这样一句话
WORDS = {"允许一次": "ok", "允许": "ok", "同意": "ok", "拒绝": "no", "总是允许": "always", "处理完了": "done", "处理不了": "fail"}
ACT_WORD = {"ok": "channel_allow", "no": "channel_deny", "always": "channel_always", "done": "channel_done", "fail": "channel_fail"}
# Keep Chinese commands for compatibility; accept Vietnamese and English too.
WORDS.update({"Cho phép": "ok", "Từ chối": "no", "Luôn cho phép": "always", "Đã xử lý": "done", "Không xử lý được": "fail",
              "Allow": "ok", "Deny": "no", "Always allow": "always", "Done": "done", "Cannot complete": "fail"})
_WORD_CMD = re.compile(r"^(" + "|".join(sorted(WORDS, key=len, reverse=True)) + r")\s*[#＃]?\s*(\d+)\s*[。.!！]?$", re.IGNORECASE)


def word_command(act: str, aid: int) -> str:
    """点了等于按按钮的那句话。"""
    return f"{_s(ACT_WORD[act])} #{aid}"


DONE_TEXT = {"approval": {"approved": "channel_approved", "always": "channel_always_approved", "rejected": "channel_rejected", "expired": "channel_expired_denied", "cancelled": "channel_cancelled"},
             "help": {"approved": "channel_help_done", "rejected": "channel_help_fail", "expired": "channel_expired", "cancelled": "channel_cancelled"}}


class Channel:
    """一个聊天软件连接。平台子类实现：check / same / pair_link / run / send_text / send_card / edit_card，
    可选 typing（每 4 秒调一次）和 download（取附件）。"""
    kind = ""
    title = ""
    max_len = 4000

    def __init__(self, r: dict, secret: str):
        self.row, self.id, self.secret = r, r["id"], secret
        self.state, self.error = "connecting", ""
        self.outbox: asyncio.Queue = asyncio.Queue()
        self.cards: dict[int, tuple[str, dict]] = {}   # 确认请求 id -> (聊天软件里的消息 id, 卡片)
        self.carding: set[int] = set()                  # 已经排队要发卡片的确认请求
        self.jobs: list[asyncio.Task] = []
        self.typer: asyncio.Task | None = None

    # ----- 平台要实现的 -----
    @classmethod
    async def check(cls, fields: dict) -> dict:
        """验证凭据，返回 {"name", "config", "secret"}；不对就抛 ValueError（写给用户看的话）。"""
        raise NotImplementedError

    @classmethod
    def same(cls, r: dict, info: dict) -> bool:
        raise NotImplementedError

    @staticmethod
    def pair_link(r: dict) -> str:
        return ""

    @staticmethod
    def setup_link(r: dict) -> str:
        """配对前要先打开的链接（比如把 Discord 机器人邀请到服务器），没有就是空。"""
        return ""

    async def run(self):
        raise NotImplementedError

    async def send_text(self, peer: str, md: str):
        raise NotImplementedError

    async def send_card(self, peer: str, card: dict) -> str:
        raise NotImplementedError

    async def edit_card(self, peer: str, msg_id: str, card: dict):
        raise NotImplementedError

    async def typing(self, peer: str):
        pass

    async def download(self, ref) -> bytes | tuple[bytes, str]:
        """取附件；文件名要下载了才知道的平台返回 (内容, 文件名)。"""
        raise ValueError(_s('audit_232804cc18'))

    async def aclose(self):
        pass

    # ----- 生命周期 -----
    def launch(self):
        self.jobs = [asyncio.create_task(self._guard()), asyncio.create_task(self._sender())]

    def close(self):
        """停下收发，HTTP 客户端放到后台关（服务关闭时 stop() 会等它关完）。"""
        for t in self.jobs + [self.typer]:
            if t:
                t.cancel()
        self.closer = asyncio.create_task(self.aclose())

    async def _guard(self):
        try:
            await self.run()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.set_state("error", _s('audit_ece311e00a', v0=e))

    def set_state(self, state: str, error: str = ""):
        if (state, error) != (self.state, self.error):
            self.state, self.error = state, error
            changed()

    async def _sender(self):
        while True:
            job = await self.outbox.get()
            try:
                await job()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(_s('audit_4f103cf2d4', v0=self.id, v1=self.kind, v2=e), flush=True)

    def queue(self, job):
        self.outbox.put_nowait(job)

    @staticmethod
    async def _safe(coro):
        try:
            await coro
        except Exception as e:
            print(_s('audit_9b63239bcf', v0=e), flush=True)

    # ----- 发出去 -----
    def say(self, md: str, peer: str | None = None):
        peer = peer or self.row["peer"]
        if peer and md.strip():
            self.queue(lambda: self._send_md(peer, md))

    async def _send_md(self, peer: str, md: str):
        for part in fmt.split(_absolute(md), self.max_len):
            await self.send_text(peer, part)

    async def _send_card(self, peer: str, card: dict):
        card = card | {"body": _absolute(card["body"])}
        self.cards[card["id"]] = (await self.send_card(peer, card), card)

    async def _finish_card(self, peer: str, aid: int, status: str):
        """确认请求处理完了（在哪边处理的都一样）：卡片去掉按钮，写上结果。"""
        hit = self.cards.pop(aid, None)
        self.carding.discard(aid)
        if not hit:
            return
        msg_id, card = hit
        done = _s(DONE_TEXT[card["kind"]].get(status, status))
        await self.edit_card(peer, msg_id, card | {"buttons": [], "link": None, "done": done})

    def consider(self, ev: dict):
        r = self.row
        peer = r["peer"]
        if not peer:
            return
        t, cid = ev.get("type"), ev.get("chat_id")
        mine = cid == r["chat_id"]
        if t == "message" and mine:
            chat = bots.chat(cid)
            md = render(ev.get("message") or {}, bool(chat and chat["kind"] == "group"))
            if md:
                self.say(md)
        elif t == "approval":
            aid, status = ev.get("id"), ev.get("status")
            if status == "pending" and (mine or ev.get("origin_chat_id") == r["chat_id"]):
                self.carding.add(aid)
                card = card_for(ev)
                self.queue(lambda: self._send_card(peer, card))
            elif status != "pending" and aid in self.carding:
                status = "always" if ev.get("always") else status
                self.queue(lambda: self._finish_card(peer, aid, status))
        elif t == "stream_start" and mine:
            self.start_typing()
        elif t == "stream_end" and mine:
            self.stop_typing()
        elif t == "error" and mine:
            self.say(f"⚠️ {ev.get('message')}")

    def start_typing(self):
        if not self.typer or self.typer.done():
            self.typer = asyncio.create_task(self._typing_loop(self.row["peer"]))

    def stop_typing(self):
        if self.typer:
            self.typer.cancel()
            self.typer = None

    async def _typing_loop(self, peer: str):
        try:
            for _ in range(45):   # 最多 3 分钟
                await self.typing(peer)
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    # ----- 收进来 -----
    async def inbound(self, peer: str, who: str, text: str, files: list = (), ref=None):
        """收到一条私聊消息。files：[(文件名, 平台取文件用的引用)]。"""
        r = row(self.id)
        if not r:
            return
        self.row = r
        text = (text or "").strip()
        if not r["peer"]:
            return await self._pair(peer, who, text)
        if peer != r["peer"]:
            return   # 不是配对过的人：不理
        cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        if cmd in ("/start", "/help"):
            return self.say(_s("audit_d3f2e2e0d3", name=_chat_title(r["chat_id"])))
        if cmd == "/new":
            await reset(r["chat_id"])
            return self.say(_s('audit_852b6b32a5'))
        if (m := _WORD_CMD.match(text)) and int(m[2]) in self.carding:
            ok, toast = await self._press(peer, f"ap:{m[2]}:{next(v for k, v in WORDS.items() if k.casefold() == m[1].casefold())}")
            if not ok:   # 成功的话卡片会更新成结果，不用再说一遍
                self.say(toast)
            return
        if cmd == "/stop":
            from .. import router
            done = [router.cancel(t.id, _s('audit_aa4e5d0b17')) for t in list(router.TASKS.values())
                    if t.chat_id == r["chat_id"] and t.status == "running"]
            return self.say(_s('audit_1bb05a5467') + "、".join(done) if done else _s('audit_f2cd45a1a5'))
        chat = bots.chat(r["chat_id"])
        if not chat:
            return self.say(_s('audit_d0c4231eb7'))
        paths = []
        for name, fref in files:
            try:
                got = await self.download(fref)
                data, name = (got[0], got[1] or name) if isinstance(got, tuple) else (got, name)
                paths.append(await save_upload(name, data))
            except Exception as e:
                self.say(_s('audit_f155f7c867', v0=name, v1=e))
        if paths:
            text = (text + "\n" if text else "") + "\n".join(_s('audit_361c2abf55', v0=p) for p in paths)
        if text:
            await handle(chat, text, self.kind)

    async def _pair(self, peer: str, who: str, text: str):
        r = self.row
        code = re.search(r"(?<!\d)(\d{6})(?!\d)", text)
        valid = bool(r["pair_code"]) and r["pair_expires"] > time.time() and r["pair_fails"] < PAIR_MAX_FAILS
        if valid and code and secrets.compare_digest(code[1], r["pair_code"]):
            conn.execute("update channels set peer=?, peer_name=?, pair_code='', pair_fails=0 where id=?",
                         (peer, who[:80], self.id))
            conn.commit()
            self.row = row(self.id)
            changed()
            return self.say(_s('audit_698b5473b6') + _s("audit_d3f2e2e0d3", name=_chat_title(r["chat_id"])), peer)
        if code and valid:
            conn.execute("update channels set pair_fails=pair_fails+1 where id=?", (self.id,))
            conn.commit()
            self.row = row(self.id)
            if self.row["pair_fails"] >= PAIR_MAX_FAILS:
                changed()
            return self.say(_s('audit_a0c0570c0c'), peer)
        self.say(_s('audit_8ff7612931'), peer)

    async def press(self, peer: str, data: str) -> str:
        """卡片上的按钮被点了。返回给用户的一句提示。"""
        return (await self._press(peer, data))[1]

    async def _press(self, peer: str, data: str) -> tuple[bool, str]:
        """(处理了没有, 提示)。"""
        if not peer or peer != self.row["peer"]:
            return False, _s('audit_69425e7491')
        m = re.fullmatch(r"ap:(\d+):(\w+)", data or "")
        if not m or int(m[1]) not in self.carding:
            return False, _s('audit_a0fc2ee7b4')
        aid, act = int(m[1]), m[2]
        item = approvals.pending.get(aid)
        if not item:
            return False, _s('audit_2dcc0d57d8')
        if act not in ACT_WORD:
            return False, _s('audit_a0fc2ee7b4')
        kind = item.get("kind")
        if act in ("done", "fail") and kind != "help" or act in ("ok", "no", "always") and kind == "help":
            return False, _s('audit_1794d47c72')
        if act == "done":
            await handback(item["bot_id"])
            return True, _s('audit_12cc2f67dc')
        if act == "fail":
            approvals.resolve(aid, False, _s('audit_18bceb2b8a'))
            return True, _s('audit_90f7dc7301')
        return True, approvals.resolve(aid, act in ("ok", "always"), "", act == "always")


async def save_upload(name: str, data: bytes) -> str:
    """聊天软件发来的文件存到电脑的 uploads 目录（和网页上传附件一样）。"""
    from .. import computer, library
    c = computer.get()
    if (await c.status())["state"] != "running":
        await c.start()
    name = re.sub(r"[/\\\0]", "_", name).strip() or "file"
    return (await library.put_file(c, library.WORKSPACE + "/uploads", name[:200], data))["path"]


from .telegram import Telegram   # noqa: E402  平台实现要用到上面的 Channel
from .feishu import Feishu        # noqa: E402
from .dingtalk import DingTalk    # noqa: E402
from .wecom import WeCom          # noqa: E402
from .discord import Discord      # noqa: E402

PLATFORMS: dict[str, type[Channel]] = {"telegram": Telegram, "feishu": Feishu, "dingtalk": DingTalk, "wecom": WeCom,
                                       "discord": Discord}
