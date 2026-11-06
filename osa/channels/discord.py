"""Discord：Gateway 长连接收私信，不需要公网地址。

- 在 Developer Portal 建一个应用，拿到 Bot token 就能连。Discord 只让和机器人在同一个服务器里的人私信它，
  所以配对前先用邀请链接把机器人加到你自己的服务器（setup_link），再私信它配对码。
- Gateway（v10，JSON）：收到 Hello 后按 heartbeat_interval 发心跳（第一次随机延后）；Identify 只要 DIRECT_MESSAGES 意图，
  私信的内容不需要特权意图。READY 里记下 session_id 和 resume_gateway_url，断线后 Resume 接着收；
  op 7 要求重连，op 9 的 d=false 要重新 Identify。关闭码 4004、4010–4014 说明 token 或意图有问题，不再重连。
- 只处理私信（没有 guild_id）。peer 是私信频道的 id，回复就发到这个频道。
- 确认卡片是 embed + 按钮（custom_id=ap:<确认请求 id>:<动作>）。点按钮收到 INTERACTION_CREATE，3 秒内回一条只有自己看得见的提示，
  卡片之后用 PATCH 改成结果。
- 服务器在国内连不上 Discord，要设置 HTTPS_PROXY（httpx 和 websockets 都会用）。
"""

from ..i18n import s as _s
import asyncio
import json
import os
import random
import httpx
import websockets
from . import Channel, fmt

API = os.environ.get("OSA_DISCORD_API", "https://discord.com/api/v10").rstrip("/")   # 测试时换成假的服务器
INTENTS = 1 << 12          # DIRECT_MESSAGES
FATAL = {4004: _s('audit_24de406428'), 4010: _s('audit_345f68831d'), 4011: _s('audit_605d57ce7f'),
         4012: _s('audit_f51ac80e6d'), 4013: _s('audit_5e1c67164b'), 4014: _s('audit_3e5734000c')}
ORANGE, GREY = 0xF59E0B, 0x9CA3AF
STYLE = {"primary": 1, "danger": 4}


class DiscordError(Exception):
    def __init__(self, status: int, msg: str, code: int = 0):
        super().__init__(f"{status} {msg}")
        self.status, self.msg, self.code = status, msg, code


async def _call(c: httpx.AsyncClient, token: str, method: str, path: str, body: dict | None = None):
    for attempt in (0, 1, 2):
        r = await c.request(method, API + path, json=body, headers={"Authorization": f"Bot {token}"})
        if r.status_code == 429 and attempt < 2:   # 限流：等它说的时间再试
            try:
                wait = float(r.json().get("retry_after") or 1)
            except ValueError:
                wait = 1.0
            await asyncio.sleep(min(wait, 30))
            continue
        if r.status_code == 204:
            return {}
        try:
            d = r.json()
        except ValueError:
            d = {}
        if r.status_code >= 400:
            raise DiscordError(r.status_code, d.get("message") or r.text[:200], d.get("code") or 0)
        return d
    return {}


class Discord(Channel):
    kind, title, max_len = "discord", "Discord", 1900

    def __init__(self, r: dict, secret: str):
        super().__init__(r, secret)
        self.http = httpx.AsyncClient(timeout=30)
        self._session, self._resume_url, self._seq = "", "", None
        self._acked = True

    async def aclose(self):
        await self.http.aclose()

    async def call(self, method: str, path: str, body: dict | None = None):
        return await _call(self.http, self.secret, method, path, body)

    # ----- 连接 -----
    @classmethod
    async def check(cls, fields: dict) -> dict:
        token = (fields.get("token") or "").strip()
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        if len(token) < 50 or token.count(".") != 2:
            raise ValueError(_s('audit_517fbdc25b'))
        async with httpx.AsyncClient(timeout=20) as c:
            try:
                me = await _call(c, token, "GET", "/users/@me")
                app = await _call(c, token, "GET", "/oauth2/applications/@me")
            except DiscordError as e:
                raise ValueError(_s('audit_ee3ca20282') if e.status == 401 else _s('audit_fc26d2ac0b', v0=e.msg))
            except httpx.HTTPError as e:
                raise ValueError(_s('audit_4933da48a3', v0=type(e).__name__))
        return {"name": me.get("username") or app.get("name") or _s('audit_39a9ca1b99'),
                "config": {"bot_id": me["id"], "app_id": app.get("id") or me["id"], "username": me.get("username", "")},
                "secret": token}

    @classmethod
    def same(cls, r: dict, info: dict) -> bool:
        return r["config"].get("bot_id") == info["config"]["bot_id"]

    @staticmethod
    def pair_link(r: dict) -> str:
        return f"https://discord.com/users/{r['config'].get('bot_id')}"

    @staticmethod
    def setup_link(r: dict) -> str:
        """把机器人加到自己的服务器（不需要任何权限），之后才能私信它。"""
        return f"https://discord.com/oauth2/authorize?client_id={r['config'].get('app_id')}&scope=bot&permissions=0"

    async def run(self):
        backoff = 3
        while True:
            try:
                if not self._session:
                    self._resume_url = ""
                    url = (await self.call("GET", "/gateway/bot"))["url"]
                else:
                    url = self._resume_url
                url += ("&" if "?" in url else "?") + "v=10&encoding=json"
                async with websockets.connect(url, max_size=None) as ws:
                    await self._session_loop(ws)
                    backoff = 3
            except DiscordError as e:
                if e.status == 401:
                    self.set_state("error", FATAL[4004])
                    return
                self.set_state("error", _s('audit_93d5f3a2fe', v0=e.msg))
            except websockets.ConnectionClosed as e:
                code = e.rcvd.code if e.rcvd else 0
                if code in FATAL:
                    self.set_state("error", _s('audit_25e7ff42ef', v0=FATAL[code]))
                    return
                if code in (4007, 4009):   # seq 不对、会话超时：重新 Identify
                    self._session = ""
                self.set_state("error", _s('audit_4cfffa6da3'))
            except (OSError, asyncio.TimeoutError, httpx.HTTPError, websockets.WebSocketException, ValueError, KeyError) as e:
                self.set_state("error", _s('audit_f2c375aded', v0=type(e).__name__))
            await asyncio.sleep(backoff + random.random() * 2)
            backoff = min(backoff * 2, 60)

    async def _session_loop(self, ws):
        hello = json.loads(await asyncio.wait_for(ws.recv(), 30))
        interval = hello["d"]["heartbeat_interval"] / 1000
        self._acked = True
        beat = asyncio.create_task(self._heartbeat(ws, interval))
        try:
            if self._session:
                await ws.send(json.dumps({"op": 6, "d": {"token": self.secret, "session_id": self._session, "seq": self._seq}}))
            else:
                await self._identify(ws)
            async for raw in ws:
                p = json.loads(raw)
                op = p.get("op")
                if p.get("s") is not None:
                    self._seq = p["s"]
                if op == 0:
                    t, d = p.get("t"), p.get("d") or {}
                    if t == "READY":
                        self._session, self._resume_url = d["session_id"], d.get("resume_gateway_url") or ""
                        self.set_state("connected")
                    elif t == "RESUMED":
                        self.set_state("connected")
                    elif t == "MESSAGE_CREATE":
                        asyncio.create_task(self._safe(self.on_message(d)))
                    elif t == "INTERACTION_CREATE":
                        asyncio.create_task(self._safe(self.on_interaction(d)))
                elif op == 1:
                    await ws.send(json.dumps({"op": 1, "d": self._seq}))
                elif op == 11:
                    self._acked = True
                elif op == 7:   # 要求重连：断开后 Resume
                    await ws.close(4000)
                    return
                elif op == 9:   # 会话失效
                    if not p.get("d"):
                        self._session, self._seq = "", None
                    await asyncio.sleep(1 + random.random() * 4)
                    await ws.close(4000)
                    return
        finally:
            beat.cancel()

    async def _identify(self, ws):
        await ws.send(json.dumps({"op": 2, "d": {"token": self.secret, "intents": INTENTS, "properties": {
            "os": "linux", "browser": "open-super-agent", "device": "open-super-agent"}}}))

    async def _heartbeat(self, ws, interval: float):
        await asyncio.sleep(interval * random.random())
        while True:
            if not self._acked:   # 上次心跳没回：连接已经死了，断开后 Resume
                await ws.close(4000)
                return
            self._acked = False
            await ws.send(json.dumps({"op": 1, "d": self._seq}))
            await asyncio.sleep(interval)

    # ----- 收 -----
    async def on_message(self, m: dict):
        author = m.get("author") or {}
        if m.get("guild_id") or author.get("bot") or author.get("id") == self.row["config"].get("bot_id"):
            return   # 只要别人发给机器人的私信
        peer = m.get("channel_id", "")
        who = author.get("global_name") or author.get("username") or ""
        text = m.get("content") or ""
        files = [(a.get("filename") or f"file_{a.get('id')}", a["url"]) for a in m.get("attachments") or [] if a.get("url")]
        if (m.get("flags") or 0) & 8192:   # 语音消息
            if peer == self.row["peer"]:
                self.say(_s('audit_e728acb4e2'))
            return
        await self.inbound(peer, who, text, files)

    async def on_interaction(self, d: dict):
        if d.get("type") != 3:   # 只有按钮
            return
        peer = "" if d.get("guild_id") else d.get("channel_id") or (d.get("channel") or {}).get("id", "")
        job = asyncio.create_task(self.press(peer, (d.get("data") or {}).get("custom_id", "")))
        done, _ = await asyncio.wait({job}, timeout=2.5)   # Discord 要 3 秒内回应；交还电脑这类慢的先回一句，接着做
        toast = job.result() if done else _s('audit_e220c3405a')
        await self.call("POST", f"/interactions/{d['id']}/{d['token']}/callback",
                        {"type": 4, "data": {"content": toast[:2000], "flags": 64}})

    async def download(self, url: str) -> bytes:
        r = await self.http.get(url, timeout=120)
        r.raise_for_status()
        return r.content

    # ----- 发 -----
    async def send_text(self, peer: str, md: str):
        await self.call("POST", f"/channels/{peer}/messages",
                        {"content": fmt.discord_md(md)[:2000], "allowed_mentions": {"parse": []}})

    @staticmethod
    def _card(card: dict) -> dict:
        body = fmt.discord_md(card["body"])
        if card.get("done"):
            body += f"\n\n**{card['done']}**"
        rows = []
        btns = [{"type": 2, "style": STYLE.get(style, 2), "label": label, "custom_id": f"ap:{card['id']}:{act}"}
                for label, act, style in card["buttons"]]
        if card.get("link") and card["link"][1].startswith(("https://", "http://")):
            btns.append({"type": 2, "style": 5, "label": card["link"][0], "url": card["link"][1]})
        if btns:
            rows.append({"type": 1, "components": btns[:5]})
        return {"embeds": [{"title": card["title"][:256], "description": body[:4096],
                            "color": GREY if card.get("done") else ORANGE}],
                "components": rows, "allowed_mentions": {"parse": []}}

    async def send_card(self, peer: str, card: dict) -> str:
        return (await self.call("POST", f"/channels/{peer}/messages", self._card(card))).get("id", "")

    async def edit_card(self, peer: str, msg_id: str, card: dict):
        if msg_id:
            await self.call("PATCH", f"/channels/{peer}/messages/{msg_id}", self._card(card))

    async def typing(self, peer: str):
        await self.call("POST", f"/channels/{peer}/typing")
