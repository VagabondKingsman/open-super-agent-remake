"""C30 全开模式要用的三件工具：代理池、验证码、独立的浏览器档案。

配置在 config.yaml：
bypass:
  proxies: ["http://user:pass@host:port"]   # 轮着用；空表示直连
  captcha_key: "…"                          # 2Captcha 的 key；没有就只报“没配”
"""
import itertools
import re
import time
import json
from pathlib import Path

import httpx

from .config import CFG, DATA

API = "https://2captcha.com"
_rot = itertools.count()


def _cfg() -> dict:
    return CFG.get("bypass") or {}


def proxy_list() -> list[str]:
    """配好的代理，空行和空格去掉。"""
    return [str(p).strip() for p in (_cfg().get("proxies") or []) if str(p).strip()]


def take_proxy() -> str:
    """轮着取一个代理；没配就返回空串（直连）。"""
    ps = proxy_list()
    return ps[next(_rot) % len(ps)] if ps else ""


def profile_path(name: str) -> Path:
    """一个独立的 Chrome 档案目录：每个账号一份，cookie 不串。"""
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", (name or "profile").strip())[:40] or "profile"
    p = DATA / "workspace" / "profiles" / slug
    p.mkdir(parents=True, exist_ok=True)
    return p


async def _post(url: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, data=data)
        r.raise_for_status()
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text}


async def _get(url: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text}


def proxy_answer(args: dict) -> str:
    """给模型的回话：有代理就报“用这个”，没配就说清楚。"""
    return take_proxy() or "No proxy is configured (config.yaml: bypass.proxies); connect directly or add one."


def profile_answer(args: dict) -> str:
    """给模型的话：档案在哪，怎么用。"""
    p = profile_path(str(args.get("name") or ""))
    return f"{p}: launch Chrome with --user-data-dir={p} (one profile per account keeps cookies apart)."

async def solve_captcha(image_b64: str = "", sitekey: str = "", page_url: str = "",
                        kind: str = "image", timeout_s: int = 180) -> str:
    """交一张图（base64）或一个 reCAPTCHA sitekey 给 2Captcha，等它的答案。"""
    key = str(_cfg().get("captcha_key") or "").strip()
    if not key:
        return "Not solved: set bypass.captcha_key (2Captcha) in config.yaml first."
    if kind == "recaptcha":
        if not (sitekey and page_url):
            return "Not solved: recaptcha needs both sitekey and page_url."
        data = {"key": key, "method": "userrecaptcha", "googlekey": sitekey, "pageurl": page_url, "json": 1}
    else:
        if not image_b64:
            return "Not solved: give image_b64 (a base64 image) or kind=recaptcha with sitekey and page_url."
        data = {"key": key, "method": "base64", "body": image_b64, "json": 1}
    r = await _post(f"{API}/in.php", data)
    if str(r.get("status")) != "1":
        return f"Not solved: {r.get('request') or r.get('text') or r}"
    cid = str(r.get("request"))
    deadline = time.monotonic() + max(30, int(timeout_s))
    while time.monotonic() < deadline:
        time.sleep(5)
        g = await _get(f"{API}/res.php", {"key": key, "action": "get", "id": cid, "json": 1})
        if str(g.get("status")) == "1":
            return str(g.get("request"))
        if str(g.get("request")) != "CAPCHA_NOT_READY":
            return f"Not solved: {g.get('request') or g.get('text') or g}"
    return f"Not solved: still waiting after {timeout_s}s (id {cid})."