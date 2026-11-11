"""Menu của một Bot trên thanh bên: ẩn, đánh dấu chưa đọc, và số id không dùng lại.

Số id là số gán lúc tạo (`bots._next_id`), không phải một chuỗi ngẫu nhiên. Xoá rồi tạo lại không lấy lại số cũ.
"""
import httpx

from osa import bots, server


def http():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://127.0.0.1")


def test_new_bot_is_visible_and_keeps_its_id(make_bot):
    b = make_bot("Hien")
    try:
        assert b["hidden"] is False
        assert bots.get(b["id"])["id"] == b["id"]
        again = bots.update(b["id"], hidden=True)
        assert again["hidden"] is True
        assert bots.get(b["id"])["hidden"] is True
        assert bots.update(b["id"], hidden=False)["hidden"] is False
    finally:
        bots.delete(b["id"])


def test_unread_mark_roundtrip(make_bot):
    b = make_bot("ChuaDoc")
    try:
        assert bots.chat(b["chat_id"])["marked_unread"] is False
        marked = bots.set_unread_mark(b["chat_id"], True)
        assert marked["marked_unread"] is True
        assert bots.chat(b["chat_id"])["marked_unread"] is True
        assert bots.set_unread_mark(b["chat_id"], False)["marked_unread"] is False
    finally:
        bots.delete(b["id"])


async def test_api_hides_a_bot_and_marks_its_chat_unread(make_bot):
    b = make_bot("Menu")
    try:
        async with http() as c:
            r = await c.patch(f"/api/bots/{b['id']}", json={"hidden": True})
            assert r.status_code == 200 and r.json()["hidden"] is True
            # đổi tên không được làm mất cờ ẩn
            r = await c.patch(f"/api/bots/{b['id']}", json={"name": "Menu2"})
            assert r.status_code == 200 and r.json()["hidden"] is True and r.json()["name"] == "Menu2"
            r = await c.post(f"/api/chats/{b['chat_id']}/unread", json={"unread": True})
            assert r.status_code == 200 and r.json()["marked_unread"] is True
            r = await c.post(f"/api/chats/{b['chat_id']}/unread", json={"unread": False})
            assert r.status_code == 200 and r.json()["marked_unread"] is False
            assert (await c.post("/api/chats/999999/unread", json={"unread": True})).status_code == 400
    finally:
        bots.delete(b["id"])
