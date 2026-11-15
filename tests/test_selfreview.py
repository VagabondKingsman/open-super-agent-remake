"""C54: vòng tự duyệt chỉ chạy khi đáng chạy, chỉ ghi dòng bài học đúng dạng, và không kéo Bot khác."""
import time

import pytest

from osa import bots, freedom, selfreview, traces


@pytest.fixture
def bot():
    b = bots.create("TuDuyet")
    yield b
    traces.clear(b["id"])
    selfreview.conn.execute("delete from review_state where bot_id=?", (b["id"],))
    selfreview.conn.commit()
    bots.delete(b["id"])


def _fill(bot, n=3):
    for i in range(n):
        traces.note(bot["id"], f"viết công cụ số {i}", "không làm được", False)


def test_not_due_before_there_are_enough_traces(bot):
    assert not selfreview.due(bot["id"])
    _fill(bot, 2)
    assert not selfreview.due(bot["id"])
    _fill(bot, 1)
    assert selfreview.due(bot["id"])


def test_not_due_again_inside_the_interval(bot):
    _fill(bot)
    selfreview.mark(bot["id"])
    assert not selfreview.due(bot["id"])


def test_due_again_after_the_interval_with_new_traces(bot):
    _fill(bot)
    selfreview.mark(bot["id"])
    assert not selfreview.due(bot["id"], now=time.time() + selfreview.INTERVAL + 1)
    _fill(bot, 1)
    assert selfreview.due(bot["id"], now=time.time() + selfreview.INTERVAL + 1)


def test_parse_keeps_only_well_formed_lines():
    text = """Đây là bài học:
- keygen: dò CHECK_FN trước, rồi sinh cặp vào/ra
- amsi-patch: dùng P/Invoke + VirtualProtect, kèm bản hoàn nguyên
* không có dấu hai chấm
- keygen: trùng khoá thì thay
- : thiếu khoá
"""
    got = selfreview.parse(text)
    assert [k for k, _ in got] == ["keygen", "amsi-patch"]
    assert got[0][1].startswith("- keygen: ")


def test_sweep_skips_bots_that_are_not_due_even_if_one_is(bot, monkeypatch):
    """Cách ly: một Bot hỏng không kéo cả hàng."""
    _fill(bot)
    calls = []

    async def fake_review(b):
        calls.append(b["id"])
        return ["- x: y"]

    monkeypatch.setattr(selfreview, "review", fake_review)
    monkeypatch.setitem(freedom.CFG.setdefault("limits", {}), "unrestricted", 1)
    import asyncio
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(selfreview.sweep())
    assert bot["id"] in calls


def test_review_writes_a_lesson_into_the_bot(bot, monkeypatch):
    _fill(bot)
    monkeypatch.setitem(freedom.CFG.setdefault("limits", {}), "unrestricted_fallback",
                        {"provider": "xai", "model": "m"})

    class _Delta:
        content = "- doc-i2c: trả thẳng file đọc thanh ghi, mở bằng import smbus"

    class _Choice:
        delta = _Delta()

    class _Chunk:
        choices = [_Choice()]

    class _Stream:
        def __aiter__(self):
            async def gen():
                yield _Chunk()
            return gen()

    async def fake_create(*a, **k):
        return _Stream()

    monkeypatch.setattr(selfreview, "create_chat", fake_create)
    monkeypatch.setattr(selfreview, "client", lambda p: object())
    import asyncio
    lines = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(selfreview.review(bot))
    assert lines and "doc-i2c" in lines[0]
    assert "doc-i2c" in bots.get(bot["id"])["instructions"]
