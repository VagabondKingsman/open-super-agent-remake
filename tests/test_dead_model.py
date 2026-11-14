"""C55: model của vai bị 404/401/402 thì lượt đi tiếp trên model cứu hộ, không trả về câu rỗng."""
from osa import freedom
from osa.config import CFG


def test_a_dead_role_model_falls_over(monkeypatch):
    import inspect
    from osa import router

    src = inspect.getsource(router.Router._stream)
    assert "openai.NotFoundError" in src and "freedom.fallback()" in src
    assert "router model unavailable" in src


def test_the_rescue_model_is_configured(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "unrestricted_fallback", {"provider": "deepseek", "model": "x"})
    assert freedom.fallback() == ("deepseek", "x", {})
