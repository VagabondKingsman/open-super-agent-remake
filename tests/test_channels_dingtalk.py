"""钉钉适配器：配对、token 缓存与 401 换新、sessionWebhook 回落 OpenAPI、按 msgId 去重、
卡片是 dtmd:// 链接、帧先回包再处理、下载。

不连真的钉钉：HTTP 走 httpx.MockTransport，长连接用一个假的 ws 对象。
"""
import json
import time
from urllib.parse import quote, unquote, urlparse, parse_qs

import httpx
import pytest

from osa.channels import dingtalk


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
        if request.url.path in self.files:
            return httpx.Response(200, content=self.files[request.url.path])
        raise AssertionError(f"没有准备 {request.method} {request.url.path}")

    def calls(self, path: str) -> list[dict]:
        return [b for m, p, b in self.seen if p == path]


REAL_CLIENT = httpx.AsyncClient
TOKEN = "/v1.0/oauth2/accessToken"
GATEWAY = "/v1.0/gateway/connections/open"
SEND = "/v1.0/robot/oToMessages/batchSend"
DOWNLOAD = "/v1.0/robot/messageFiles/download"


@pytest.fixture(autouse=True)
def no_api_prefix(monkeypatch):
    """换成一个假的域名：请求不出网，MockTransport 按 path 认。"""
    monkeypatch.setattr(dingtalk, "API", "https://api.dingtalk.test")


def patch(monkeypatch, fake: FakeHTTP):
    monkeypatch.setattr(dingtalk.httpx, "AsyncClient",
                        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(fake),
                                                 **{k: v for k, v in kw.items() if k != "transport"}))


def channel(monkeypatch, fake: FakeHTTP, *, peer="staff_1", exp=time.time() + 3600):
    patch(monkeypatch, fake)
    row = {"id": 9, "kind": "dingtalk", "name": "Robot", "config": {"app_key": "ding_abc"}, "chat_id": 1,
           "peer": peer, "peer_name": "An", "pair_code": "", "pair_expires": exp, "pair_fails": 0,
           "enabled": 1, "created": 0}
    c = dingtalk.DingTalk(row, "secret")
    c.said, c.pressed, c.inbox = [], [], []

    def say(md, peer=None):
        c.said.append(md)

    async def press(peer, data):
        c.pressed.append((peer, data))
        return "ok"

    async def inbound(peer, name, text, files):
        c.inbox.append({"peer": peer, "name": name, "text": text, "files": files})

    c.say, c.press, c.inbound = say, press, inbound
    return c


def ok_token(monkeypatch, fake=None, token="t-1", expire=7200):
    (fake or FakeHTTP()).routes.setdefault(("POST", TOKEN), {"accessToken": token, "expireIn": expire})


# ---------- 配对 ----------
async def test_check_takes_the_app_and_names_it(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t", "expireIn": 7200}})
    patch(monkeypatch, fake)
    info = await dingtalk.DingTalk.check({"app_key": " ding_abc ", "app_secret": " s ", "name": "Trợ lý"})
    assert info == {"name": "Trợ lý", "config": {"app_key": "ding_abc"}, "secret": "s"}
    assert fake.calls(TOKEN) == [{"appKey": "ding_abc", "appSecret": "s"}]
    assert await dingtalk.DingTalk.check({"app_key": "ding_abc", "app_secret": "s"}) == \
        {"name": "ding_abc", "config": {"app_key": "ding_abc"}, "secret": "s"}   # 没填名字就用 AppKey


async def test_check_explains_what_is_wrong(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): httpx.Response(400, json={"code": "invalidClientIdOrSecret",
                                                               "message": "ClientId or Secret is invalid"})})
    patch(monkeypatch, fake)
    with pytest.raises(ValueError) as e:
        await dingtalk.DingTalk.check({"app_key": "ding_abc", "app_secret": "s"})
    assert "ClientId or Secret is invalid" in str(e.value)

    with pytest.raises(ValueError) as e:
        await dingtalk.DingTalk.check({"app_key": "", "app_secret": "s"})
    assert "Client ID" in str(e.value) and "AppSecret" in str(e.value)

    def broken(request):
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(dingtalk.httpx, "AsyncClient", lambda **kw: REAL_CLIENT(
        transport=httpx.MockTransport(broken), **{k: v for k, v in kw.items() if k != "transport"}))
    with pytest.raises(ValueError) as e:
        await dingtalk.DingTalk.check({"app_key": "ding_abc", "app_secret": "s"})
    assert "连不上钉钉" in str(e.value)


def test_the_same_app_is_recognised_by_its_app_key():
    row = {"config": {"app_key": "ding_abc"}}
    assert dingtalk.DingTalk.same(row, {"config": {"app_key": "ding_abc"}})
    assert not dingtalk.DingTalk.same(row, {"config": {"app_key": "ding_other"}})


# ---------- token ----------
async def test_the_token_is_kept_and_renewed_only_when_it_is_about_to_expire(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t-1", "expireIn": 7200},
                      ("POST", SEND): {"invalidStaffIdList": [], "flowControlledStaffIdList": []}})
    c = channel(monkeypatch, fake)
    await c.send_text("staff_1", "một")
    await c.send_text("staff_1", "hai")
    assert len(fake.calls(TOKEN)) == 1                 # 两次发消息只换一次 token
    assert len(fake.calls(SEND)) == 2

    c._token_exp = time.time() + 10                   # 快过期了：提前换
    await c.send_text("staff_1", "ba")
    assert len(fake.calls(TOKEN)) == 2


async def test_a_401_gets_a_new_token_once(monkeypatch):
    answers = [httpx.Response(401, json={"code": "InvalidAuthentication", "message": "token expired"}),
               {"invalidStaffIdList": [], "flowControlledStaffIdList": []}]
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t-1", "expireIn": 7200},
                      ("POST", SEND): lambda: answers.pop(0)})
    c = channel(monkeypatch, fake)
    await c.send_text("staff_1", "một")
    assert len(fake.calls(TOKEN)) == 2 and len(fake.calls(SEND)) == 2

    fake.routes[("POST", SEND)] = httpx.Response(403, json={"code": "Forbidden", "message": "bị chặn"})
    with pytest.raises(dingtalk.DingError) as e:
        await c.send_text("staff_1", "hai")
    assert e.value.status == 403


# ---------- 收 ----------
def _msg(**kw):
    m = {"msgId": "msg-1", "conversationType": "1", "senderStaffId": "staff_1", "senderNick": "An",
         "msgtype": "text", "text": {"content": "chào"}, "robotCode": "ding_robot"}
    return {**m, **kw}


async def test_a_message_arrives_once_and_only_from_a_private_chat(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    await c.on_message(_msg())
    await c.on_message(_msg())                                   # 钉钉回包没送到，重推一次
    assert [m["text"] for m in c.inbox] == ["chào"]
    await c.on_message(_msg(msgId="msg-2", conversationType="2"))   # 群里发的：不理
    assert len(c.inbox) == 1
    await c.on_message(_msg(msgId="msg-3", senderStaffId="staff_2", text={"content": "hí"}))
    assert c.inbox[-1]["peer"] == "staff_2"                      # 别人发的也收，配对由 inbound 决定


async def test_a_voice_message_without_words_asks_again(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    await c.on_message(_msg(msgtype="audio", content={"recognition": ""}))
    assert c.inbox == [] and "没听清这条语音" in c.said[0]
    await c.on_message(_msg(msgId="m2", msgtype="audio", content={"recognition": "mở cửa"}))
    assert c.inbox[-1]["text"] == "mở cửa"


async def test_pictures_and_files_become_attachments(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    await c.on_message(_msg(msgtype="picture", content={"downloadCode": "dc-1"}))
    await c.on_message(_msg(msgId="m2", msgtype="file", content={"fileName": "báo cáo.pdf", "downloadCode": "dc-2"}))
    await c.on_message(_msg(msgId="m3", msgtype="richText", content={"richText": [
        {"text": "xem này "}, {"downloadCode": "dc-3"}]}))
    assert [f for m in c.inbox for f in m["files"]][0][0].startswith("image_")
    assert c.inbox[1]["files"] == [("báo cáo.pdf", "dc-2")]
    assert c.inbox[2]["text"] == "xem này " and c.inbox[2]["files"][0][1] == "dc-3"


# ---------- 发 ----------
async def test_a_reply_rides_the_session_webhook_while_it_lasts(monkeypatch):
    fake = FakeHTTP({("POST", "/robot/sendBySession"): {"errcode": 0}})
    c = channel(monkeypatch, fake)
    await c.on_message(_msg(sessionWebhook="https://oapi.dingtalk.com/robot/sendBySession?session=abc",
                            sessionWebhookExpiredTime=int((time.time() + 3600) * 1000)))
    await c.send_text("staff_1", "**xong** rồi")

    body = fake.calls("/robot/sendBySession")[0]
    assert body["msgtype"] == "markdown" and "xong" in body["markdown"]["text"]
    assert fake.calls(SEND) == []                        # 不用 OpenAPI，也就不需要权限


async def test_an_expired_webhook_falls_back_to_the_open_api(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t-1", "expireIn": 7200},
                      ("POST", SEND): {"invalidStaffIdList": [], "flowControlledStaffIdList": []}})
    c = channel(monkeypatch, fake)
    c._webhooks["staff_1"] = ("https://oapi.dingtalk.com/robot/sendBySession?session=abc", time.time() - 10)
    await c.on_message(_msg(robotCode="ding_robot_2"))
    await c.send_text("staff_1", "kết quả")

    body = fake.calls(SEND)[0]
    assert body["robotCode"] == "ding_robot_2" and body["userIds"] == ["staff_1"]
    assert body["msgKey"] == "sampleMarkdown"
    assert "kết quả" in json.loads(body["msgParam"])["text"]


async def test_the_open_api_saying_nobody_accepted_is_an_error(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t-1", "expireIn": 7200},
                      ("POST", SEND): {"invalidStaffIdList": ["staff_1"]}})
    c = channel(monkeypatch, fake)
    with pytest.raises(dingtalk.DingError) as e:
        await c.send_text("staff_1", "kết quả")
    assert "钉钉没发出去" in str(e.value)


async def test_a_card_is_a_markdown_with_links_that_send_the_command(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t-1", "expireIn": 7200},
                      ("POST", SEND): {"invalidStaffIdList": []}})
    c = channel(monkeypatch, fake)
    card = {"id": 12, "title": "允许吗", "body": "**git push**",
            "buttons": [("允许", "ok", "primary"), ("拒绝", "no", "danger")],
            "link": ("看看", "https://example.com/diff")}
    assert await c.send_card("staff_1", card) == ""       # 钉钉没有消息 id 可改

    text = json.loads(fake.calls(SEND)[0]["msgParam"])["text"]
    links = [t for t in text.split() if t.startswith("[")]
    assert len(links) == 3
    first = links[0].split("](")[1].rstrip(")")
    assert first.startswith("dtmd://dingtalkclient/sendMessage?content=")
    from osa.channels import word_command
    assert unquote(first.split("content=")[1]) == word_command("ok", 12)
    assert "https://example.com/diff" in text

    await c.edit_card("staff_1", "", {**card, "done": "✓ 已允许"})
    assert "已允许" in json.loads(fake.calls(SEND)[-1]["msgParam"])["text"]


# ---------- 长连接的帧 ----------
class FakeWS:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, raw):
        self.sent.append(json.loads(raw))


async def test_a_ping_is_answered_and_a_message_is_acknowledged_first(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    ws = FakeWS()

    await c._frame(ws, json.dumps({"type": "SYSTEM", "headers": {"topic": "ping", "messageId": "p1"},
                                   "data": "{}"}))
    assert ws.sent[0]["headers"]["messageId"] == "p1" and ws.sent[0]["code"] == 200

    await c._frame(ws, json.dumps({"type": "SYSTEM", "headers": {"topic": "disconnect", "messageId": "d1"}}))
    assert len(ws.sent) == 1                                    # 断开不用回，run 里重连

    await c._frame(ws, json.dumps({"type": "CALLBACK", "headers": {"messageId": "m1", "topic": dingtalk.TOPIC_MSG},
                                   "data": json.dumps(_msg())}))
    assert ws.sent[-1]["headers"]["messageId"] == "m1" and ws.sent[-1]["data"] == json.dumps({"response": None})
    assert [m["text"] for m in c.inbox] == ["chào"]             # 回包之后才处理


async def test_a_frame_that_is_not_for_the_bot_is_ignored(monkeypatch):
    c = channel(monkeypatch, FakeHTTP())
    ws = FakeWS()
    await c._frame(ws, json.dumps({"type": "CALLBACK", "headers": {"messageId": "m9", "topic": "/v1.0/other"},
                                   "data": "{}"}))
    assert len(ws.sent) == 1 and c.inbox == []


# ---------- 下载 ----------
async def test_a_file_is_downloaded_with_the_open_api(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t-1", "expireIn": 7200},
                      ("POST", DOWNLOAD): {"downloadUrl": "https://down.example/f/1"}})
    fake.files["/f/1"] = "nội dung".encode()
    c = channel(monkeypatch, fake)
    await c.on_message(_msg(msgtype="file", content={"downloadCode": "dc-9", "fileName": "a.pdf"}))
    assert await c.download("dc-9") == "nội dung".encode()
    assert fake.calls(DOWNLOAD)[0] == {"downloadCode": "dc-9", "robotCode": "ding_robot"}


async def test_a_download_dingtalk_refuses_is_explained(monkeypatch):
    fake = FakeHTTP({("POST", TOKEN): {"accessToken": "t-1", "expireIn": 7200},
                      ("POST", DOWNLOAD): httpx.Response(403, json={"code": "Forbidden", "message": "no permission"})})
    c = channel(monkeypatch, fake)
    with pytest.raises(ValueError) as e:
        await c.download("dc-9")
    assert "钉钉不让下载" in str(e.value) and "no permission" in str(e.value)
