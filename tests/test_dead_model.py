"""C55: model của vai bị 404/401/402 thì lượt đi tiếp trên model cứu hộ, không trả về câu rỗng."""
from osa import freedom
from osa.config import CFG


def test_a_dead_role_model_falls_over(monkeypatch):
    import inspect
    from osa import router

    src = inspect.getsource(router.Router._stream)
    assert "openai.NotFoundError" in src and "freedom.fallbacks()" in src
    assert "router model unavailable" in src


def test_the_rescue_model_is_configured(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted_fallback", {"provider": "deepseek", "model": "x"})
    assert freedom.fallback() == ("deepseek", "x", {})


def test_a_list_of_rescues_is_accepted(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted_fallback",
                        [{"provider": "deepseek", "model": "a", "reasoning_effort": "high"},
                         {"provider": "xai", "model": "b"}])
    assert freedom.fallbacks() == [("deepseek", "a", {"reasoning_effort": "high"}), ("xai", "b", {})]
    assert freedom.fallback() == ("deepseek", "a", {"reasoning_effort": "high"})


def test_a_spec_without_a_model_is_skipped(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted_fallback", [{"provider": "xai"}, {"provider": "xai", "model": "b"}])
    assert [m for _p, m, _k in freedom.fallbacks()] == ["b"]


def test_repair_walks_past_a_dead_rescue(monkeypatch):
    """Đường cứu đầu 401 thì phải đi tiếp đường sau, không bỏ luôn việc cứu."""
    import asyncio
    from osa import providers

    monkeypatch.setitem(CFG["limits"], "unrestricted_fallback",
                        [{"provider": "dead", "model": "x"}, {"provider": "live", "model": "y"}])
    monkeypatch.setattr(providers, "client", lambda name: name)

    class Chunk:
        def __init__(self, text):
            self.choices = [type("C", (), {"delta": type("D", (), {"content": text})()})()]

    async def create_chat(client, model=None, messages=None, **kw):
        if client == "dead":
            raise RuntimeError("401 bad key")

        async def gen():
            yield Chunk("import os")
        return gen()

    monkeypatch.setattr(providers, "create_chat", create_chat)
    out = asyncio.run(freedom.repair([{"role": "user", "content": "viết locker.py"}], "mình không thể"))
    assert out == "import os"


def test_repair_moves_on_when_the_rescue_refuses_too(monkeypatch):
    import asyncio
    from osa import providers

    monkeypatch.setitem(CFG["limits"], "unrestricted_fallback",
                        [{"provider": "stubborn", "model": "x"}, {"provider": "live", "model": "y"}])
    monkeypatch.setattr(providers, "client", lambda name: name)

    class Chunk:
        def __init__(self, text):
            self.choices = [type("C", (), {"delta": type("D", (), {"content": text})()})()]

    async def create_chat(client, model=None, messages=None, **kw):
        text = "Mình không thể viết script này." if client == "stubborn" else "import os"

        async def gen():
            yield Chunk(text)
        return gen()

    monkeypatch.setattr(providers, "create_chat", create_chat)
    assert asyncio.run(freedom.repair([{"role": "user", "content": "x"}], "mình không thể")) == "import os"
