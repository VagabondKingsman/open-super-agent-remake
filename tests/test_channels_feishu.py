"""飞书适配器：配对（check）、token 缓存与失效重试、发消息/卡片、事件去重、收附件。

不连真的飞书：HTTP 走 httpx.MockTransport，长连接是一个假的对象。
"""
import asyncio
import json
import time

import httpx
import pytest

from osa.channels import feishu


class FakeHTTP:
    """按 (method, path) 回答的假服务器，顺带记下每个请求。"""

    def __init__(self, routes: dict | None = None):
        self.routes = routes or {}
        self.seen: list[tuple[str, str, dict]] = []
        self.files: dict[str, bytes] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content or b"{}") if request.content else {}
        self.seen.append((request.method, request.url.path, body))
        for (method, path), answer in self.routes.items():
            if request.method == method and request.url.path == path:
                answer = answer() if callable(answer) else answer
                return answer if isinstance(answer, httpx.Response) else httpx.Response(200, json=answer)
        if key := self.files.get(request.url.path):
            return httpx.Response(200, content=key, headers={"content-type": "image/png"})
        raise AssertionError(f"没有准备 {request.method} {request.url.path}")

    def calls(self, path: str) -> list[dict]:
        return [b for m, p, b in self.seen if p == path]


REAL_CLIENT = httpx.AsyncClient   # 在打补丁之前抓住真的类，免得一个测试里打两次补丁就套娃
TOKEN = "/open-apis/auth/v3/tenant_access_token/internal"
BOT = "/open-apis/bot/v3/info"
MESSAGES = "/open-apis/im/v1/messages"


def patch(monkeypatch, fake: FakeHTTP):
    monkeypatch.setattr(feishu.httpx, "AsyncClient",
                        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(fake), **{k: v for k, v in kw.items() if k != "transport"}))


def channel(monkeypatch, fake: FakeHTTP, **cfg):
    patch(monkeypatch, fake)
    row = {"id": 7, "kind": "feishu", "name": "Bot", "config": {"app_id": "cli_abc", "domain": "feishu", **cfg},
           "chat_id": 1, "peer": "oc_1", "peer_name": "", "pair_code": "", "pair_expires": 0, "pair_fails": 0,
           "enabled": 1, "created": 0}
    c = feishu.Feishu(row, "secret")
    c.said, c.pressed, c.inbox = [], [], []

    async def say(md):
        c.said.append(md)

    async def press(peer, data):
        c.pressed.append((peer, data))
        return "ok"

    async def inbound(peer, aid, text, files):
        c.inbox.append({"peer": peer, "text": text, "files": files})

    c.say, c.press, c.inbound = say, press, inbound
    return c


# ---------- 配对 ----------
async def test_check_accepts_a_real_app(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"code": 0, "tenant_access_token": "t", "expire": 7200},
                       ("GET", BOT): {"code": 0, "bot": {"app_name": "Trợ lý", "open_id": "ou_1"}}})
    patch(monkeypatch, fake)
    info = await feishu.Feishu.check({"app_id": "cli_abc", "app_secret": "s", "domain": "lark"})
    assert info["name"] == "Trợ lý" and info["secret"] == "s"
    assert info["config"] == {"app_id": "cli_abc", "domain": "lark", "open_id": "ou_1"}
    assert fake.seen[0][2] == {"app_id": "cli_abc", "app_secret": "s"}


async def test_check_explains_what_is_wrong(monkeypatch):
    patch(monkeypatch, FakeHTTP())
    with pytest.raises(ValueError, match="cli_"):
        await feishu.Feishu.check({"app_id": "abc", "app_secret": "s"})
    with pytest.raises(ValueError, match="App Secret"):
        await feishu.Feishu.check({"app_id": "cli_abc"})

    fake = FakeHTTP({("POST", TOKEN): {"code": 10003, "msg": "invalid param"},
                        ("GET", BOT): {"code": 0, "bot": {}}})
    patch(monkeypatch, fake)
    with pytest.raises(ValueError, match="不对"):
        await feishu.Feishu.check({"app_id": "cli_abc", "app_secret": "bad"})

    fake = FakeHTTP({("POST", TOKEN): {"code": 0, "tenant_access_token": "t"},
                        ("GET", BOT): {"code": 10031, "msg": "bot not enabled"}})
    patch(monkeypatch, fake)
    with pytest.raises(ValueError, match="机器人"):
        await feishu.Feishu.check({"app_id": "cli_abc", "app_secret": "s"})

    fake = FakeHTTP({("POST", TOKEN): lambda: (_ for _ in ()).throw(httpx.ConnectError("no route"))})
    patch(monkeypatch, fake)
    with pytest.raises(ValueError, match="连不上"):
        await feishu.Feishu.check({"app_id": "cli_abc", "app_secret": "s"})


def test_pairing_link_and_same_account():
    row = {"config": {"app_id": "cli_abc", "domain": "lark"}}
    link = feishu.Feishu.pair_link(row)
    assert link.startswith("https://applink.larksuite.com/client/bot/open?appId=cli_abc")
    assert feishu.Feishu.same(row, {"config": {"app_id": "cli_abc"}})
    assert not feishu.Feishu.same(row, {"config": {"app_id": "cli_other"}})


# ---------- token ----------
async def test_the_token_is_kept_and_refreshed(monkeypatch):
    tokens = iter(["t1", "t2"])

    def new_token():
        return {"code": 0, "tenant_access_token": next(tokens), "expire": 7200}
    fake = FakeHTTP({("POST", TOKEN): new_token, ("GET", BOT): {"code": 0, "bot": {}}})
    c = channel(monkeypatch, fake, open_id="ou_1")
    assert await c.token() == "t1" and await c.token() == "t1"
    assert len(fake.calls(TOKEN)) == 1                     # 缓存着，没有每次都换
    c._token_exp = time.time() - 1                          # 过期了
    assert await c.token() == "t2" and len(fake.calls(TOKEN)) == 2


async def test_a_stale_token_is_replaced_once(monkeypatch):
    """飞书那边说 token 失效（99991661）：换一个 token 再发一次，用户看不到错误。"""
    order = iter([{"code": 99991661, "msg": "token expired"}, {"code": 0, "data": {"message_id": "om_1"}}])

    def send():
        return order.__next__()
    tokens = iter(["t1", "t2"])
    fake = FakeHTTP({("POST", TOKEN): lambda: {"code": 0, "tenant_access_token": next(tokens)},
                        ("POST", MESSAGES): send})
    c = channel(monkeypatch, fake)
    d = await c.api("POST", MESSAGES, json={"x": 1})
    assert d == {"message_id": "om_1"} and len(fake.calls(TOKEN)) == 2 and c._token == "t2"


async def test_other_api_errors_are_raised(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"code": 0, "tenant_access_token": "t"},
                        ("POST", MESSAGES): {"code": 230002, "msg": "bot is not in the chat"}})
    c = channel(monkeypatch, fake)
    with pytest.raises(feishu.FeishuError) as e:
        await c._create("oc_1", "text", {"text": "hi"})
    assert e.value.code == 230002 and "not in the chat" in str(e.value)


# ---------- 发 ----------
async def test_send_text_uses_the_rich_post_and_falls_back(monkeypatch):
    sent = []

    def send():
        sent.append(1)
        if len(sent) == 1:
            return {"code": 230002, "msg": "no post"}
        return {"code": 0, "data": {"message_id": "om_9"}}
    fake = FakeHTTP({("POST", TOKEN): {"code": 0, "tenant_access_token": "t"}, ("POST", MESSAGES): send})
    c = channel(monkeypatch, fake)
    await c.send_text("oc_1", "**xin chào**")
    first, second = fake.calls(MESSAGES)
    assert first["msg_type"] == "post" and first["receive_id"] == "oc_1"
    assert json.loads(first["content"])["zh_cn"]["content"]     # 富文本（md 段）
    assert second["msg_type"] == "text" and "xin chào" in json.loads(second["content"])["text"]


async def test_cards_carry_the_buttons_and_are_edited_in_place(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"code": 0, "tenant_access_token": "t"},
                        ("POST", MESSAGES): {"code": 0, "data": {"message_id": "om_5"}},
                        ("PATCH", f"{MESSAGES}/om_5"): {"code": 0, "data": {}}})
    c = channel(monkeypatch, fake)
    card = {"id": 12, "title": "允许吗", "body": "**git push**", "buttons": [("允许", "allow", "primary"), ("拒绝", "deny", "danger")],
            "link": ("看看", "https://example.com")}
    assert await c.send_card("oc_1", card) == "om_5"
    created = fake.calls(MESSAGES)[-1]
    assert created["msg_type"] == "interactive"
    body = json.loads(created["content"])
    assert body["config"]["update_multi"] and body["header"]["template"] == "orange"
    actions = next(e for e in body["elements"] if e["tag"] == "action")["actions"]
    assert [a["value"]["osa"] for a in actions[:2]] == ["ap:12:allow", "ap:12:deny"]
    assert actions[0]["type"] == "primary" and actions[2]["url"] == "https://example.com"

    await c.edit_card("oc_1", "om_5", {**card, "done": "已允许"})
    edited = fake.calls(f"{MESSAGES}/om_5")[-1]
    body = json.loads(edited["content"])
    assert body["header"]["template"] == "grey" and any("已允许" in e.get("content", "") for e in body["elements"])
    await c.edit_card("oc_1", "", card)          # 没有消息 id：什么也不做，也不报错


# ---------- 收 ----------
def event(kind: str, ev: dict, eid: str = "ev_1") -> dict:
    return {"header": {"event_id": eid, "event_type": kind}, "event": ev}


async def test_a_message_arrives_once_even_if_feishu_resends_it(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    p = event("im.message.receive_v1", {"message": {"chat_id": "oc_1", "message_id": "om_1", "message_type": "text",
                                                     "chat_type": "p2p", "content": json.dumps({"text": "chào"})},
                                         "sender": {"sender_type": "user"}})
    await c._event(p)
    await c._event(p)          # 同一个 event_id 再来一次：去重
    await asyncio.sleep(0.05)
    assert [m["text"] for m in c.inbox] == ["chào"] and c.inbox[0]["peer"] == "oc_1"
    assert c.last_msg == "om_1"    # “正在输入”的表情加在这条上


async def test_group_messages_and_the_bot_itself_are_ignored(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    group = event("im.message.receive_v1", {"message": {"chat_id": "oc_1", "message_id": "m", "message_type": "text",
                                                        "chat_type": "group", "content": "{}"}, "sender": {}}, eid="e1")
    own = event("im.message.receive_v1", {"message": {"chat_id": "oc_1", "message_id": "m", "message_type": "text",
                                                      "chat_type": "p2p", "content": "{}"},
                                           "sender": {"sender_type": "app"}}, eid="e2")
    await c._event(group)
    await c._event(own)
    await asyncio.sleep(0.02)
    assert c.inbox == []


async def test_images_and_files_become_attachments(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    post = {"title": "x", "content": [[{"tag": "md", "text": "看这个"}, {"tag": "img", "image_key": "img_key_123456"}]]}
    await c._event(event("im.message.receive_v1", {
        "message": {"chat_id": "oc_1", "message_id": "om_9", "message_type": "post", "chat_type": "p2p",
                    "content": json.dumps(post)}, "sender": {}}))
    file_ev = event("im.message.receive_v1", {
        "message": {"chat_id": "oc_1", "message_id": "om_10", "message_type": "file", "chat_type": "p2p",
                    "content": json.dumps({"file_name": "bao.pdf", "file_key": "fk"})}, "sender": {}}, eid="e2")
    await c._event(file_ev)
    await asyncio.sleep(0.05)
    assert c.inbox[0]["files"] == [(f"image_{'img_key_123456'[-10:]}.png", ("om_9", "img_key_123456", "image"))]
    assert c.inbox[0]["text"].startswith("x\n看这个")
    assert c.inbox[1]["files"] == [("bao.pdf", ("om_10", "fk", "file"))]


async def test_a_card_button_press_is_answered_with_a_toast(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    out = await c._event(event("card.action.trigger", {"context": {"open_chat_id": "oc_1"},
                                                      "action": {"value": {"osa": "ap:3:allow"}}}))
    assert c.pressed == [("oc_1", "ap:3:allow")] and out == {"toast": {"type": "info", "content": "ok"}}


# ---------- 附件、分包帧 ----------
async def test_download_explains_a_permission_problem(monkeypatch):
    path = "/open-apis/im/v1/messages/om_1/resources/fk"
    fake = FakeHTTP({("POST", TOKEN): {"code": 0, "tenant_access_token": "t"},
                      ("GET", path): lambda: httpx.Response(200, json={"code": 234003, "msg": "no permission"},
                                                            headers={"content-type": "application/json"})})
    c = channel(monkeypatch, fake)
    with pytest.raises(ValueError, match="权限"):
        await c.download(("om_1", "fk", "file"))
    ok = FakeHTTP({("POST", TOKEN): {"code": 0, "tenant_access_token": "t"}})
    ok.files[path] = b"\x89PNG..."
    c = channel(monkeypatch, ok)
    assert await c.download(("om_1", "fk", "image")) == b"\x89PNG..."


async def test_a_split_event_is_put_back_together_and_answered(monkeypatch):
    """大的事件按 sum/seq 分包：凑齐了才处理，处理完回一个 code=200 的帧（3 秒内不回会重推）。"""
    c = channel(monkeypatch, FakeHTTP())
    payload = json.dumps(event("im.message.receive_v1", {
        "message": {"chat_id": "oc_1", "message_id": "om_1", "message_type": "text", "chat_type": "p2p",
                    "content": json.dumps({"text": "một hai ba"})}, "sender": {}})).encode()
    half = len(payload) // 2

    class WS:
        def __init__(self):
            self.sent = []

        async def send(self, raw):
            self.sent.append(feishu.decode_frame(raw))
    ws = WS()

    def frame(seq, chunk):
        return feishu.encode_frame({"seq": seq, "log": 1, "service": 1, "method": 1,
                                    "headers": [("type", "event"), ("message_id", "m1"), ("sum", "2"), ("seq", str(seq))],
                                    "payload": chunk})
    await c._frame(ws, frame(0, payload[:half]))
    assert ws.sent == [] and c.inbox == []          # 还没齐
    await c._frame(ws, frame(1, payload[half:]))
    await asyncio.sleep(0.05)
    assert [m["text"] for m in c.inbox] == ["một hai ba"]
    ack = ws.sent[-1]
    body = json.loads(ack["payload"])
    assert body["code"] == 200 and dict(ack["headers"])["biz_rt"].isdigit()


async def test_a_broken_event_is_answered_with_500(monkeypatch):
    """事件处理出错要回 500：飞书会重推，总比悄悄吞掉好。"""
    c = channel(monkeypatch, FakeHTTP())
    class WS:
        def __init__(self):
            self.sent = []

        async def send(self, raw):
            self.sent.append(feishu.decode_frame(raw))
    ws = WS()
    raw = feishu.encode_frame({"seq": 1, "log": 1, "service": 1, "method": 1, "headers": [("type", "event")],
                                "payload": b"{not json"})
    await c._frame(ws, raw)
    assert json.loads(ws.sent[-1]["payload"])["code"] == 500


async def test_ping_keeps_the_long_connection_alive(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())

    class WS:
        def __init__(self):
            self.sent = []

        async def send(self, raw):
            self.sent.append(feishu.decode_frame(raw))
    ws = WS()
    task = asyncio.create_task(c._ping(ws, 9, {"PingInterval": 0.05}))
    await asyncio.sleep(0.12)
    task.cancel()
    assert len(ws.sent) >= 2 and all(f["method"] == 0 and dict(f["headers"]) == {"type": "ping"} for f in ws.sent)
    assert all(f["service"] == 9 for f in ws.sent)
