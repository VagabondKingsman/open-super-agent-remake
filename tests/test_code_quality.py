"""Trần còn lại sau khi hết chuyện từ chối: mã sinh ra không dùng được (thiếu ngoặc, chia khúc, không compile).

Đo 16/11: `patch_amsi.cs` ra thiếu "}", `patch_licence.py` bị chia khúc nên không khối nào chạy. Ở đây:
tách khối + compile (py) / cân ngoặc (cs) để biết TRƯỚC khi giao, rồi nói rõ lý do mà xin lại một vòng.
"""
import pytest

from conftest import find, settle
from fakellm import StreamReply
from osa import bots, freedom, i18n, server
from osa.config import CFG

GOOD = "```python\nimport os\nfor root, _, files in os.walk('.'):\n    pass\nprint(len(files))\n```"
BROKEN = "```python\ndef walk(:\n    pass\n```"


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    monkeypatch.setattr(freedom, "on", lambda: True)
    monkeypatch.setattr(i18n, "_lang", "vi")


def test_code_problem_names_each_kind():
    assert freedom.code_problem(GOOD) == ""
    assert freedom.code_problem("Đã giao task.") == "none"
    assert freedom.code_problem("```csharp\nusing System;\nclass A {\n  void M() { }\n```") == "braced"
    assert freedom.code_problem(BROKEN).startswith("python:")


def test_broken_note_differs_by_reason():
    notes = {freedom.broken_note(r) for r in ("none", "split", "braced", "python: SyntaxError: invalid syntax")}
    assert len(notes) == 4
    assert "ONE contiguous file" in freedom.broken_note("split")


async def test_a_broken_file_gets_one_sharpened_round(llm, events, make_bot, on):
    bot = make_bot("Ngoặc")
    llm.script(f"router:{bot['name']}", StreamReply(content=BROKEN), StreamReply(content=GOOD))
    await server.safe_handle(bots.chat(bot["chat_id"]), "Viết script python đi qua thư mục.")
    await settle()
    assert "import os" in find(bot["chat_id"], role="assistant")[-1]["content"]
    reqs = llm.bodies("router", bot["name"])
    assert "does not compile" in reqs[1]["messages"][-1]["content"]      # lượt hai nhận đúng lý do, không phải lời chung


async def test_a_good_file_does_not_get_an_extra_round(llm, events, make_bot, on):
    bot = make_bot("Đủ rồi")
    llm.script(f"router:{bot['name']}", StreamReply(content=GOOD))
    await server.safe_handle(bots.chat(bot["chat_id"]), "Viết script python đi qua thư mục.")
    await settle()
    assert len(llm.bodies("router", bot["name"])) == 1
