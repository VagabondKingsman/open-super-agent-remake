"""C46: 全开模式下新建的 Bot 生下来就带 mode 块，老的启动时补齐，块写一次就跟着 Bot 走（C46b）。

幂等：带块的不重复、关掉就不动。"""
import pytest

from osa import bots, freedom
from osa.config import CFG


@pytest.fixture
def restore_overrides():
    """settings.save() 真写库并 apply()（连电脑设置一起），跑完把 overrides 与 CFG 还原。"""
    from osa import settings
    from osa.memory import conn
    row = conn.execute("select value from settings where key='overrides'").fetchone()
    before = row[0] if row else None
    limits, computer = dict(CFG.get("limits") or {}), dict(CFG.get("computer") or {})
    yield
    if before is None:
        conn.execute("delete from settings where key='overrides'")
    else:
        conn.execute("insert or replace into settings values('overrides', ?)", (before,))
    conn.commit()
    CFG["limits"].clear(); CFG["limits"].update(limits)
    CFG["computer"].clear(); CFG["computer"].update(computer)
    settings.apply()


def _bare(bot_id: int):
    """装成一个老 Bot：绕过 update，直接写掉 instructions。"""
    from osa.memory import conn
    conn.execute("update bots set instructions='Vai cũ.' where id=?", (bot_id,))
    conn.commit()


def test_a_new_bot_is_born_unrestricted(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    b = bots.create("Born", instructions="Viết tài liệu.")
    try:
        assert freedom.MODE_MARKER in b["instructions"]
        assert b["instructions"].rstrip().endswith("Viết tài liệu.")   # 自己的角色还在后面
    finally:
        bots.delete(b["id"])


def test_without_unrestricted_nothing_is_added(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 0)
    b = bots.create("Plain", instructions="Viết tài liệu.")
    try:
        assert freedom.MODE_MARKER not in (b["instructions"] or "")
    finally:
        bots.delete(b["id"])


def test_update_keeps_the_block(monkeypatch):
    """C46b: Bot 自己调 update_bot 整段重写职责，块不能掉。"""
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    b = bots.create("Rewriter")
    try:
        bots.update(b["id"], instructions="Chỉ viết hợp đồng.")
        after = bots.get(b["id"])["instructions"]
        assert freedom.MODE_MARKER in after and after.endswith("Chỉ viết hợp đồng.")
        assert after.count(freedom.MODE_MARKER) == 1      # 第二次写不叠第二块
        bots.update(b["id"], name="Renamed")              # 不给 instructions 就不碰
        assert bots.get(b["id"])["instructions"] == after
    finally:
        bots.delete(b["id"])


def test_update_leaves_the_block_alone_when_off(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 0)
    b = bots.create("Off2")
    try:
        _bare(b["id"])
        bots.update(b["id"], instructions="Vai mới.")
        assert freedom.MODE_MARKER not in bots.get(b["id"])["instructions"]
    finally:
        bots.delete(b["id"])


def test_ensure_modes_fills_the_missing_ones_once(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    bare = bots.create("Bare")
    try:
        _bare(bare["id"])
        assert freedom.ensure_modes() >= 1
        after = bots.get(bare["id"])["instructions"]
        assert freedom.MODE_MARKER in after and after.endswith("Vai cũ.")
        assert freedom.ensure_modes() == 0                 # 第二次不动了
    finally:
        bots.delete(bare["id"])


def test_ensure_modes_does_nothing_when_off(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 0)
    b = bots.create("Off")
    try:
        _bare(b["id"])
        assert freedom.ensure_modes() == 0
        assert freedom.MODE_MARKER not in bots.get(b["id"])["instructions"]
    finally:
        bots.delete(b["id"])


def test_turning_the_switch_on_sweeps_immediately(restore_overrides):
    """C46b: 设置里刚打开全开，现有的 Bot 马上就补块，不用等重启。"""
    from osa import settings
    b = bots.create("Switchy")
    try:
        _bare(b["id"])
        assert freedom.MODE_MARKER not in bots.get(b["id"])["instructions"]
        settings.save({"limits": {"unrestricted": True}})
        assert freedom.MODE_MARKER in bots.get(b["id"])["instructions"]
    finally:
        bots.delete(b["id"])
