"""fetch_url 默认不抓本机和内网地址，跳转到内网也挡住。"""
import httpx
import pytest

from osa import i18n, tools
from osa.config import CFG


def _blocked_prefix() -> str:
    sample = i18n.t("没抓取：{host} 是本机或内网地址。要抓内网页面，在 config.yaml 里设 tools.fetch_private: true", host="HOST")
    return sample.split("HOST", 1)[0]


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "192.168.1.1", "172.17.0.1", "169.254.169.254",
                                "100.100.100.100", "0.0.0.0", "::1", "::ffff:127.0.0.1", "fe80::1", "fd00::1", "224.0.0.1"])
def test_private_addresses(ip):
    assert tools.private_ip(ip)


@pytest.mark.parametrize("ip", ["1.1.1.1", "8.8.8.8", "2606:4700:4700::1111", "198.18.0.7"])   # 最后一个：代理的假地址
def test_public_addresses(ip):
    assert not tools.private_ip(ip)


@pytest.mark.parametrize("url", ["http://127.0.0.1:8765/api/bootstrap", "http://localhost:8765/", "http://[::1]/",
                                 "http://169.254.169.254/latest/meta-data/", "http://2130706433/", "http://127.1/"])
async def test_blocked_urls(url):
    assert (await tools.fetch_url(url)).startswith(_blocked_prefix())


async def test_only_http():
    assert await tools.blocked("file:///etc/passwd") == i18n.t("只能抓取 http / https 网址")


async def test_redirect_to_private_is_blocked(monkeypatch, public_dns):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["host"] + request.url.path)
        return httpx.Response(302, headers={"location": "http://127.0.0.1:8765/api/bootstrap"})
    monkeypatch.setattr(tools, "_TRANSPORT", httpx.MockTransport(handler))
    out = await tools.fetch_url("https://public.example.invalid/start")
    assert out.startswith(_blocked_prefix()) and seen == ["public.example.invalid/start"]   # 内网那一跳没发出去


async def test_redirects_are_followed(monkeypatch, public_dns):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/a":
            return httpx.Response(301, headers={"location": "/b"})
        return httpx.Response(200, text="<html><script>x()</script><p>到了 b</p></html>")
    monkeypatch.setattr(tools, "_TRANSPORT", httpx.MockTransport(handler))
    assert await tools.fetch_url("https://site.example.invalid/a") == " 到了 b "


def _dns(monkeypatch, answer):
    """Fake the event loop's resolver (what both the check and a plain httpx connect would use).
    answer(host) returns a list of IPs or raises OSError."""
    import asyncio
    import socket

    async def getaddrinfo(self, host, port, *a, **kw):
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
                for ip in answer(host)]
    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", getaddrinfo)


@pytest.fixture
def public_dns(monkeypatch):
    """Every name resolves to one public address; records each lookup."""
    lookups = []

    def answer(host):
        lookups.append(host)
        return ["93.184.215.14"]
    _dns(monkeypatch, answer)
    return lookups


async def test_connects_to_the_checked_address(monkeypatch, public_dns):
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, text="<p>ok</p>")
    monkeypatch.setattr(tools, "_TRANSPORT", httpx.MockTransport(handler))
    assert await tools.fetch_url("https://news.example.invalid:8443/x?q=1") == " ok "
    [r] = sent
    assert r.url.host == "93.184.215.14" and r.url.port == 8443 and r.url.path == "/x" and r.url.query == b"q=1"
    assert r.headers["host"] == "news.example.invalid:8443"
    assert r.extensions["sni_hostname"] == "news.example.invalid"
    assert public_dns == ["news.example.invalid"]   # resolved once: the checked answer is the one used


async def test_rebinding_answer_is_refused(monkeypatch):
    """A name whose answer flips to a private address between lookups never gets a request."""
    answers = iter([["93.184.215.14"], ["127.0.0.1"]])
    sent = []
    _dns(monkeypatch, lambda host: next(answers, ["127.0.0.1"]))
    monkeypatch.setattr(tools, "_TRANSPORT", httpx.MockTransport(lambda r: sent.append(r) or httpx.Response(200, text="x")))
    await tools.fetch_url("http://rebind.example.invalid/")
    assert sent and all(r.url.host == "93.184.215.14" for r in sent)   # the request goes to the checked address


async def test_any_private_answer_blocks(monkeypatch):
    _dns(monkeypatch, lambda host: ["93.184.215.14", "10.0.0.5"])
    assert (await tools.fetch_url("http://mixed.example.invalid/")).startswith(_blocked_prefix())


async def test_unresolvable_host_is_not_fetched(monkeypatch):
    def fail(host):
        raise OSError("no such host")
    _dns(monkeypatch, fail)
    assert await tools.fetch_url("http://gone.example.invalid/") == i18n.t("没抓取：解析不了 {host}", host="gone.example.invalid")


async def test_body_is_read_with_a_cap(monkeypatch, public_dns):
    monkeypatch.setattr(tools, "MAX_BYTES", 1000, raising=False)
    pulled = []

    async def stream():
        for _ in range(100):
            pulled.append(1)
            yield b"<p>" + b"a" * 497 + b"</p>"

    monkeypatch.setattr(tools, "_TRANSPORT", httpx.MockTransport(lambda r: httpx.Response(200, content=stream())))
    out = await tools.fetch_url("http://big.example.invalid/")
    assert len(pulled) < 100 and 0 < len(out) <= 1000


async def test_private_allowed_when_configured(monkeypatch):
    monkeypatch.setitem(CFG, "tools", {"fetch_private": True})
    assert await tools.blocked("http://127.0.0.1:8765/") is None
