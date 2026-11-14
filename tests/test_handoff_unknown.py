"""C56b: handoff tới tên không có trong nhóm thì trả danh sách thành viên, không im lặng."""
import asyncio
from osa import bots, router


def test_an_unknown_name_returns_the_member_list(make_bot):
    a = make_bot("Lead")
    b = make_bot("Other")
    chat = bots.create_group([a["id"], b["id"]], "R", lead=a["id"])
    try:
        r = router.runtime(a["id"])
        r.chat = bots.chat(chat["id"])
        r._turn_outputs, r._turn_tasks, r._turn_tool_ms = [], [], []
        out = asyncio.run(router.Router._tool(r, "handoff", {"bot": "Nobody", "note": "x"}))
        assert "Other" in out and "Nobody" in out
    finally:
        bots.delete_chat(chat["id"]); bots.delete(a["id"]); bots.delete(b["id"])
