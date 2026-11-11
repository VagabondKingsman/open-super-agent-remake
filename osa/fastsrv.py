"""Speed layer for slow links (high RTT, small MTU).

- /assets/*: serves a precompressed sibling (.gz) when the client accepts gzip,
  and marks the response immutable so repeat visits cost zero round trips.
- JSON/HTML answers above ~900 B: gzip compress, flushed per chunk so
  streaming is unaffected.

Nothing here touches WebSocket scopes or event streams.
"""
from __future__ import annotations

import logging
import mimetypes
import os
from email.utils import formatdate
from pathlib import Path
from starlette.types import ASGIApp, Message, Receive, Scope, Send
import zlib

log = logging.getLogger("osa.fastsrv")

DIST = Path(__file__).parent / "static" / "dist"
ASSET_PREFIX = "/assets/"
MIN = 900
TEXTY = (
    "application/json",
    "application/javascript",
    "application/xml",
    "image/svg+xml",
    "text/",
)


def accepts_gzip(header) -> bool:
    if not header:
        return False
    if isinstance(header, (bytes, bytearray)):
        header = header.decode("latin-1")
    for part in header.split(","):
        bits = part.split(";")
        enc = bits[0].strip().lower()
        q = 1.0
        for b in bits[1:]:
            b = b.strip()
            if b.startswith("q="):
                try:
                    q = float(b[2:])
                except ValueError:
                    q = 1.0
        if enc in ("gzip", "*") and q > 0:
            return True
    return False


def _hget(headers, name: bytes):
    for k, v in headers:
        if k.lower() == name:
            return v
    return None


class Speed:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        if path.startswith(ASSET_PREFIX) and scope["method"] in ("GET", "HEAD"):
            try:
                served = await self._asset(scope, receive, send)
            except Exception:  # 静态文件永远不要挡住页面
                log.warning("fastsrv asset %s", path, exc_info=True)
                served = False
            if served:
                return
        return await self._compress(scope, receive, send)

    # ---------- static assets ----------
    async def _asset(self, scope: Scope, receive: Receive, send: Send) -> bool:
        if _hget(scope["headers"], b"range"):
            return False  # 交给 StaticFiles 处理 Range
        rel = scope["path"][len(ASSET_PREFIX):]
        if ".." in rel:
            return False
        src = (DIST / "assets" / rel).resolve()
        try:
            src.relative_to((DIST / "assets").resolve())
        except ValueError:
            return False
        gz = src.with_name(src.name + ".gz")
        if not src.is_file():
            return False
        want = accepts_gzip(_hget(scope["headers"], b"accept-encoding"))
        body_path = gz if (want and gz.is_file()) else src
        try:
            st = src.stat()
        except OSError:
            return False
        etag = '"%x-%x"' % (int(st.st_mtime), st.st_size)
        ctype = mimetypes.guess_type(src.name)[0] or "application/octet-stream"
        headers = [
            (b"content-type", ctype.encode()),
            (b"cache-control", b"public, max-age=31536000, immutable"),
            (b"etag", etag.encode()),
            (b"last-modified", formatdate(st.st_mtime, usegmt=True).encode()),
            (b"vary", b"accept-encoding"),
        ]
        inm = _hget(scope["headers"], b"if-none-match")
        if inm and etag in inm.decode("latin-1"):
            await send({"type": "http.response.start", "status": 304, "headers": headers})
            await send({"type": "http.response.body", "body": b""})
            return True
        if body_path == gz:
            headers.append((b"content-encoding", b"gzip"))
        headers.append((b"content-length", str(body_path.stat().st_size).encode()))
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        if scope["method"] == "HEAD":
            await send({"type": "http.response.body", "body": b""})
            return True
        with open(body_path, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b""})
        return True

    # ---------- on-the-fly gzip for text answers ----------
    async def _compress(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not accepts_gzip(_hget(scope["headers"], b"accept-encoding")):
            return await self.app(scope, receive, send)
        state = {"on": False, "co": None}

        async def send2(message: Message) -> None:
            if message["type"] == "http.response.start":
                st = message["status"]
                headers = list(message.get("headers") or [])
                ctype = (_hget(headers, b"content-type") or b"").decode("latin-1").lower()
                clen = _hget(headers, b"content-length")
                big = clen is None or (clen.isdigit() and int(clen) >= MIN)
                ok = (
                    st in (200, 201, 202)
                    and not _hget(headers, b"content-encoding")
                    and big
                    and ctype.startswith(TEXTY)
                )
                if ok:
                    state["on"] = True
                    state["co"] = zlib.compressobj(6, zlib.DEFLATED, 16 + 15)  # gzip 框架，不是 raw deflate
                    headers = [(k, v) for k, v in headers if k.lower() != b"content-length"]
                    headers.append((b"content-encoding", b"gzip"))
                    headers.append((b"vary", b"accept-encoding"))
                    message = dict(message, headers=headers)
                return await send(message)
            if message["type"] == "http.response.body" and state["on"]:
                body = message.get("body", b"") or b""
                more = bool(message.get("more_body"))
                out = state["co"].compress(body)
                if not more:
                    out += state["co"].flush(zlib.Z_FINISH)
                else:
                    out += state["co"].flush(zlib.Z_SYNC_FLUSH)
                return await send({"type": "http.response.body", "body": out, "more_body": more})
            return await send(message)

        return await self.app(scope, receive, send2)
