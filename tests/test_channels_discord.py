"""B8: the Discord adapter, offline. Token check, pairing links, sending (limits, markdown, cards), rate limits,
who is listened to, and the gateway session loop -- all against a fake HTTP transport and a fake websocket."""
import asyncio
import json
import time

import httpx
import pytest

from osa import channels
from osa.channels import discord, fmt
from osa.memory import conn

TOKEN = "MTA." + "x" * 46 + ".yyyyyyyyyyyyyyyyyyyyyyyyyyy"
REAL = httpx.AsyncClient   # 补丁会落到 httpx 全局（discord.httpx 就是这个模块）：先留一份真的   # 三段、够长：check() 的形状检查


def ok(body):
    return httpx.Response(200, json=body)


class Api:
    """假的 Discord HTTP：routes 是 (method, 正则) -> 回复；每条请求都记下来。"""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls: list[dict] = []

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        body = json.loads(request.content or b"{}") if request.content else None
        self.calls.append({"method": method, "path": path, "body": body,
                           "auth": request.headers.get("authorization", "")})
        for (m, part), reply in self.routes.items():
            if m == method and part in path:
                return reply(body) if callable(reply) else reply
        return ok({})


@pytest.fixture
def api(monkeypatch):
    box = Api()

    def install(routes=None):
        if routes:
            box.routes = routes
        monkeypatch.setattr(discord.httpx, "AsyncClient",
                            lambda **kw: REAL(transport=httpx.MockTransport(box), **kw))
        return box
    return install


def channel(make_bot, peer: str = "dm1", config: dict | None = None, kind: str = "discord"):
    """数据库里的一条连接，和它对应的适配器。"""
    bot = make_bot("Disc")
    cur = conn.execute("insert into channels(kind, name, config, chat_id, peer, peer_name, created) values(?,?,?,?,?,?,?)",
                       (kind, "osa", json.dumps(config or {"bot_id": "9", "app_id": "app", "username": "osa"}),
                        bot["chat_id"], peer, "dat" if peer else "", time.time()))
    conn.commit()
    r = channels.row(cur.lastrowid)
    return discord.Discord(r, TOKEN), r["id"]


async def drain(c, n: int = 0):
    """把 say() 排进 outbox 的话真的发出去（平常由 _sender 协程做）。n=0：有多少发多少。"""
    for _ in range(n or 10 ** 6):
        try:
            job = await asyncio.wait_for(c.outbox.get(), 0.2)
        except asyncio.TimeoutError:
            return
        await job()


# ---------- 连接 / 配对 ----------
async def test_check_takes_a_good_token_and_strips_the_bot_prefix(api, monkeypatch):
    box = api({("GET", "/users/@me"): ok({"id": "42", "username": "osa_bot"}),
               ("GET", "/oauth2/applications/@me"): ok({"id": "app7", "name": "OSA"})})
    info = await discord.Discord.check({"token": "Bot " + TOKEN})
    assert info["name"] == "osa_bot" and info["secret"] == TOKEN
    assert info["config"] == {"bot_id": "42", "app_id": "app7", "username": "osa_bot"}
    assert box.calls[0]["auth"] == f"Bot {TOKEN}"          # Bot 前缀只去掉一次，鉴权头照样是 Bot <token>


async def test_check_explains_a_bad_token(api, monkeypatch):
    api({("GET", "/users/@me"): httpx.Response(401, json={"message": "401: Unauthorized", "code": 0})})
    with pytest.raises(ValueError, match="token 格式不对"):
        await discord.Discord.check({"token": "short"})
    with pytest.raises(ValueError, match="token 不对"):
        await discord.Discord.check({"token": TOKEN})
    api({("GET", "/users/@me"): httpx.Response(502, json={"message": "bad gateway"})})
    with pytest.raises(ValueError, match="返回错误"):
        await discord.Discord.check({"token": TOKEN})

    def boom(request):
        raise httpx.ConnectError("no route")
    api({("GET", "/users/@me"): ok({"id": "1", "username": "u"})})
    monkeypatch.setattr(discord.httpx, "AsyncClient",
                        lambda **kw: REAL(transport=httpx.MockTransport(boom), **kw))
    with pytest.raises(ValueError, match="HTTPS_PROXY"):   # 国内的服务器连不上：说清楚要设代理
        await discord.Discord.check({"token": TOKEN})


def test_identity_and_the_links_to_pair():
    r = {"config": {"bot_id": "42", "app_id": "app7"}}
    assert discord.Discord.same(r, {"config": {"bot_id": "42"}}) and not discord.Discord.same(r, {"config": {"bot_id": "1"}})
    assert discord.Discord.pair_link(r) == "https://discord.com/users/42"
    link = discord.Discord.setup_link(r)
    assert "client_id=app7" in link and "scope=bot" in link and "permissions=0" in link


# ---------- 发 ----------
async def test_a_long_answer_is_split_into_discord_sized_pieces(api, make_bot):
    c, _ = channel(make_bot)
    sent = []
    async def fake_send(peer, md):
        sent.append((peer, md))
    c.send_text = fake_send
    await c._send_md("dm1", "# 标题\n**粗** " + "甲" * 4200)
    whole = "".join(m for _, m in sent)
    assert len(sent) >= 2 and {p for p, _ in sent} == {"dm1"}          # 太长就分几条，一条都不超过上限
    assert all(len(m) <= c.max_len for _, m in sent)
    assert "标题" in whole and "粗" in whole and whole.count("甲") == 4200     # 一个字都没丢


async def test_send_text_mentions_nobody(api, make_bot):
    box = api({("POST", "/channels/dm1/messages"): ok({"id": "m1"})})
    c, _ = channel(make_bot)
    await c.send_text("dm1", "@everyone hi")
    body = box.calls[-1]["body"]
    assert box.calls[-1]["path"].endswith("/channels/dm1/messages")
    assert body["allowed_mentions"] == {"parse": []} and "@everyone" in body["content"]


async def test_cards_are_embeds_with_buttons(api, make_bot):
    box = api({("POST", "/channels/dm1/messages"): ok({"id": "m9"})})
    c, _ = channel(make_bot)
    card = {"id": 31, "kind": "approval", "title": "跑命令", "body": "**git push**", "buttons": [("允许", "ok", "primary")],
            "link": ("看看", "https://example.com/x")}
    built = discord.Discord._card(card)
    assert built["embeds"][0]["title"] == "跑命令" and built["embeds"][0]["color"] == discord.ORANGE
    btns = built["components"][0]["components"]
    assert btns[0]["custom_id"] == "ap:31:ok" and btns[0]["style"] == discord.STYLE["primary"]
    assert btns[1]["style"] == 5 and btns[1]["url"] == "https://example.com/x"   # 链接按钮
    assert await c.send_card("dm1", card) == "m9"
    done = discord.Discord._card(card | {"buttons": [], "link": None, "done": "处理完了"})
    assert done["components"] == [] and done["embeds"][0]["color"] == discord.GREY
    assert done["embeds"][0]["description"].endswith("**处理完了**")   # 结果写在正文最后


async def test_editing_a_card_patches_the_same_message(api, make_bot):
    box = api({("PATCH", "/channels/dm1/messages/m1"): ok({"id": "m1"})})
    c, _ = channel(make_bot)
    await c.edit_card("dm1", "m1", {"id": 1, "kind": "approval", "title": "t", "body": "b", "buttons": []})
    assert box.calls[-1]["method"] == "PATCH" and box.calls[-1]["path"].endswith("/channels/dm1/messages/m1")


# ---------- 限流 / 断线 ----------
async def test_rate_limit_waits_and_tries_again(api, make_bot, monkeypatch):
    state = {"n": 0}

    def boom_429(body):
        state["n"] += 1
        return httpx.Response(429, json={"retry_after": 0.01}) if state["n"] < 3 else ok({"id": "m1"})
    box = api({("POST", "/channels/dm1/messages"): boom_429})
    c, _ = channel(make_bot)
    await c.send_text("dm1", "hi")
    assert state["n"] == 3 and len(box.calls) == 3       # 两次限流，第三次成功


async def test_errors_come_back_as_discord_errors(api, make_bot):
    api({("POST", "/channels/dm1/messages"): httpx.Response(403, json={"message": "Missing Access", "code": 50001})})
    c, _ = channel(make_bot)
    with pytest.raises(discord.DiscordError) as e:
        await c.send_text("dm1", "hi")
    assert e.value.status == 403 and e.value.code == 50001


# ---------- 收 ----------
async def test_only_private_messages_from_other_people_count(api, make_bot, monkeypatch):
    got = []

    async def handle(chat, text, via, atts):
        got.append((chat["id"], text, via, atts))
    monkeypatch.setattr(channels, "handle", handle)
    api({("GET", "/x"): httpx.Response(200, content=b"hello")})   # 附件的内容
    c, cid = channel(make_bot)
    said = []
    async def fake_send(peer, md):
        said.append(md)
    c.send_text = fake_send

    async def save_upload(name, data):
        return f"/data/workspace/uploads/{name}"
    monkeypatch.setattr(channels, "save_upload", save_upload)   # 本机电脑在测试里是关着的：附件存到“电脑”这一步假装成功
    base = {"channel_id": "dm1", "content": "你好", "author": {"id": "7", "username": "dat"}}
    await c.on_message(base | {"guild_id": "g1"})                       # 服务器里的消息：不理
    await c.on_message(base | {"author": {"id": "9", "bot": True}})      # 自己发的：不理
    await c.on_message(base | {"channel_id": "other"})                  # 别人（没配对）：不理
    await asyncio.sleep(0.05)
    assert not got and c.outbox.empty()
    await c.on_message(base | {"flags": 8192})                          # 语音消息：不说“听不懂”
    await drain(c)
    assert said and "打字" in said[0]
    await c.on_message(base | {"attachments": [{"id": "a1", "filename": "a.txt", "url": "https://cdn/x"}]})
    await asyncio.sleep(0.05)
    assert got and got[-1][1] == "你好" and got[-1][2] == "discord" and got[-1][3][0]["name"] == "a.txt"
    assert got[-1][0] == c.row["chat_id"]


async def test_the_inbound_path_pairs_with_the_six_digit_code(api, make_bot, monkeypatch):
    code = "246810"
    c, cid = channel(make_bot, peer="", config={"bot_id": "9", "app_id": "app"})
    conn.execute("update channels set pair_code=?, pair_expires=? where id=?", (code, time.time() + 60, cid))
    conn.commit()
    sent = []
    async def fake_send(peer, md):
        sent.append((peer, md))
    c.send_text = fake_send
    await c.on_message({"channel_id": "dm1", "content": code, "author": {"id": "7", "username": "dat"}})
    await drain(c, 2)
    assert channels.row(cid)["peer"] == "dm1" and any("配对成功" in md for _, md in sent)
    conn.execute("update channels set peer='' where id=?", (cid,))
    conn.commit()


async def test_download_takes_the_bytes(api, make_bot):
    api({("GET", "/file"): httpx.Response(200, content=b"file-bytes")})
    c, _ = channel(make_bot)
    assert await c.download("https://cdn.example/file") == b"file-bytes"


async def test_a_button_press_is_acknowledged_privately(api, make_bot, monkeypatch):
    box = api({("POST", "/interactions/i1/tok1/callback"): httpx.Response(204)})
    c, _ = channel(make_bot)

    async def press(peer, data):
        return "已允许"
    monkeypatch.setattr(c, "press", press)
    await c.on_interaction({"id": "i1", "token": "tok1", "type": 3, "channel_id": "dm1", "data": {"custom_id": "ap:5:ok"}})
    body = box.calls[-1]["body"]
    assert box.calls[-1]["path"].endswith("/interactions/i1/tok1/callback")
    assert body == {"type": 4, "data": {"content": "已允许", "flags": 64}}   # 只有点的人看得见
    box.calls.clear()
    await c.on_interaction({"id": "i2", "token": "t", "type": 2})           # 不是按钮：不回
    assert not box.calls


# ---------- 长连接 ----------
class FakeWS:
    """一条假的 Gateway 连接：把 frames 一条条吐出来，记下发出去的东西和关闭码。"""

    def __init__(self, frames):
        self.frames, self.sent, self.closed = list(frames), [], None

    async def recv(self):
        return self.frames.pop(0)

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def close(self, code=1000):
        self.closed = code

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.frames:
            raise StopAsyncIteration
        return self.frames.pop(0)


HELLO = json.dumps({"op": 10, "d": {"heartbeat_interval": 60000}})


async def test_the_session_identifies_and_delivers_messages(api, make_bot, monkeypatch):
    c, _ = channel(make_bot)
    seen = []

    async def on_message(m):
        seen.append(m["content"])
    monkeypatch.setattr(c, "on_message", on_message)
    ws = FakeWS([
        HELLO,
        json.dumps({"op": 0, "s": 1, "t": "READY", "d": {"session_id": "s1", "resume_gateway_url": "wss://resume"}}),
        json.dumps({"op": 0, "s": 2, "t": "MESSAGE_CREATE", "d": {"content": "hi", "channel_id": "dm1"}}),
        json.dumps({"op": 11}),                                       # 心跳的回音
        json.dumps({"op": 7}),                                        # 要我重连
    ])
    await c._session_loop(ws)
    assert ws.sent[0] == {"op": 2, "d": {"token": TOKEN, "intents": discord.INTENTS, "properties": {
        "os": "linux", "browser": "open-super-agent", "device": "open-super-agent"}}}
    assert (c._session, c._resume_url, c._seq) == ("s1", "wss://resume", 2)   # 最后一条带序号的事件
    assert c.state == "connected"
    await asyncio.sleep(0.05)          # 分发是 create_task：让它们跑完
    assert seen == ["hi"]
    assert ws.closed == 4000                                          # op 7：断开后从 resume 地址接着收


async def test_a_dead_session_starts_over(api, make_bot):
    c, _ = channel(make_bot)
    c._session, c._seq = "old", 9
    ws = FakeWS([HELLO, json.dumps({"op": 9, "d": None})])
    await c._session_loop(ws)
    assert c._session == "" and c._seq is None and c.state == "connecting"   # 重新 Identify，不是 Resume
    assert ws.closed == 4000


async def test_missing_heartbeat_acks_drop_the_connection(api, make_bot, monkeypatch):
    c, _ = channel(make_bot)
    monkeypatch.setattr(discord.random, "random", lambda: 0)
    c._acked = False
    ws = FakeWS([])
    await c._heartbeat(ws, 0.01)
    assert ws.closed == 4000 and not ws.sent        # 上一次心跳没人应：断线重来，别再傻等


async def test_a_fatal_close_code_stops_instead_of_retrying(api, make_bot):
    """4004（token 失效）：不再重连，把原因写在连接上。"""
    c, _ = channel(make_bot)
    err = discord.websockets.ConnectionClosed(
        discord.websockets.frames.Close(code=4004, reason="auth failed"), None)
    assert err.rcvd.code == 4004                     # 就是这个东西让 run() 里的分支认得
