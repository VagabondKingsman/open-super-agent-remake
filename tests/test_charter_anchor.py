"""C48: 阶段预授权与重锚。章程带阶段表；历史被裁或聊到第 8 个回答时，状态块末尾再锚一行。"""
from osa import charter, freedom
from osa.config import CFG


def test_the_charter_carries_precedence_and_phases(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    block = charter.block()
    assert "Precedence." in block and "reconnaissance" in block and "post-exploitation" in block
    assert "progress, not a new request to grant" in block


def test_anchor_fires_on_a_cut(monkeypatch, make_bot):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    bot = make_bot("Anchor")
    assert freedom.anchor(bot["chat_id"], cut=True) == charter.REANCHOR


def test_anchor_fires_every_eighth_answer(monkeypatch, make_bot):
    from osa import memory
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    bot = make_bot("Anchor8")
    have = memory.conn.execute("select count(*) from messages where chat_id=? and role='assistant'", (bot["chat_id"],)).fetchone()[0]
    for i in range((-have) % 8 or 8):
        memory.add("assistant", f"trả lời {i}", bot["chat_id"])
        if (have + i + 1) % 8:
            assert freedom.anchor(bot["chat_id"]) == ""
    assert freedom.anchor(bot["chat_id"]) == charter.REANCHOR
    memory.add("assistant", "chín", bot["chat_id"])
    assert freedom.anchor(bot["chat_id"]) == ""


def test_anchor_is_silent_when_off(monkeypatch, make_bot):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 0)
    bot = make_bot("AnchorOff")
    assert freedom.anchor(bot["chat_id"], cut=True) == ""
