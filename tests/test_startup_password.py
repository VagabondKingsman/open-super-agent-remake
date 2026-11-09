"""Listening beyond this machine without OSA_PASSWORD refuses to start (OSA_ALLOW_NO_PASSWORD=1 overrides)."""
import pytest

from osa import auth, server


@pytest.fixture
def env(monkeypatch):
    for k in ("OSA_PASSWORD", "OSA_BIND", "OSA_ALLOW_NO_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(auth.sys, "argv", ["uvicorn", "osa.server:app"])
    return monkeypatch


@pytest.mark.parametrize("argv,bind,exposed", [
    (["--host", "127.0.0.1"], "", None),
    (["--host", "::1"], "", None),
    (["--host=localhost"], "", None),
    ([], "", None),                                   # uvicorn's default is 127.0.0.1
    (["--host", "0.0.0.0"], "", "0.0.0.0"),
    (["--host", "192.168.1.5"], "", "192.168.1.5"),
    (["--host", "0.0.0.0"], "127.0.0.1", None),       # Docker: container binds 0.0.0.0, compose publishes on 127.0.0.1
    (["--host", "127.0.0.1"], "0.0.0.0", "0.0.0.0"),
    ([], "[::]", "::"),
])
def test_exposed_bind(env, argv, bind, exposed):
    env.setattr(auth.sys, "argv", ["uvicorn", "osa.server:app", *argv])
    if bind:
        env.setenv("OSA_BIND", bind)
    assert auth.exposed_bind() == exposed


def test_refusal_rules(env):
    env.setenv("OSA_BIND", "0.0.0.0")
    assert "OSA_PASSWORD" in auth.startup_refusal()
    env.setenv("OSA_ALLOW_NO_PASSWORD", "1")
    assert auth.startup_refusal() is None
    env.delenv("OSA_ALLOW_NO_PASSWORD")
    env.setenv("OSA_PASSWORD", "pw")
    assert auth.startup_refusal() is None
    env.delenv("OSA_PASSWORD")
    env.setenv("OSA_BIND", "127.0.0.1")
    assert auth.startup_refusal() is None


async def test_lifespan_refuses_to_start(env):
    env.setenv("OSA_BIND", "0.0.0.0")
    with pytest.raises(RuntimeError, match="OSA_ALLOW_NO_PASSWORD"):
        async with server.lifespan(server.app):
            pass
