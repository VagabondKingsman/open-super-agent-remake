"""C46: 全开模式下新建的 Bot 生下来就带 mode 块，老的启动时补齐，全是幂等的。"""
from osa import bots, freedom
from osa.config import CFG


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


def test_ensure_modes_fills_the_missing_ones_once(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    bare = bots.create("Bare")            # 这里也带块，先摘掉装成老 Bot
    try:
        bots.update(bare["id"], instructions="Vai cũ.")
        assert freedom.MODE_MARKER not in bots.get(bare["id"])["instructions"]
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
        bots.update(b["id"], instructions="x")
        assert freedom.ensure_modes() == 0
        assert freedom.MODE_MARKER not in bots.get(b["id"])["instructions"]
    finally:
        bots.delete(b["id"])
