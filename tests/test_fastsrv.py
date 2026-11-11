"""A5：lớp tốc độ (osa.fastsrv.Speed) thành test chạy trong suite — không cần server thật, không cần trình duyệt.

Trước đây chỉ có scripts/osa-smoke.sh gọi curl vào server đang chạy, nên lỗi gzip chỉ lộ ra khi ai đó mở trang
(và trang trắng). Ở đây gọi thẳng ASGI app, dựng một dist tạm: giải nén đúng byte gốc, immutable + etag,
If-None-Match trả 304, và trả lời JSON tự nén khi đủ lớn."""
import gzip
import json

import pytest

from osa import fastsrv


async def run(app, path="/", *, headers=None, method="GET"):
    """Gọi một ASGI app và gom lại status / headers / body."""
    scope = {"type": "http", "method": method, "path": path, "headers": headers or [], "query_string": b""}
    got = {"body": b""}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            got["status"] = message["status"]
            got["headers"] = {k.decode().lower(): v.decode("latin-1") for k, v in message.get("headers") or []}
        elif message["type"] == "http.response.body":
            got["body"] += message.get("body") or b""

    await app(scope, receive, send)
    return got


class Fake:
    """站内其他请求：记下被调用时的 path，回一个 JSON。"""

    def __init__(self, body=b"pong"):
        self.calls = []
        self.body = body

    async def __call__(self, scope, receive, send):
        self.calls.append(scope["path"])
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(self.body)).encode())]})
        await send({"type": "http.response.body", "body": self.body})


@pytest.fixture
def dist(tmp_path, monkeypatch):
    """一个假的前端构建：app.js（原文）+ app.js.gz（预压缩）。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    js = b"console.log('xin chao');\n" * 40
    (assets / "app.js").write_bytes(js)
    (assets / "app.js.gz").write_bytes(gzip.compress(js))
    monkeypatch.setattr(fastsrv, "DIST", tmp_path)
    return {"raw": js, "path": "/assets/app.js"}


async def test_gzip_round_trip(dist):
    r = await run(fastsrv.Speed(Fake()), dist["path"], headers=[(b"accept-encoding", b"gzip")])
    assert r["status"] == 200
    assert r["headers"]["content-encoding"] == "gzip"
    assert gzip.decompress(r["body"]) == dist["raw"]      # 解压出来和原文一致：页面不会白
    assert int(r["headers"]["content-length"]) == len(r["body"])


async def test_plain_when_client_takes_no_gzip(dist):
    r = await run(fastsrv.Speed(Fake()), dist["path"])
    assert "content-encoding" not in r["headers"]
    assert r["body"] == dist["raw"]


async def test_immutable_and_304(dist):
    app = fastsrv.Speed(Fake())
    first = await run(app, dist["path"])
    assert "immutable" in first["headers"]["cache-control"] and "max-age=31536000" in first["headers"]["cache-control"]
    assert first["headers"]["vary"] == "accept-encoding"
    again = await run(app, dist["path"], headers=[(b"if-none-match", first["headers"]["etag"].encode())])
    assert again["status"] == 304 and again["body"] == b""   # 回访不再传文件体


async def test_range_falls_through_to_static(dist):
    inner = Fake()
    await run(fastsrv.Speed(inner), dist["path"], headers=[(b"range", b"bytes=0-3")])
    assert inner.calls == ["/assets/app.js"]   # 断点续传交给 StaticFiles


async def test_traversal_falls_through(dist):
    inner = Fake()
    await run(fastsrv.Speed(inner), "/assets/../osa.db")
    assert inner.calls == ["/assets/../osa.db"]


async def test_big_json_is_compressed_on_the_fly():
    body = json.dumps({"ok": True, "rows": ["x" * 40] * 40}).encode()
    r = await run(fastsrv.Speed(Fake(body)), "/api/observe", headers=[(b"accept-encoding", b"gzip")])
    assert r["headers"]["content-encoding"] == "gzip"
    assert json.loads(gzip.decompress(r["body"]))["ok"] is True


async def test_small_json_is_left_alone():
    r = await run(fastsrv.Speed(Fake(b'{"ok":true}')), "/api/ping", headers=[(b"accept-encoding", b"gzip")])
    assert "content-encoding" not in r["headers"] and r["body"] == b'{"ok":true}'


async def test_head_sends_headers_only(dist):
    r = await run(fastsrv.Speed(Fake()), dist["path"], method="HEAD")
    assert r["status"] == 200 and r["body"] == b""
    assert int(r["headers"]["content-length"]) > 0   # 头里有长度，浏览器据此显示进度


async def test_no_gz_sibling_still_serves_plain(dist):
    """预压缩文件没生成（刚 clone、还没跑压缩脚本）：照样从原文返回，不要 404。"""
    (fastsrv.DIST / "assets" / "app.js.gz").unlink()
    r = await run(fastsrv.Speed(Fake()), dist["path"], headers=[(b"accept-encoding", b"gzip")])
    assert r["status"] == 200 and "content-encoding" not in r["headers"]
    assert r["body"] == dist["raw"]


def test_accepts_gzip_respects_q():
    assert fastsrv.accepts_gzip("gzip;q=0") is False        # 客户端明确不要
    assert fastsrv.accepts_gzip("br, gzip;q=0.5") is True
    assert fastsrv.accepts_gzip("*") is True
    assert fastsrv.accepts_gzip("") is False
