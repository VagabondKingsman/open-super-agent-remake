"""Worker 可用的工具。新增工具：写一个 async 函数并加进 TOOLS。"""

from .i18n import s as _s
import re
import html
import httpx
from .config import CFG

UA = {"User-Agent": "open-super-agent/0.1"}


async def web_search(query: str) -> str:
    async with httpx.AsyncClient(timeout=20, headers=UA, follow_redirects=True) as c:
        if url := CFG["search"].get("searxng_url"):
            r = await c.get(f"{url}/search", params={"q": query, "format": "json"})
            items = r.json().get("results", [])[:8]
            return "\n".join(f"- {i['title']} | {i['url']}\n  {i.get('content', '')}" for i in items) or _s('audit_9b7997c71d')
        r = await c.post("https://html.duckduckgo.com/html/", data={"q": query})
        links = re.findall(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>', r.text)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.S)
        out = []
        for i, (u, t) in enumerate(links[:8]):
            s = re.sub("<.*?>", "", snippets[i]) if i < len(snippets) else ""
            out.append(f"- {html.unescape(re.sub('<.*?>', '', t))} | {u}\n  {html.unescape(s)}")
        return "\n".join(out) or _s('audit_9b7997c71d')


async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=20, headers=UA, follow_redirects=True) as c:
        r = await c.get(url)
    text = re.sub(r"<(script|style)[\s\S]*?</\1>", "", r.text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text)[:8000]


TOOLS = {
    "web_search": (web_search, _s('audit_d6eca627fd'), {"query": _s('audit_8e7107da9f')}),
    "fetch_url": (fetch_url, _s('audit_cf12a9d00c'), {"url": _s('audit_33fa921b9f')}),
}


def lookup(name: str):
    """内置工具或 MCP 工具，找不到返回 None。"""
    from . import mcp_hub
    if name in TOOLS:
        return TOOLS[name][0]
    return mcp_hub.TOOLS.get(name, (None,))[0]


def schemas() -> list[dict]:
    from . import mcp_hub
    return [s for _, s in mcp_hub.TOOLS.values()] + [{"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in params.items()},
                       "required": list(params)}}} for name, (_, desc, params) in TOOLS.items()]
