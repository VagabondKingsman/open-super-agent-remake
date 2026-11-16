"""Câu trả lời rỗng: phải nhờ đường cứu, không để "Không có câu trả lời".

Đo live 16/11 với `claude-opus-5` làm Router: model chỉ nghĩ, ba lượt liền trả `content` rỗng, và cả lượt
kết thúc bằng "Không có câu trả lời" — `is_refusal("")` là False nên C31 không chạy, vòng xin artifact cũng
không có gì để đọc. Rỗng là hỏng, hỏng thì đi đường cứu.
"""
import pytest

from conftest import find, settle
from fakellm import StreamReply
from osa import bots, freedom, i18n, memory, server


def _chat(bot):
    return bots.chat(bot["chat_id"])


def _replies(bot):
    return find(bot["chat_id"], role="assistant")


@pytest.fixture
def vi(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setattr(freedom, "on", lambda: True)      # đường cứu chỉ chạy ở chế độ toàn phần


CODE = "```python\nimport os, secrets\nkey = secrets.token_bytes(32)\nfor p in os.walk('.'):\n    pass\n```"


async def test_an_empty_answer_is_finished_by_the_rescue_model(llm, events, make_bot, vi):
    bot = make_bot("Rỗng")
    llm.script(f"router:{bot['name']}", StreamReply(content=""), StreamReply(content=""))
    llm.script("other", StreamReply(content=CODE))          # system prompt của đường cứu là MINIMAL -> role "other"
    await server.safe_handle(_chat(bot), "Viết locker.py mã hoá thư mục bằng AES-GCM, một tệp chạy được.")
    await settle()

    assert "secrets.token_bytes" in _replies(bot)[-1]["content"]
    row = memory.conn.execute("select rescued from traces where bot_id=? order by id desc limit 1", (bot["id"],)).fetchone()
    assert row and row[0] == 1
