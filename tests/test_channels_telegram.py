"""B8: the Telegram adapter on its own. No real network: an httpx MockTransport answers for api.telegram.org.

Covered: connecting with a token, what a bad token looks like to the user, the pair link, markdown -> Telegram HTML
with the plain-text fallback, long replies split, confirmation cards (inline buttons, edits), typing, file download,
the polling loop surviving a 429 and honouring the update offset (so the same update is not handled twice).
"""
import asyncio
import json
import time

import httpx
import pytest

from osa import channels
from osa.channels import telegram
from osa.memory import conn

TOKEN = "123456789:AAH-abcdefghijklmnopqrstuvwxyz"


class Api:
    """A fake Bot API: reply(method, params) decides what comes back, every call is recorded."""

    def __init__(self, reply=None):
        self.calls: list[tuple[str, dict]] = []
        self.reply = reply or (lambda method, params: {"ok": True, "result": True})

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path                      # /bot<token>/<method> or /file/bot<token>/<path>
        params = json.loads(request.content or b"{}")
        if path.startswith("/file/"):
            self.calls.append(("file", {"url": str(request.url)}))
            return httpx.Response(200, content=b"%PDF-1.4 test")
        method = path.rsplit("/", 1)[-1]
        self.calls.append((method, params))
        return httpx.Response(200, json=self.reply(method, params))

    def methods(self) -> list[str]:
        return [m for m, _ in self.calls]

    def last(self, method: str) -> dict:
        return [p for m, p in self.calls if m == method][-1]


@pytest.fixture
def api(monkeypatch):
    box = Api()
    real = httpx.AsyncClient
    monkeypatch.setattr(telegram.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(box.handler), **kw))
    return box


@pytest.fixture
def clean():
    conn.execute("delete from channels")
    conn.commit()
    yield
    conn.execute("delete from channels")
    conn.commit()
    channels.RUNNING.clear()


def row(**kw) -> dict:
    """A channel row as the database gives it (paired unless told otherwise)."""
    now = time.time()
    base = {"id": 1, "kind": "telegram", "name": "@osa_bot", "config": {"username": "osa_bot", "bot_id": 42},
            "chat_id": 7, "peer": "900", "peer_name": "An", "pair_code": "", "pair_expires": now + 600,
            "pair_fails": 0, "enabled": 1, "created": now}
    return {**base, **kw}


def keep(r: dict) -> dict:
    """Put the row in the database (the channel re-reads it from there)."""
    conn.execute("insert or replace into channels(id, kind, name, config, chat_id, peer, peer_name, pair_code, "
                 "pair_expires, pair_fails, enabled, created) values(?,?,?,?,?,?,?,?,?,?,?,?)",
                 (r["id"], r["kind"], r["name"], json.dumps(r["config"]), r["chat_id"], r["peer"], r["peer_name"],
                  r["pair_code"], r["pair_expires"], r["pair_fails"], r["enabled"], r["created"]))
    conn.commit()
    return r


# ---------- connecting ----------
async def test_a_good_token_brings_back_the_bot(api, clean):
    api.reply = lambda m, p: ({"ok": True, "result": {"id": 42, "username": "osa_bot", "is_bot": True}}
                              if m == "getMe" else {"ok": True, "result": True})
    info = await telegram.Telegram.check({"token": " " + TOKEN + " "})
    assert info["name"] == "@osa_bot" and info["secret"] == TOKEN
    assert info["config"] == {"username": "osa_bot", "bot_id": 42}
    assert api.methods() == ["getMe"]


async def test_a_token_that_is_not_a_token_is_caught_before_any_call(api, clean):
    with pytest.raises(ValueError, match="@BotFather"):
        await telegram.Telegram.check({"token": "hello"})
    assert api.calls == []


async def test_a_revoked_token_says_so(api, clean):
    api.reply = lambda m, p: {"ok": False, "error_code": 401, "description": "Unauthorized"}
    with pytest.raises(ValueError, match="已经被删除"):
        await telegram.Telegram.check({"token": TOKEN})


async def test_no_connection_points_at_the_proxy_setting(clean, monkeypatch):
    def boom(request):
        raise httpx.ConnectError("no route", request=request)
    real = httpx.AsyncClient
    monkeypatch.setattr(telegram.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(boom), **kw))
    with pytest.raises(ValueError, match="HTTPS_PROXY"):
        await telegram.Telegram.check({"token": TOKEN})


def test_the_pair_link_opens_the_bot_with_the_code(clean):
    assert telegram.Telegram.pair_link(row(pair_code="123456")) == "https://t.me/osa_bot?start=123456"


def test_same_account_is_recognised_by_bot_id(clean):
    me = {"config": {"username": "osa_bot", "bot_id": 42}, "secret": TOKEN}
    assert telegram.Telegram.same(row(), me)
    assert not telegram.Telegram.same(row(config={"username": "other", "bot_id": 43}), me)


# ---------- sending ----------
async def test_text_is_sent_as_telegram_html(api, clean):
    tg = telegram.Telegram(row(), TOKEN)
    try:
        await tg.send_text("900", "**bold** and `code` and [link](https://example.com)")
    finally:
        await tg.aclose()
    sent = api.last("sendMessage")
    assert sent["chat_id"] == "900" and sent["parse_mode"] == "HTML"
    assert "<b>bold</b>" in sent["text"] and "<code>code</code>" in sent["text"]
    assert '<a href="https://example.com">link</a>' in sent["text"]
    assert sent["link_preview_options"] == {"is_disabled": True}


async def test_html_telegram_cannot_parse_falls_back_to_plain_text(api, clean):
    def reply(method, params):
        if method == "sendMessage" and "parse_mode" in params:
            return {"ok": False, "error_code": 400, "description": "Bad Request: can't parse entities"}
        return {"ok": True, "result": {"message_id": 11}}
    api.reply = reply
    tg = telegram.Telegram(row(), TOKEN)
    try:
        await tg.send_text("900", "**bold** but broken <tag>")
    finally:
        await tg.aclose()
    first, second = [p for m, p in api.calls if m == "sendMessage"]
    assert "parse_mode" in first and "parse_mode" not in second
    assert "**" not in second["text"] and "bold" in second["text"]   # 退成纯文本：不再是 Markdown


async def test_a_long_reply_is_split_into_several_messages(api, clean):
    api.reply = lambda m, p: {"ok": True, "result": {"message_id": 1}}
    tg = telegram.Telegram(row(), TOKEN)
    try:
        await tg._send_md("900", "x" * 5000)
    finally:
        await tg.aclose()
    parts = [p["text"] for m, p in api.calls if m == "sendMessage"]
    assert len(parts) == 2 and all(len(x) <= telegram.Telegram.max_len for x in parts)
    assert "".join(parts) == "x" * 5000      # nothing lost


async def test_a_card_gets_buttons_that_carry_the_approval(api, clean):
    api.reply = lambda m, p: {"ok": True, "result": {"message_id": 77}}
    tg = telegram.Telegram(row(), TOKEN)
    card = {"id": 12, "title": "Run <ls>", "body": "**computer_shell**\n`ls -la`", "done": "",
            "buttons": [("Allow", "ok", ""), ("No", "no", "")], "link": ("Open", "https://example.com")}
    try:
        mid = await tg.send_card("900", card)
        await tg.edit_card("900", mid, card | {"done": "Done"})
    finally:
        await tg.aclose()
    assert mid == "77"
    sent = api.last("sendMessage")
    rows = sent["reply_markup"]["inline_keyboard"]
    assert [b["callback_data"] for b in rows[0]] == ["ap:12:ok", "ap:12:no"]
    assert rows[1] == [{"text": "Open", "url": "https://example.com"}]
    assert "&lt;ls&gt;" in sent["text"]
    edit = api.last("editMessageText")
    assert edit["message_id"] == 77 and "Done" in edit["text"]


async def test_editing_to_the_same_card_is_not_an_error(api, clean):
    api.reply = lambda m, p: ({"ok": False, "error_code": 400, "description": "Bad Request: message is not modified"}
                              if m == "editMessageText" else {"ok": True, "result": {"message_id": 5}})
    tg = telegram.Telegram(row(), TOKEN)
    try:
        await tg.edit_card("900", "5", {"id": 3, "title": "T", "body": "B", "done": "", "buttons": []})
    finally:
        await tg.aclose()


async def test_typing_and_downloading_a_file(api, clean):
    api.reply = lambda m, p: {"ok": True, "result": {"file_path": "documents/a.pdf", "file_size": 12}}
    tg = telegram.Telegram(row(), TOKEN)
    try:
        await tg.typing("900")
        data = await tg.download("FILE123")
    finally:
        await tg.aclose()
    assert api.last("sendChatAction") == {"chat_id": "900", "action": "typing"}
    assert api.last("getFile") == {"file_id": "FILE123"}
    assert data == b"%PDF-1.4 test"
    assert api.calls[-1][1]["url"].endswith(f"/file/bot{TOKEN}/documents/a.pdf")


async def test_a_file_too_big_for_the_bot_api_is_refused_early(api, clean):
    api.reply = lambda m, p: {"ok": True, "result": {"file_path": "big.zip", "file_size": telegram.MAX_FILE + 1}}
    tg = telegram.Telegram(row(), TOKEN)
    try:
        with pytest.raises(ValueError, match="20 MB"):
            await tg.download("BIG")
    finally:
        await tg.aclose()
    assert "file" not in api.methods()


# ---------- receiving ----------
async def test_only_private_messages_get_in(api, clean):
    tg = telegram.Telegram(keep(row()), TOKEN)
    seen = []

    async def inbound(peer, who, text, files=(), ref=None):
        seen.append((peer, who, text, files))
    tg.inbound = inbound
    try:
        await tg.on_update({"update_id": 1, "message": {"message_id": 3, "chat": {"id": 900, "type": "group"}, "text": "hi"}})
        await tg.on_update({"update_id": 2, "message": {"message_id": 4, "chat": {"id": 900, "type": "private"},
                                                        "from": {"first_name": "An"}, "text": "hi"}})
    finally:
        await tg.aclose()
    assert seen == [("900", "An", "hi", [])]


async def test_a_photo_comes_with_a_name_and_the_biggest_size(api, clean):
    tg = telegram.Telegram(keep(row()), TOKEN)
    seen = []

    async def inbound(peer, who, text, files=(), ref=None):
        seen.append((text, files))
    tg.inbound = inbound
    try:
        await tg.on_update({"update_id": 3, "message": {"message_id": 9, "chat": {"id": 900, "type": "private"},
                                                        "from": {"first_name": "An"}, "caption": "look",
                                                        "photo": [{"file_id": "small"}, {"file_id": "big"}]}})
    finally:
        await tg.aclose()
    assert seen == [("look", [("photo_9.jpg", "big")])]


async def test_a_button_press_is_answered(api, clean):
    tg = telegram.Telegram(keep(row()), TOKEN)
    pressed = []

    async def press(peer, data):
        pressed.append((peer, data))
        return "allowed"
    tg.press = press
    try:
        await tg.on_update({"update_id": 4, "callback_query": {"id": "cb1", "data": "ap:12:ok",
                                                               "message": {"chat": {"id": 900}}}})
    finally:
        await tg.aclose()
    assert pressed == [("900", "ap:12:ok")]
    assert api.last("answerCallbackQuery") == {"callback_query_id": "cb1", "text": "allowed"}


# ---------- the polling loop ----------
async def test_a_rate_limit_is_handled_the_way_telegram_asks(api, clean):
    """429 + retry_after：TgError 带上它说的秒数，轮询循环照着等（不是自己拍脑袋的重试间隔）。"""
    api.reply = lambda m, p: {"ok": False, "error_code": 429, "description": "Too Many Requests",
                              "parameters": {"retry_after": 7}}
    tg = telegram.Telegram(row(), TOKEN)
    try:
        with pytest.raises(telegram.TgError) as e:
            await tg.call("getUpdates")
    finally:
        await tg.aclose()
    assert e.value.code == 429 and e.value.retry == 7


async def test_the_poller_asks_for_the_next_update_and_its_own_commands(api, clean):
    """长轮询第一件事：清掉 webhook、登记 /new /stop /help，然后从 offset 往下问——
    正是这个 offset 让同一个 update 不会被处理两次。"""
    api.reply = lambda m, p: ({"ok": True, "result": [{"update_id": 5}]} if m == "getUpdates" and "offset" not in p
                              else {"ok": True, "result": True})
    tg = telegram.Telegram(row(), TOKEN)
    try:
        await tg.call("deleteWebhook")
        await tg.call("setMyCommands", commands=[{"command": "new", "description": "x"}])
        ups = await tg.call("getUpdates", offset=None, timeout=50, allowed_updates=["message", "callback_query"])
        assert ups and ups[0]["update_id"] == 5
        await tg.call("getUpdates", offset=ups[0]["update_id"] + 1)
    finally:
        await tg.aclose()
    assert api.methods()[:2] == ["deleteWebhook", "setMyCommands"]
    polls = [p for m, p in api.calls if m == "getUpdates"]
    assert "offset" not in polls[0] and polls[-1]["offset"] == 6


async def test_updates_are_handled_one_after_another(api, clean):
    tg = telegram.Telegram(keep(row()), TOKEN)
    seen = []

    async def on_update(u):
        seen.append(u["update_id"])
    tg.on_update = on_update
    try:
        for u in ({"update_id": 1, "message": {"message_id": 1, "chat": {"id": 900, "type": "private"}, "text": "a"}},
                  {"update_id": 2, "message": {"message_id": 2, "chat": {"id": 900, "type": "private"}, "text": "b"}}):
            await tg.on_update(u)
    finally:
        await tg.aclose()
    assert seen == [1, 2]


async def test_a_wrong_pair_code_counts_then_the_right_one_pairs(api, clean, make_bot):
    """Pairing: a wrong code is remembered as a failure, the right one makes this chat the owner."""
    chat = make_bot("PairBot")
    tg = telegram.Telegram(keep(row(peer="", peer_name="", pair_code="123456", chat_id=chat["chat_id"])), TOKEN)
    api.reply = lambda m, p: {"ok": True, "result": {"message_id": 1}}
    try:
        await tg.inbound("900", "An", "000000")
        failed = channels.row(1)
        await tg.inbound("900", "An", "ma cua toi: 123456")
        got = channels.row(1)
    finally:
        await tg.aclose()
    assert failed["pair_fails"] == 1 and failed["peer"] == ""
    assert got["peer"] == "900" and got["peer_name"] == "An" and got["pair_code"] == ""
    assert got["pair_fails"] == 0


async def test_the_poller_does_not_starve_the_event_loop(api, clean):
    """getUpdates 立刻返回（代理、测试里的假 API）时也要让出一下：不然 run() 会把事件循环占死，
    同一个进程里的别的任务（对话、心跳、别的聊天软件）全都停住。"""
    api.reply = lambda method, params: {"ok": True, "result": []}
    t = telegram.Telegram(row(), "secret-" + TOKEN)
    task = asyncio.create_task(t.run())
    try:
        await asyncio.wait_for(asyncio.sleep(0.05), 1)   # 能睡得着就说明没被占死
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert api.methods().count("getUpdates") > 1
