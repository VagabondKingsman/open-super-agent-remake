"""OPEN-RETRY-LIVE: lỗi giữa stream sau khi đã có chữ vẫn phải gọi lại, không để lượt trả lời rỗng.

Trước đây Router chỉ gọi lại khi chưa đẩy chữ nào (`sent or … -> raise`), nên một lỗi "at capacity" đến sau
vài chữ là cả lượt chết: người dùng thấy khung chat trống. Giao diện đã xoá được phần đã hiện (sự kiện
`stream` `reset`), nên gọi lại là an toàn.
"""
import pytest

from conftest import find, settle
from fakellm import MidError
from osa import bots, i18n, server


def _chat(bot):
    return bots.chat(bot["chat_id"])


def _replies(bot):
    return find(bot["chat_id"], role="assistant")


@pytest.fixture
def vi(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")


async def test_text_already_pushed_does_not_block_the_retry(llm, events, make_bot, vi):
    bot = make_bot("Retry sau khi đã có chữ")
    llm.script(f"router:{bot['name']}", MidError(), "Câu trả lời đầy đủ sau khi gọi lại.")
    await server.safe_handle(_chat(bot), "Chào")
    await settle()

    assert _replies(bot)[-1]["content"].strip() == "Câu trả lời đầy đủ sau khi gọi lại."
    assert len(llm.bodies("router", bot["name"])) == 2          # có gọi lại thật
    assert any(e.get("reset") for e in events.of("stream"))     # và bảo giao diện xoá phần đã hiện


async def test_quota_midstream_still_does_not_retry(llm, events, make_bot, vi):
    """Đã có chữ mà hết hạn mức thì vẫn không gọi lại: chờ cũng thế."""
    bot = make_bot("Hết hạn mức giữa stream")
    llm.script(f"router:{bot['name']}", MidError(code="insufficient_quota", message="insufficient_quota: out of credits"))
    await server.safe_handle(_chat(bot), "Chào")
    await settle()
    assert len(llm.bodies("router", bot["name"])) == 1
