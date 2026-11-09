"""Login brute force: per-IP lockout plus one global queue, so rotating IPs or X-Forwarded-For buys nothing."""
import asyncio

import pytest

from osa import auth


@pytest.fixture
def fast(monkeypatch, password):
    monkeypatch.setattr(auth, "FAIL_DELAY", 0.05, raising=False)
    monkeypatch.setattr(auth, "_fails", {})
    monkeypatch.setattr(auth, "_waiting", 0, raising=False)


async def test_wrong_guesses_from_many_ips_are_serialised(fast, monkeypatch):
    inside, peak = 0, 0
    real = auth.check_password
    real_sleep = asyncio.sleep

    def counting(given):
        nonlocal inside, peak
        inside += 1
        peak = max(peak, inside)
        return real(given)

    async def slow_sleep(s):
        nonlocal inside
        await real_sleep(0)   # yield so other guesses could run if the lock did not hold
        inside -= 1

    monkeypatch.setattr(auth, "check_password", counting)
    monkeypatch.setattr(auth.asyncio, "sleep", slow_sleep)
    results = await asyncio.gather(*(auth._guess(f"10.0.0.{i}", "wrong") for i in range(5)))
    assert results == [False] * 5
    assert peak == 1


async def test_parallel_wrong_guesses_take_one_delay_each(fast):
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    await asyncio.gather(*(auth._guess(f"10.0.1.{i}", "wrong") for i in range(4)))
    assert loop.time() - t0 >= 4 * auth.FAIL_DELAY * 0.9


async def test_full_queue_is_refused_without_checking(fast, monkeypatch):
    monkeypatch.setattr(auth, "MAX_WAITING", 2)
    checked = []
    real = auth.check_password
    monkeypatch.setattr(auth, "check_password", lambda g: checked.append(g) or real(g))
    results = await asyncio.gather(*(auth._guess(f"10.0.2.{i}", f"wrong{i}") for i in range(5)))
    assert results.count(None) == 3
    assert len(checked) == 2
    assert auth._waiting == 0


async def test_right_password_still_works_and_clears_the_ip(fast):
    assert await auth._guess("10.0.3.1", "wrong") is False
    assert auth._fails["10.0.3.1"]
    assert await auth._guess("10.0.3.1", "test-password") is True
    assert "10.0.3.1" not in auth._fails


async def test_per_ip_lockout_is_unchanged(fast):
    for _ in range(auth.MAX_FAILS):
        await auth._guess("10.0.4.1", "wrong")
    assert auth._blocked("10.0.4.1")
    assert not auth._blocked("10.0.4.2")


async def test_login_endpoint_serialises_wrong_guesses(fast, monkeypatch):
    from osa import server
    real_sleep, sleeping, peak = asyncio.sleep, 0, 0

    async def tracked(s):
        nonlocal sleeping, peak
        sleeping += 1
        peak = max(peak, sleeping)
        await real_sleep(0.02)
        sleeping -= 1

    monkeypatch.setattr(auth.asyncio, "sleep", tracked)

    async def attempt(i):
        body = b"password=wrong&next=/"
        scope = {"type": "http", "method": "POST", "path": "/login", "raw_path": b"/login", "query_string": b"",
                 "headers": [(b"host", b"127.0.0.1:8765"), (b"origin", b"http://127.0.0.1:8765"),
                             (b"content-type", b"application/x-www-form-urlencoded")],
                 "scheme": "http", "root_path": "", "http_version": "1.1",
                 "client": (f"10.0.5.{i}", 50000), "server": ("127.0.0.1", 8765)}
        sent = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(msg):
            sent.append(msg)
        await server.app(scope, receive, send)
        return sent[0]["status"]

    assert await asyncio.gather(*(attempt(i) for i in range(4))) == [401] * 4
    assert peak == 1
