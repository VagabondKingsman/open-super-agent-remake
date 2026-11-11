"""企业微信适配器：配对、回执按 req_id 对上、去重、卡片按钮与 5 秒内改卡片、解密下载、ping。

不连真的企业微信：HTTP 走 httpx.MockTransport，长连接用假的对象。
"""
import asyncio
import base64
import json
import os
import time

import httpx
import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from osa.channels import wecom


class FakeHTTP:
    """按 path 回答的假服务器（企业微信这边只有下载用 HTTP）。"""

    def __init__(self, routes: dict | None = None):
        self.routes = routes or {}
        self.seen: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request.url.path)
        for path, answer in self.routes.items():
            if request.url.path == path:
                return answer() if callable(answer) else answer
        raise AssertionError(f"没有准备 GET {request.url.path}")


REAL_CLIENT = httpx.AsyncClient


def patch_http(monkeypatch, fake: FakeHTTP):
    monkeypatch.setattr(wecom.httpx, "AsyncClient",
                        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(fake),
                                                 **{k: v for k, v in kw.items() if k != "transport"}))


def channel(monkeypatch, fake=None, *, peer="zhang", connected=True):
    patch_http(monkeypatch, fake or FakeHTTP())
    row = {"id": 11, "kind": "wecom", "name": "Robot", "config": {"bot_id": "bot_1"}, "chat_id": 1,
           "peer": peer, "peer_name": "An", "pair_code": "", "pair_expires": time.time() + 600,
           "pair_fails": 0, "enabled": 1, "created": 0}
    c = wecom.WeCom(row, "secret")
    c.said, c.pressed, c.inbox = [], [], []

    def say(md, peer=None):
        c.said.append(md)

    async def press(peer, data):
        c.pressed.append((peer, data))
        return "ok"

    async def inbound(peer, name, text, files):
        c.inbox.append({"peer": peer, "text": text, "files": files})

    c.say, c.press, c.inbound = say, press, inbound
    if connected:
        c.ws = FakeWS(c)
    return c


class FakeWS:
    """假的连接：发出去的帧记下来，需要回执的当场把回执从 channel._frame 送回去。"""

    def __init__(self, c, answers: dict | None = None):
        self.c, self.sent, self.answers, self.closed = c, [], answers or {}, False
        self.waiting: list[str] = []

    async def send(self, raw):
        f = json.loads(raw)
        self.sent.append(f)
        cmd, rid = f.get("cmd", ""), (f.get("headers") or {}).get("req_id", "")
        if cmd == "ping":
            return
        ans = self.answers.get(cmd, {"errcode": 0, "errmsg": "ok"})
        ans = ans.pop(0) if isinstance(ans, list) else (ans(rid) if callable(ans) else ans)
        if ans is not None:
            await self.c._frame({"headers": {"req_id": rid, **(ans.get("headers") or {})}, **{k: v for k, v in ans.items()
                                                                                            if k != "headers"}})

    async def close(self):
        self.closed = True


# ---------- 配对 ----------
class SubWS:
    """check() 里那条连接：send 记下订阅帧，recv 把回执还回去。"""

    def __init__(self, answer: dict):
        self.answer, self.sent = answer, []

    async def send(self, raw):
        f = json.loads(raw)
        self.sent.append(f)
        self.reply = {**self.answer, "headers": {"req_id": f["headers"]["req_id"]}}

    async def recv(self):
        return json.dumps(self.reply)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def test_check_subscribes_with_the_bot_and_secret(monkeypatch):
    ws = SubWS({"errcode": 0})
    monkeypatch.setattr(wecom.websockets, "connect", lambda *a, **kw: ws)
    info = await wecom.WeCom.check({"bot_id": " bot_1 ", "secret": " s ", "name": "Trợ lý"})
    assert info == {"name": "Trợ lý", "config": {"bot_id": "bot_1"}, "secret": "s"}
    [frame] = ws.sent
    assert frame["cmd"] == "aibot_subscribe" and frame["body"] == {"bot_id": "bot_1", "secret": "s"}
    assert frame["headers"]["req_id"].startswith("aibot_subscribe_")


async def test_check_explains_what_is_wrong(monkeypatch):
    monkeypatch.setattr(wecom.websockets, "connect", lambda *a, **kw: SubWS({"errcode": 40001, "errmsg": "invalid secret"}))
    with pytest.raises(ValueError) as e:
        await wecom.WeCom.check({"bot_id": "bot_1", "secret": "s"})
    assert "invalid secret" in str(e.value) and "长连接" in str(e.value)

    with pytest.raises(ValueError) as e:
        await wecom.WeCom.check({"bot_id": "", "secret": "s"})
    assert "Bot ID" in str(e.value)

    def no_connect(*a, **kw):
        raise OSError("down")

    monkeypatch.setattr(wecom.websockets, "connect", no_connect)
    with pytest.raises(ValueError) as e:
        await wecom.WeCom.check({"bot_id": "bot_1", "secret": "s"})
    assert "连不上企业微信" in str(e.value)


def test_the_same_bot_is_recognised_by_its_bot_id():
    assert wecom.WeCom.same({"config": {"bot_id": "b"}}, {"config": {"bot_id": "b"}})
    assert not wecom.WeCom.same({"config": {"bot_id": "b"}}, {"config": {"bot_id": "c"}})


# ---------- 回执 ----------
async def test_a_request_waits_for_the_ack_with_its_own_req_id(monkeypatch):
    c = channel(monkeypatch)
    c.ws.answers["aibot_send_msg"] = {"errcode": 0}
    await c.request("aibot_send_msg", {"chatid": "zhang", "msgtype": "markdown"})
    [frame] = c.ws.sent
    assert frame["cmd"] == "aibot_send_msg" and frame["body"]["chatid"] == "zhang"
    assert frame["headers"]["req_id"].startswith("aibot_send_msg_")
    assert c._acks == {}                       # 等到了就收起来

    c.ws.answers["aibot_send_msg"] = {"errcode": 93000, "errmsg": "chưa nói câu nào"}
    with pytest.raises(wecom.WecomError) as e:
        await c.request("aibot_send_msg", {})
    assert e.value.code == 93000 and "chưa nói" in e.value.msg


async def test_a_request_without_a_connection_says_so(monkeypatch):
    c = channel(monkeypatch, connected=False)
    with pytest.raises(ConnectionError):
        await c.request("aibot_send_msg", {})


async def test_an_ack_for_somebody_else_is_ignored(monkeypatch):
    c = channel(monkeypatch)
    assert await c._frame({"headers": {"req_id": "không-ai"}, "errcode": 0}) is None
    assert c._acks == {}


# ---------- 收 ----------
def _msg(**kw):
    return {"msgid": "m1", "chattype": "single", "from": {"userid": "zhang"}, "msgtype": "text",
            "text": {"content": "chào"}, **kw}


async def test_a_message_is_handled_once_even_if_it_is_resend(monkeypatch):
    c = channel(monkeypatch)
    await c._frame({"cmd": "aibot_msg_callback", "headers": {"req_id": "r1"}, "body": _msg()})
    await asyncio.sleep(0)
    await c._frame({"cmd": "aibot_msg_callback", "headers": {"req_id": "r2"}, "body": _msg()})
    await asyncio.sleep(0)
    assert [m["text"] for m in c.inbox] == ["chào"]
    await c._frame({"cmd": "aibot_msg_callback", "headers": {}, "body": _msg(msgid="m2", chattype="group")})
    await asyncio.sleep(0)
    assert len(c.inbox) == 1                  # 群里发的不收


async def test_a_mixed_message_keeps_the_text_and_the_pictures(monkeypatch):
    c = channel(monkeypatch)
    await c._frame({"cmd": "aibot_msg_callback", "body": _msg(msgid="m3", msgtype="mixed", mixed={"msg_item": [
        {"msgtype": "text", "text": {"content": "xem hai cái này"}},
        {"msgtype": "image", "image": {"url": "https://d/1", "aeskey": "k"}}]})})
    await asyncio.sleep(0)
    m = c.inbox[0]
    assert m["text"] == "xem hai cái này" and m["files"][0][1] == {"url": "https://d/1", "aeskey": "k"}


async def test_a_voice_message_without_words_asks_again(monkeypatch):
    c = channel(monkeypatch)
    await c._frame({"cmd": "aibot_msg_callback", "body": _msg(msgtype="voice", voice={"content": ""})})
    await asyncio.sleep(0)
    assert c.inbox == [] and "没听清这条语音" in c.said[0]


# ---------- 发 ----------
def card(**kw):
    return {"id": 12, "title": "允许吗", "body": "**git push** lên nhánh chính",
            "buttons": [("允许", "ok", "primary"), ("拒绝", "no", "danger")], **kw}


async def test_a_card_is_a_button_interaction_card(monkeypatch):
    c = channel(monkeypatch)
    task_id = await c.send_card("zhang", card(link=("看看", "https://example.com/diff")))
    assert task_id.startswith(f"osa{c.id}_12_")

    body = c.ws.sent[-1]["body"]
    assert body["msgtype"] == "template_card"
    tc = body["template_card"]
    assert tc["card_type"] == "button_interaction" and tc["task_id"] == task_id
    assert tc["main_title"] == {"title": "允许吗", "desc": "#12"}
    assert [b["key"] for b in tc["button_list"]] == ["ap:12:ok", "ap:12:no"]
    assert tc["card_action"] == {"type": 1, "url": "https://example.com/diff"}


async def test_a_long_card_comes_as_text_first(monkeypatch):
    c = channel(monkeypatch)
    await c.send_card("zhang", card(body="dài " * 200))
    assert c.ws.sent[0]["body"]["msgtype"] == "markdown"    # 详细内容先单独发一条
    assert c.ws.sent[1]["body"]["msgtype"] == "template_card"


async def test_a_card_that_cannot_be_sent_falls_back_to_text(monkeypatch):
    c = channel(monkeypatch)
    c.ws.answers["aibot_send_msg"] = [{"errcode": 93000, "errmsg": "no card"}, {"errcode": 0}]   # 卡片不成，文字成
    assert await c.send_card("zhang", card()) == ""
    assert "允许一次 #12" in c.ws.sent[-1]["body"]["markdown"]["content"]


async def test_a_button_press_updates_the_card_within_five_seconds(monkeypatch):
    c = channel(monkeypatch)
    c._press = lambda peer, data: _ok()
    await c._frame({"cmd": "aibot_event_callback", "headers": {"req_id": "ev-1"},
                    "body": {"event": {"eventtype": "template_card_event", "task_id": "t1",
                                       "event_key": "ap:12:ok"}, "from": {"userid": "zhang"}}})
    await asyncio.sleep(0)
    await c.edit_card("zhang", "t1", card(done="✓ 已允许"))
    [update] = [f for f in c.ws.sent if f["cmd"] == "aibot_respond_update_msg"]
    assert update["headers"]["req_id"] == "ev-1"                     # 用点按钮那个事件的 req_id
    assert update["body"]["template_card"]["button_list"][0]["key"] == "ap:12:over"

    c._events["t1"] = ("ev-1", time.time() - 10)                    # 超过 5 秒：改不了，发一条
    await c.edit_card("zhang", "t1", card(done="✓ 已允许"))
    assert c.ws.sent[-1]["body"]["msgtype"] == "markdown" and "已允许" in c.ws.sent[-1]["body"]["markdown"]["content"]


async def _ok():
    return True, "ok"


async def test_a_press_from_someone_else_is_told_why(monkeypatch):
    c = channel(monkeypatch)

    async def nope(peer, data):
        return False, "没有权限"

    c._press = nope
    await c._frame({"cmd": "aibot_event_callback", "headers": {"req_id": "ev-2"},
                    "body": {"event": {"eventtype": "template_card_event", "task_id": "t2", "event_key": "ap:12:ok"},
                             "from": {"userid": "lạ"}}})
    await asyncio.sleep(0)
    assert c.said == ["没有权限"] and "t2" not in c._events


# ---------- 连接 ----------
async def test_a_kicked_bot_is_reported(monkeypatch):
    c = channel(monkeypatch)
    assert await c._frame({"cmd": "aibot_event_callback",
                           "body": {"event": {"eventtype": "disconnected_event"}}}) == "kicked"


async def test_two_missed_acks_close_the_connection(monkeypatch):
    c = channel(monkeypatch)
    task = asyncio.create_task(c._ping(c.ws))
    monkeypatch.setattr(wecom, "PING_EVERY", 0)
    c._missed = 1
    await asyncio.sleep(0.05)
    await asyncio.sleep(0.05)
    assert c.ws.closed and task.done()

    c2 = channel(monkeypatch)
    c2.ws.answers["ping"] = None              # 没回执
    monkeypatch.setattr(wecom, "PING_EVERY", 1)
    task2 = asyncio.create_task(c2._ping(c2.ws))
    await c2._frame({"headers": {"req_id": "ping_1"}})     # 回执到了：_missed 归零
    task2.cancel()


# ---------- 下载 ----------
def sealed(data: bytes, key: bytes) -> bytes:
    """按企业微信的规矩封起来：AES-256-CBC，IV 是密钥前 16 字节，PKCS#7 按 32 字节补。"""
    pad = 32 - len(data) % 32
    enc = Cipher(algorithms.AES(key), modes.CBC(key[:16])).encryptor()
    return enc.update(data + bytes([pad]) * pad) + enc.finalize()


async def test_a_file_is_downloaded_and_decrypted(monkeypatch):
    key = os.urandom(32)
    fake = FakeHTTP({"/f/1": httpx.Response(200, content=sealed("xin chào".encode(), key), headers={
        "content-disposition": "attachment; filename*=UTF-8''b%C3%A1o%20c%C3%A1o.pdf"})})
    c = channel(monkeypatch, fake)

    data, name = await c.download({"url": "https://d/f/1", "aeskey": base64.b64encode(key).decode()})

    assert data == "xin chào".encode() and name == "báo cáo.pdf"


async def test_a_file_without_a_key_is_saved_as_it_comes(monkeypatch):
    fake = FakeHTTP({"/f/2": httpx.Response(200, content=b"plain", headers={"content-disposition": 'filename="a.txt"'})})
    c = channel(monkeypatch, fake)
    assert await c.download({"url": "https://d/f/2"}) == (b"plain", "a.txt")


async def test_a_file_that_will_not_decrypt_says_so(monkeypatch):
    fake = FakeHTTP({"/f/3": httpx.Response(200, content="rác".encode())})
    c = channel(monkeypatch, fake)
    with pytest.raises(ValueError) as e:
        await c.download({"url": "https://d/f/3", "aeskey": base64.b64encode(os.urandom(32)).decode()})
    assert "解密" in str(e.value)
