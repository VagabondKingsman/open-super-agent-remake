"""Một Bot có thể có hơn một cuộc trò chuyện riêng (script, hoặc sau này là “chủ đề mới”) — cái nào là của Bot, và tên hiển thị.

Hiện trường 11/11: màn hình có **hai** “Nova”. Không phải hai Bot (bảng bots chỉ có một dòng id 1),
mà là hai cuộc trò chuyện riêng cùng trỏ bot 1: “Nova” và “scratch-nova” (một lượt trước tự chèn vào DB để đo trên một
cuộc trò chuyện yên tĩnh). Hai lỗi thật lộ ra từ đó:

1. `bots._bot()` chọn cuộc trò chuyện bằng `select ... where bot_ids=?` **không có order by** — có hai cái
   thì “cuộc trò chuyện của Bot” là cái nào tuỳ sqlite, bấm vào Bot có thể rơi vào cuộc trò chuyện test.
2. Đổi tên Bot ghi đè **mọi** cuộc trò chuyện riêng của nó, xoá mất cái tên người dùng đã đặt.

3. Không có đường nào để đổi tên hay xoá một cuộc trò chuyện riêng (PATCH/DELETE chỉ nhận group) — nên
   cái chat test tạo ra không dọn được, không đổi tên được. Nay PATCH nhận title của chat riêng, DELETE xoá
   được chat riêng **không phải** cái của Bot (cái của Bot đi cùng Bot).

Phía giao diện: `web/src/chatLabel.ts` (test: `web/tests/chat-label.cjs`).
"""
import json

import httpx

from osa import bots, memory, server


def _add_direct_chat(bot_id: int, title: str) -> int:
    cur = memory.conn.execute("insert into chats(kind, title, bot_ids, updated) values('direct', ?, ?, 0)",
                              (title, json.dumps([bot_id])))
    memory.conn.commit()
    return cur.lastrowid


def _drop_chat(chat_id: int):
    memory.conn.execute("delete from chats where id=?", (chat_id,))
    memory.conn.commit()


def test_bot_chat_is_the_oldest_direct_chat(make_bot):
    b = make_bot("Chon")
    first = b["chat_id"]
    second = _add_direct_chat(b["id"], "scratch")
    try:
        assert second > first
        assert bots.get(b["id"])["chat_id"] == first   # thêm một dòng sau đó không được đổi cuộc trò chuyện của Bot
        assert bots.chat(first)["bot_ids"] == [b["id"]]
    finally:
        _drop_chat(second)
        bots.delete(b["id"])


def test_rename_keeps_a_title_that_is_not_the_bot_name(make_bot):
    b = make_bot("Truoc")
    own = b["chat_id"]
    scratch = _add_direct_chat(b["id"], "scratch-ten")
    try:
        bots.update(b["id"], name="Sau")
        assert bots.chat(own)["title"] == "Sau"          # cuộc trò chuyện đi theo tên Bot vẫn đổi theo
        assert bots.chat(scratch)["title"] == "scratch-ten"   # 自己起过名的保留
    finally:
        _drop_chat(scratch)
        bots.delete(b["id"])


def http():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://127.0.0.1")


async def test_api_renames_a_direct_chat_and_clears_it_back_to_the_bot_name(make_bot):
    b = make_bot("DatTen")
    extra = _add_direct_chat(b["id"], "probe")
    try:
        async with http() as c:
            r = await c.patch(f"/api/chats/{extra}", json={"title": "việc riêng"})
            assert r.status_code == 200
            assert bots.chat(extra)["title"] == "việc riêng"
            # 空标题 = 跟着 Bot 的名字走（界面上就只剩 Bot 的名字）
            assert (await c.patch(f"/api/chats/{extra}", json={"title": "  "})).status_code == 200
            assert bots.chat(extra)["title"] == b["name"]
            # 群聊以外的成员/头像字段对私聊是空操作，不能把它改坏
            assert (await c.patch(f"/api/chats/{extra}", json={"bot_ids": [999]})).status_code == 200
            assert bots.chat(extra)["bot_ids"] == [b["id"]]
    finally:
        _drop_chat(extra)
        bots.delete(b["id"])


async def test_api_deletes_a_second_direct_chat_but_not_the_bot_own(make_bot):
    b = make_bot("Xoa")
    own = b["chat_id"]
    extra = _add_direct_chat(b["id"], "probe")
    try:
        async with http() as c:
            assert (await c.delete(f"/api/chats/{own}")).status_code == 400   # Bot 自己的那个：随 Bot
            assert bots.chat(own) is not None
            assert (await c.delete(f"/api/chats/{extra}")).status_code == 200
            assert bots.chat(extra) is None
            assert bots.get(b["id"])["chat_id"] == own   # 删掉另一个，不影响 Bot 的私聊
    finally:
        _drop_chat(extra)
        bots.delete(b["id"])


def test_rename_of_a_second_direct_chat_follows_the_old_name(make_bot):
    """Cái tên vừa được đổi lần trước cũng phải theo: 不改 thì lần đổi thứ hai để lại tên cũ."""
    b = make_bot("Mot")
    own = b["chat_id"]
    try:
        bots.update(b["id"], name="Hai")
        bots.update(b["id"], name="Ba")
        assert bots.chat(own)["title"] == "Ba"
    finally:
        bots.delete(b["id"])
