"""Một Bot có thể có hơn một cuộc trò chuyện riêng (script, hoặc sau này là “chủ đề mới”) — cái nào là của Bot, và tên hiển thị.

Hiện trường 11/11: màn hình có **hai** “Nova”. Không phải hai Bot (bảng bots chỉ có một dòng id 1),
mà là hai cuộc trò chuyện riêng cùng trỏ bot 1: “Nova” và “scratch-nova” (một lượt trước tự chèn vào DB để đo trên một
cuộc trò chuyện yên tĩnh). Hai lỗi thật lộ ra từ đó:

1. `bots._bot()` chọn cuộc trò chuyện bằng `select ... where bot_ids=?` **không có order by** — có hai cái
   thì “cuộc trò chuyện của Bot” là cái nào tuỳ sqlite, bấm vào Bot có thể rơi vào cuộc trò chuyện test.
2. Đổi tên Bot ghi đè **mọi** cuộc trò chuyện riêng của nó, xoá mất cái tên người dùng đã đặt.

Phía giao diện: `web/src/chatLabel.ts` (test: `web/tests/chat-label.cjs`).
"""
import json

from osa import bots, memory


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
