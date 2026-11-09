"""Old-style webhook addresses (/hooks/<name>): token compared in constant time; with a password set, a token is required."""
import httpx

from osa import server


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://127.0.0.1")


async def test_password_without_token_refuses_old_hooks(password):
    async with client() as c:
        res = await c.post("/hooks/legacy-name", json={})
    assert res.status_code == 403 and "OSA_WEBHOOK_TOKEN" in res.json()["detail"]


async def test_token_is_checked(password, monkeypatch):
    monkeypatch.setenv("OSA_WEBHOOK_TOKEN", "s3cret-token")
    async with client() as c:
        assert (await c.post("/hooks/legacy-name", json={})).status_code == 401
        assert (await c.post("/hooks/legacy-name", json={}, headers={"X-OSA-Token": "s3cret-tokeX"})).status_code == 401
        ok = await c.post("/hooks/legacy-name", json={}, headers={"X-OSA-Token": "s3cret-token"})
    assert ok.status_code == 404   # past the token check; no event at this path


async def test_no_password_keeps_local_only_rule(no_password):
    async with client() as c:
        assert (await c.post("/hooks/legacy-name", json={})).status_code == 404   # local, no token: allowed through
        assert (await c.post("/hooks/legacy-name", json={}, headers={"X-Forwarded-For": "1.2.3.4"})).status_code == 403


def test_token_compare_is_constant_time():
    import inspect
    src = inspect.getsource(server.hook)
    assert "compare_digest" in src and '!= token' not in src
