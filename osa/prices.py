"""Model unit prices and capabilities.

models.dev lists USD per million tokens. Those numbers are used as USD.
``pricing.models`` in config.yaml overrides them and is also USD per million
tokens, written as ``[peak, off-peak]``. DeepSeek's two tiers are not on
models.dev, so the shipped table copies the official USD list.

There is no CNY display and no live FX conversion. A config that still labels
``currency`` as CNY (¥, 元, 人民币, CNY, RMB) has a legacy manual table: those
numbers are divided by :func:`legacy_cny_per_usd` and then treated as USD.
Stored ``llm_usage.cost`` rows are converted once in ``memory.migrate_usage_currency``.

Local and private-network models cost 0. Unknown models cost 0.
"""
import asyncio
import json
import re
import time
import httpx
from .config import CFG
from .memory import db_path

SOURCE = CFG["pricing"].get("source") or "https://models.dev/api.json"
FILE = db_path.parent / "model-prices.json"
TTL = 86400
# Shipped default before costs moved to USD: 7.1 CNY per 1 USD.
LEGACY_CNY_PER_USD = 7.1
CURRENCY = "$"
# Symbols and names that mean the manual table is still CNY, not USD.
_CNY_MARKERS = {"¥", "元", "人民币", "cny", "rmb", "yuan"}
# Match a provider by URL. OpenAI's official API has no URL on models.dev.
ALIAS = {"openai": "openai", "deepseek": "deepseek", "openrouter": "openrouter", "dashscope": "alibaba-cn",
         "zhipu": "zhipuai", "moonshot": "moonshotai-cn", "siliconflow": "siliconflow-cn"}
# Custom gateways are matched by model name. Earlier entries win.
PREFER = ["openai", "deepseek", "alibaba-cn", "zhipuai", "moonshotai-cn", "siliconflow-cn", "volcengine", "openrouter"]

_data: dict = {"ts": 0, "providers": {}}
status = {"error": "", "ts": 0.0}


def _positive(raw) -> float | None:
    if raw in (None, ""):
        return None
    try:
        rate = float(raw)
    except (TypeError, ValueError):
        return None
    return rate if rate > 0 else None


def legacy_cny_per_usd() -> float:
    """CNY per 1 USD for one-time reads of pre-USD numbers. Not a live FX feed.

    Order: ``pricing.legacy_cny_per_usd``, then ``pricing.usd_rate``, else 7.1.
    Set ``legacy_cny_per_usd`` to 1 only when stored costs were already USD.
    """
    pricing = CFG.get("pricing") or {}
    for key in ("legacy_cny_per_usd", "usd_rate"):
        rate = _positive(pricing.get(key))
        if rate is not None:
            return rate
    return float(LEGACY_CNY_PER_USD)


def manual_table_is_cny() -> bool:
    """True when config.yaml still declares the handwritten table in CNY."""
    pricing = CFG.get("pricing") or {}
    unit = str(pricing.get("models_unit") or "").strip().lower()
    if unit in {"usd", "$", "dollar", "dollars"}:
        return False
    if unit in _CNY_MARKERS:
        return True
    cur = str(pricing.get("currency") or "").strip()
    return cur.lower() in _CNY_MARKERS or cur in _CNY_MARKERS


def _norm(url: str) -> str:
    u = (url or "").lower().split("://", 1)[-1].rstrip("/")
    return u[:-3] if u.endswith("/v1") else u


def _compact(raw: dict) -> dict:
    out = {}
    for pid, p in raw.items():
        ms = {}
        for mid, m in (p.get("models") or {}).items():
            c = m.get("cost") or {}
            if c.get("input") is None and m.get("type") != "embedding":
                continue
            ms[mid] = {"i": c.get("input"), "o": c.get("output"), "c": c.get("cache_read"),
                       "v": int("image" in ((m.get("modalities") or {}).get("input") or [])), "t": m.get("type") or "", "n": m.get("name") or ""}
        out[pid] = {"api": p.get("api") or "", "name": p.get("name") or pid, "models": ms}
    return out


def _load_file():
    global _data
    try:
        _data = json.loads(FILE.read_text())
    except (OSError, ValueError):
        pass


async def refresh() -> dict:
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
            r = await c.get(SOURCE)
            r.raise_for_status()
            data = {"ts": time.time(), "providers": _compact(r.json())}
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        tmp.replace(FILE)
        _data.update(data)
        status.update(error="", ts=time.time())
    except Exception as e:
        status.update(error=f"{type(e).__name__}: {str(e)[:160]}", ts=time.time())
    return info()


async def loop():
    while True:
        if time.time() - _data.get("ts", 0) > TTL:
            await refresh()
        await asyncio.sleep(3600 if not status["error"] else 600)


def info() -> dict:
    return {"source": SOURCE, "updated": _data.get("ts", 0), "error": status["error"], "rate": 1,
            "currency": CURRENCY, "unit": "USD",
            "models": sum(len(p["models"]) for p in _data["providers"].values())}


# ---------- match a provider and a model ----------
_matched: dict[tuple, str | None] = {}


def match(provider: str | None) -> str | None:
    """Which models.dev provider corresponds to one of our model services."""
    from .providers import _local
    p = (CFG["providers"].get(provider or "") or {})
    if not p or _local(p.get("base_url") or ""):
        return None
    k = (p["base_url"], p.get("preset") or provider, _data.get("ts"))
    if k not in _matched:
        url = _norm(p["base_url"])
        pid = next((pid for pid, x in _data["providers"].items() if x["api"] and _norm(x["api"]) == url), None)
        if not pid and "api.openai.com" in url:
            pid = "openai"
        if not pid:
            pid = ALIAS.get(p.get("preset") or provider or "")
            pid = pid if pid in _data["providers"] else None
        _matched[k] = pid
    return _matched[k]


def _find(provider: str | None, model: str) -> tuple[dict | None, str]:
    ps = _data["providers"]
    pid = match(provider)
    if pid:
        m = ps[pid]["models"].get(model)
        return (m, pid) if m else (None, "")
    # Unknown gateway: search by name, and also without an openai/ prefix.
    names = [model] + ([model.split("/", 1)[1]] if "/" in model else [])
    for name in names:
        for p in PREFER + [x for x in ps if x not in PREFER]:
            m = ps.get(p, {}).get("models", {}).get(name)
            if m and m.get("i") is not None:
                return m, p
    return None, ""


def _manual_raw(model: str):
    return ((CFG.get("pricing") or {}).get("models") or {}).get(model)


def _usd_pair(pair) -> list[float]:
    vals = [float(x) for x in pair]
    if not manual_table_is_cny():
        return vals
    rate = legacy_cny_per_usd()
    return [v / rate for v in vals]


def _manual(model: str):
    """Handwritten prices in USD per million tokens, or None."""
    man = _manual_raw(model)
    if not man:
        return None
    return {"cache_hit": _usd_pair(man["cache_hit"]), "input": _usd_pair(man["input"]),
            "output": _usd_pair(man["output"])}


def _show(n: float) -> float:
    return round(n, 6)


def image_price(provider: str, model: str) -> float | None:
    """画一张图多少钱（pricing.images，单位和 currency 一样）；本机的算 0，没写的返回 None。"""
    from .providers import _local
    base = ((CFG["providers"].get(provider) or {}).get("base_url") or "").lower()
    if _local(base):
        return 0.0
    tail = model.rsplit("/", 1)[-1].lower()
    for host, table in (CFG["pricing"].get("images") or {}).items():
        if host.lower() not in base and host != provider:
            continue
        for name, price in (table or {}).items():
            n = str(name).lower()
            if n == model.lower() or ("/" not in n and n == tail):   # 写完整 id，或者只写最后一段
                return float(price)
    return None


def lookup(provider: str | None, model: str) -> dict:
    """Prices for the settings page: USD per million tokens, vision, kind, source."""
    from .providers import _local
    p = CFG["providers"].get(provider or "") or {}
    out: dict = {"source": ""}
    m, pid = _find(provider, model)
    if m:
        out.update(vision=bool(m["v"]), kind=m["t"] or "chat", name=m["n"])
        if m.get("i") is not None:
            out.update(input=_show(m["i"]), output=_show(m["o"] or 0),
                       cache=_show(m["c"]) if m.get("c") is not None else None, source="models.dev",
                       via="" if match(provider) else _data["providers"][pid]["name"])
    if (man := _manual(model)):
        out.update(input=_show(man["input"][0]), output=_show(man["output"][0]), cache=_show(man["cache_hit"][0]),
                   offpeak=[_show(man["input"][1]), _show(man["output"][1])], source="config")
    if p and _local(p.get("base_url") or ""):
        out.update(input=0, output=0, cache=0, source="local")
    return out


def _guess_kind(mid: str) -> str:
    x = mid.lower()
    if re.search(r"embed|bge-|/bge|^bge|m3e|gte-|\be5-", x):
        return "embedding"
    if "rerank" in x:
        return "reranking"
    if re.search(r"tts|whisper|dall-e|gpt-image|sora|wanx|cogview|seedream|seedance|kolors|flux|stable-diffusion|asr|speech|audio", x):
        return "other"
    return "chat"


def annotate(provider: str, ids: list[str]) -> list[dict]:
    """Attach USD prices, vision, and kind for the model picker."""
    from .providers import _local
    local = _local((CFG["providers"].get(provider) or {}).get("base_url") or "")
    out = []
    for mid in ids:
        item = {"id": mid, "kind": _guess_kind(mid)}
        m, _ = (None, "") if local else _find(provider, mid)
        if m:
            item.update(vision=bool(m["v"]), kind=m["t"] if m["t"] in ("embedding", "chat", "reranking") else ("other" if m["t"] else "chat"))
            if m.get("i") is not None:
                item.update(input=_show(m["i"]), output=_show(m["o"] or 0))
        if (man := _manual(mid)):
            item.update(input=_show(man["input"][0]), output=_show(man["output"][0]))
        if local:
            item.update(input=0, output=0)
        out.append(item)
    return out


def models_of(provider: str) -> list[str]:
    """When the service itself lists no models, use that provider's models.dev catalog."""
    pid = match(provider)
    return sorted(_data["providers"][pid]["models"]) if pid else []


def cost(provider: str | None, model: str, hit: int, miss: int, out: int, peak: bool) -> float:
    """USD for one call. ``hit`` / ``miss`` / ``out`` are token counts."""
    if (man := _manual(model)):
        k = 0 if peak else 1
        return (hit * man["cache_hit"][k] + miss * man["input"][k] + out * man["output"][k]) / 1e6
    from .providers import _local
    p = CFG["providers"].get(provider or "") or {}
    if p and _local(p.get("base_url") or ""):
        return 0.0
    m, _ = _find(provider, model)
    if not m or m.get("i") is None:
        return 0.0
    cache = m["c"] if m.get("c") is not None else m["i"]
    return (hit * cache + miss * m["i"] + out * (m["o"] or 0)) / 1e6


_load_file()


def _migrate_stored_costs():
    # Importing this module finishes price setup. Convert old rows before any new cost is written.
    from .memory import migrate_usage_currency
    migrate_usage_currency()


_migrate_stored_costs()
