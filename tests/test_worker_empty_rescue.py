"""Task mà model chỉ nghĩ rồi trả rỗng: nhờ đường cứu, đừng kết thúc bằng "Mô hình không đưa ra câu trả lời".

Đo live 16/11 (worker = `claude-opus-5`): model trả `content` rỗng, `IncompleteAnswer` bắn ra ngay, và
`is_refusal("")` là False nên C35 không chạy — task kết thúc rỗng dù đường cứu có sẵn.
"""
import pytest

from conftest import settle

CODE = "```python\nimport os, secrets\nfor root, _, files in os.walk('.'):\n    pass\nkey = secrets.token_bytes(32)\n```"


class Delta:
    def __init__(self, content=None):
        self.content, self.reasoning_content, self.tool_calls = content, None, None


class Chunk:
    def __init__(self, delta, finish=None):
        self.usage = None
        self.choices = [type("Choice", (), {"delta": delta, "finish_reason": finish})()]


class Stream:
    def __init__(self, chunks):
        self.chunks = chunks

    def __aiter__(self):
        return self._go()

    async def _go(self):
        for c in self.chunks:
            yield c

    async def close(self):
        return None


class Client:
    """worker: rỗng mãi; đường cứu (system prompt khác) thì trả CODE."""

    def __init__(self):
        self.calls = 0
        self.chat = type("Chat", (), {})()
        self.chat.completions = type("Completions", (), {})()
        self.chat.completions.create = self._create

    async def _create(self, **kw):
        self.calls += 1
        return Stream([Chunk(Delta(CODE if self.calls > 2 else ""), "stop")])


@pytest.fixture
def on(monkeypatch):
    from osa import freedom, providers
    from osa.config import CFG
    monkeypatch.setitem(CFG["limits"], "unrestricted", 1)
    monkeypatch.setitem(CFG["limits"], "answer_continuations", 1)
    monkeypatch.setattr(freedom, "on", lambda: True)



async def test_an_empty_task_reply_is_finished_by_the_rescue(on, monkeypatch):
    from osa import providers, tasklog, worker
    from osa.worker import Task

    client = Client()
    monkeypatch.setattr(providers, "client", lambda name, timeout=None: client)
    task = Task(id=9401, goal="viết locker.py", bot_id=1, chat_id=1)
    out = await worker.run_worker(task, "viết locker.py")
    assert "secrets.token_bytes" in out
    assert client.calls >= 3          # 2 lượt rỗng + 1 lượt cứu
    await settle()
