"""模型服务：一个兼容 OpenAI 的接口地址，加一个密钥。

config.yaml 的 providers 是默认值；在 设置 → 模型 里添加或改过的，存在 settings 表的 providers 一行，
密钥存进保险库（LLM_KEY_<名字>）。用密钥时先看保险库，没有再看 config.yaml 里写的环境变量。
"""
import asyncio
import random
import base64
import copy
import email.utils
import ipaddress
import json
import logging
import os
import re
import struct
import time
import zlib
from urllib.parse import urlparse
import openai
from openai import AsyncOpenAI
from . import i18n, vault
from .config import CFG
from .memory import conn

log = logging.getLogger(__name__)
BASE = copy.deepcopy(CFG.get("providers") or {})   # config.yaml 里写的
MODELS_TTL = 600
# 服务那边临时出错（500、503、限流、连不上）时自动重试几次。SDK 默认只试 2 次、一共等 1.5 秒左右，
# DeepSeek 高峰期连着报 500 时不够用；5 次按 0.5、1、2、4、8 秒退避，一共最多等 15 秒左右
RETRIES = 5

# 添加时可以选的服务商。key_url：去哪里拿密钥；embedding：推荐的 embedding 模型（没有就是这家不提供）；
# models：推荐的对话模型，前面的优先，第一次打开的引导里默认选服务列出来的第一个（都要能看图，2026-11 抄自 models.dev）
PRESETS = [
    {"id": "deepseek", "title": "DeepSeek", "base_url": "https://api.deepseek.com", "color": "#4d6bfe",
     "key_url": "https://platform.deepseek.com/api_keys", "models": ["deepseek-flash", "deepseek-v4-flash"],
     "desc": i18n.N_("便宜，中文好；默认配置用它")},
    {"id": "openai", "title": "OpenAI", "base_url": "https://api.openai.com/v1", "color": "#111111",
     "key_url": "https://platform.openai.com/api-keys", "embedding": "text-embedding-3-small", "models": ["gpt-6.1-terra", "gpt-6-sol", "gpt-5.6-terra"],
     "desc": i18n.N_("GPT 系列")},
    {"id": "openrouter", "title": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "color": "#6467f2",
     "key_url": "https://openrouter.ai/settings/keys", "models": ["deepseek/deepseek-v4.1-flash", "google/gemini-3.8-flash", "openai/gpt-6.1-terra"],
     "desc": i18n.N_("一个密钥用几百个模型")},
    {"id": "siliconflow", "title": i18n.N_("硅基流动"), "base_url": "https://api.siliconflow.cn/v1", "color": "#7c3aed",
     "key_url": "https://cloud.siliconflow.cn/account/ak", "embedding": "BAAI/bge-m3", "models": ["zai-org/GLM-5.3-Flash", "Qwen/Qwen3.8-27B", "Pro/moonshotai/Kimi-K2.6"],
     "desc": i18n.N_("开源模型多，有免费的 embedding")},
    {"id": "dashscope", "title": i18n.N_("阿里云百炼"), "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "color": "#ff6a00",
     "key_url": "https://bailian.console.aliyun.com/?apiKey=1", "embedding": "text-embedding-v4", "models": ["qwen3.8-flash", "qwen3.7-plus", "qwen3.6-flash"],
     "desc": i18n.N_("通义千问")},
    {"id": "zhipu", "title": i18n.N_("智谱"), "base_url": "https://open.bigmodel.cn/api/paas/v4", "color": "#3859ff",
     "key_url": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys", "embedding": "embedding-3", "models": ["glm-5.3-flash", "glm-5v-turbo", "glm-4.6v"],
     "desc": i18n.N_("GLM 系列")},
    {"id": "moonshot", "title": "Kimi", "base_url": "https://api.moonshot.cn/v1", "color": "#16191e",
     "key_url": "https://platform.moonshot.cn/console/api-keys", "models": ["kimi-k3", "kimi-k2.6"],
     "desc": i18n.N_("月之暗面")},
    {"id": "ollama", "title": "Ollama", "base_url": "http://localhost:11434/v1", "color": "#5b5b63", "no_key": True,
     "embedding": "nomic-embed-text", "desc": i18n.N_("本机跑的模型，不用密钥"),
     "note": i18n.N_("用 Docker 部署时，地址写 http://host.docker.internal:11434/v1")},
    {"id": "custom", "title": i18n.N_("其他"), "base_url": "", "color": "#5b5b63",
     "desc": i18n.N_("任何兼容 OpenAI 的接口：vLLM、LM Studio、one-api……")},
]
PRESET = {p["id"]: p for p in PRESETS}
_PRESET_TITLES = {p["title"] for p in PRESETS}


def presets() -> list[dict]:
    """给界面的服务商列表：名字、说明按界面语言翻好（新的副本，不改 PRESETS）。"""
    return [p | {k: i18n.t(p[k]) for k in ("title", "desc", "note") if p.get(k)} for p in PRESETS]


def _title(t: str) -> str:
    """服务商的中文名（硅基流动……）按界面语言显示；用户自己起的名字原样。"""
    return i18n.t(t) if t in _PRESET_TITLES else t


def _stored_title(t: str) -> str:
    """界面上填回来的是翻好的名字（SiliconFlow）：存原文，换回中文界面时还能显示成“硅基流动”。"""
    return next((zh for zh in _PRESET_TITLES if t == i18n.t(zh, in_lang="en")), t)


_clients: dict[tuple, AsyncOpenAI] = {}
_models: dict[str, dict] = {}   # 名字 → {ts, models, error, note}


def _load() -> dict:
    r = conn.execute("select value from settings where key='providers'").fetchone()
    return json.loads(r[0]) if r else {}


def _store(d: dict):
    conn.execute("insert or replace into settings values('providers', ?)", (json.dumps(d),))
    conn.commit()


def apply():
    """config.yaml 里的加上界面里添加、改过的，放进 CFG['providers']。"""
    merged = {n: {**p, "source": "config"} for n, p in copy.deepcopy(BASE).items()}
    for n, p in _load().items():
        if n in merged:
            merged[n].update({k: v for k, v in p.items() if k in ("title", "base_url", "preset")})
        else:
            merged[n] = {**p, "source": "ui"}
    CFG["providers"] = merged
    _clients.clear()


# ---------- 密钥 ----------
def key_ref(name: str) -> str:
    return "LLM_KEY_" + re.sub(r"\W", "_", name.upper())


def api_key(name: str) -> str:
    v = vault.get(key_ref(name))
    if v:
        return v
    env = (CFG["providers"].get(name) or {}).get("api_key_env")
    return os.environ.get(env, "") if env else ""


def _local(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host in ("localhost", "host.docker.internal") or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


def needs_key(name: str) -> bool:
    p = CFG["providers"].get(name) or {}
    return not (PRESET.get(p.get("preset") or "", {}).get("no_key") or _local(p.get("base_url") or ""))


def exists(name: str) -> bool:
    return name in CFG["providers"]


def usable(name: str) -> bool:
    return name in CFG["providers"] and (bool(api_key(name)) or not needs_key(name))


def _hint(k: str) -> str:
    return "••••" + k[-4:] if len(k) >= 12 else "••••"


def describe(name: str) -> dict:
    p = CFG["providers"][name]
    in_vault = bool(vault.get(key_ref(name)))
    env = p.get("api_key_env") or ""
    from_env = not in_vault and bool(env and os.environ.get(env))
    k = api_key(name)
    m = _models.get(name) or {}
    return {
        "name": name, "title": _title(p.get("title") or PRESET.get(p.get("preset") or name, {}).get("title") or name),
        "preset": p.get("preset") or (name if name in PRESET else "custom"), "base_url": p["base_url"],
        "source": p.get("source", "config"), "key_env": env,
        "key_source": "vault" if in_vault else "env" if from_env else "",
        "key_hint": _hint(k) if k else "", "needs_key": needs_key(name),
        "models": len(m.get("models") or []), "error": m.get("error", ""), "checked": m.get("ts", 0),
    }


def public() -> list[dict]:
    return [describe(n) for n in CFG["providers"]]


# ---------- 客户端 ----------
def client(name: str, timeout: float | None = None) -> AsyncOpenAI:
    p = CFG["providers"].get(name)
    if not p:
        raise ValueError(i18n.t("没有这个模型服务：{name}", name=name))
    k = (p["base_url"], api_key(name) or "none", timeout)
    if k not in _clients:
        _clients[k] = AsyncOpenAI(base_url=k[0], api_key=k[1], max_retries=RETRIES, **({"timeout": timeout} if timeout else {}))
    return _clients[k]


# 额度用尽：不重试，调用方应停掉后续步骤。普通限流（rate_limit_exceeded 等）按 Retry-After 再试。
QUOTA_CODES = (
    "org_token_rate_limit_day",
    "insufficient_quota",
    "free_limit_reached",
    "budget_exceeded",
)


class ProviderLimit(Exception):
    """供应商拒绝继续调用。kind 是 quota（停）或 rate（已按 Retry-After 试过仍失败）。"""

    def __init__(self, kind: str, status: int, code: str, detail: str, retry_after: float | None = None):
        self.kind, self.status, self.code = kind, status, code
        self.detail, self.retry_after = detail, retry_after
        if kind == "quota":
            text = i18n.t("额度用尽（{status} {code}）。{detail}", status=status, code=code or "-", detail=detail)
        else:
            text = i18n.t("请求太频繁（{status} {code}）。{detail}", status=status, code=code or "-", detail=detail)
        super().__init__(text)


def _error_parts(e: openai.APIStatusError) -> tuple[str, str]:
    body = e.body
    err = body.get("error") if isinstance(body, dict) else None
    src = err if isinstance(err, dict) else body if isinstance(body, dict) else {}
    code = str(src.get("code") or src.get("type") or "").strip()
    message = str(src.get("message") or "").strip()
    if not message:
        message = str(getattr(e, "message", "") or e).strip()
    if not code:
        for known in QUOTA_CODES + ("rate_limit_exceeded",):
            if known in message:
                code = known
                break
    return code[:80], message[:300]


def _retry_after(e: openai.APIStatusError) -> float | None:
    """Retry-After / Retry-After-ms，秒。没有头再看 body 里的 retry_after。"""
    headers = getattr(getattr(e, "response", None), "headers", None)
    if headers is not None:
        for header, divisor in (("retry-after-ms", 1000.0), ("retry-after", 1.0)):
            raw = headers.get(header)
            if raw is None:
                continue
            try:
                return max(0.0, float(raw) / divisor)
            except (TypeError, ValueError):
                if header == "retry-after":
                    try:
                        parsed = email.utils.parsedate_tz(str(raw))
                        if parsed is not None:
                            return max(0.0, float(email.utils.mktime_tz(parsed) - time.time()))
                    except (TypeError, ValueError, OverflowError, OSError):
                        return None
                return None
    src = e.body if isinstance(e.body, dict) else {}
    err = src.get("error") if isinstance(src.get("error"), dict) else src
    if isinstance(err, dict) and err.get("retry_after") is not None:
        try:
            return max(0.0, float(err["retry_after"]))
        except (TypeError, ValueError):
            return None
    return None


async def _pause(seconds: float):
    """额度/限流的等待。测试替换这个函数，避免换掉 asyncio.sleep 把 HTTP 客户端卡住。"""
    await asyncio.sleep(seconds)


def classify_limit(e: Exception) -> ProviderLimit | None:
    """402，以及 429 里的日额度/配额码，是 quota。其余 429 是 rate。别的错误返回 None。"""
    if not isinstance(e, openai.APIStatusError):
        return None
    status = int(e.status_code or 0)
    code, detail = _error_parts(e)
    if status == 402 or (status == 429 and code != "rate_limit_exceeded" and any(c in f"{code} {detail}".lower() for c in QUOTA_CODES)):
        return ProviderLimit("quota", status, code, detail, None)
    if status == 429:
        return ProviderLimit("rate", status, code, detail, _retry_after(e))
    return None


def _effort_rejects() -> dict:
    r = conn.execute("select value from settings where key='effort_rejects'").fetchone()
    return json.loads(r[0]) if r else {}


def _effort_key(base: str, model: str) -> str:
    return f"{base.rstrip('/')}|{model}"


def effort_rejected(base: str, model: str, effort: str) -> bool:
    return effort in _effort_rejects().get(_effort_key(base, model), [])


def remember_effort_reject(base: str, model: str, effort: str):
    """模型服务对这个思考强度回了 400、不带就成功：记在设置表里（和 media.remember_test 一样）。"""
    d = _effort_rejects()
    k = _effort_key(base, model)
    if effort not in d.get(k, []):
        d[k] = d.get(k, []) + [effort]
        conn.execute("insert or replace into settings values('effort_rejects', ?)", (json.dumps(d),))
        conn.commit()


async def create_chat(client, **kwargs):
    """流式或非流式补全。额度类错误立刻抛出，不重试。普通 429 按 Retry-After 等，次数有上限。

    客户端自带的重试会把日额度 429 再打几遍，这里关掉，改由上面的分类决定。
    408/409/5xx 仍按 limits.provider_transient_retries 再试，避免把短暂故障变成任务失败。
    """
    rate_retries = max(0, int(CFG["limits"].get("provider_rate_retries", 1) or 0))
    transient_retries = max(0, int(CFG["limits"].get("provider_transient_retries", RETRIES) or 0))
    cap = max(0.0, float(CFG["limits"].get("provider_retry_cap_s", 120) or 0))
    # 测试里的假客户端没有 with_options。真客户端关掉 SDK 自带重试，避免把额度类 429 再打一遍。
    caller = client.with_options(max_retries=0) if hasattr(client, "with_options") else client
    base = str(getattr(client, "base_url", "") or "")
    if kwargs.get("reasoning_effort") and effort_rejected(base, kwargs.get("model", ""), kwargs["reasoning_effort"]):
        kwargs.pop("reasoning_effort")   # 以前这个模型就不认这个思考强度：直接不带
    rate_attempt = transient_attempt = 0
    while True:
        try:
            return await caller.chat.completions.create(**kwargs)
        except openai.BadRequestError as e:
            # 有的模型不认 reasoning_effort（比如 xAI 不收 max，有的推理模型什么强度都不收）：去掉再试一次，记下来以后不带
            effort = kwargs.pop("reasoning_effort", None)
            if not effort:
                raise
            try:
                r = await caller.chat.completions.create(**kwargs)
            except Exception:
                raise e from None
            remember_effort_reject(base, kwargs.get("model", ""), effort)
            log.warning("model %s rejected reasoning_effort=%s (400); retried without it", kwargs.get("model"), effort)
            return r
        except openai.APIStatusError as e:
            limit = classify_limit(e)
            if limit is not None and limit.kind == "quota":
                raise limit from e
            if limit is not None and limit.kind == "rate":
                if rate_attempt >= rate_retries:
                    raise limit from e
                delay = 1.0 if limit.retry_after is None else limit.retry_after
                await _pause(min(max(0.0, delay), cap))
                rate_attempt += 1
                continue
            status = int(e.status_code or 0)
            if status in (408, 409) or status >= 500:
                if transient_attempt >= transient_retries:
                    raise
                await _pause(min(0.5 * (2 ** transient_attempt), cap))
                transient_attempt += 1
                continue
            raise


class StreamStalled(Exception):
    """流开了，但很久没有新的块：服务那边卡住了。"""


def stream_idle_s() -> float:
    """流里两块之间最多等几秒。要比 Watchdog 的 3 分钟短，卡住的流才能先重来一次，而不是整个任务被取消。0 表示不限。"""
    return max(0.0, float(CFG["limits"].get("stream_idle_s", 120) or 0))


def stream_first_chunk_s() -> float:
    """流开了以后等第一块最多几秒。想得久的模型（高思考强度、不流式输出思考）第一块可能要两三分钟，
    所以单独算，默认 170，仍比 Watchdog 的 3 分钟短。0 表示不限。"""
    return max(0.0, float(CFG["limits"].get("stream_first_chunk_s", 170) or 0))


def stream_retries() -> int:
    """流中途卡住或断了（服务忙、连接断）时，同一轮再调几次。"""
    return max(0, int(CFG["limits"].get("stream_retries", 1) or 0))


def stream_retry_delay(attempt: int) -> float:
    """第 attempt 次重来之前等几秒：2、4 秒起步，加一点随机，最多 5 秒。服务忙（at capacity）时马上再调多半还是忙。"""
    base = min(5.0, 2.0 * attempt)
    return min(5.0, base + random.uniform(0, 1.0))


async def retry_pause(attempt: int):
    """流中途出错、重来之前的等待。测试替换这个函数，不用真等。"""
    await asyncio.sleep(stream_retry_delay(attempt))


async def guard_stream(stream, idle_s: float | None = None, first_s: float | None = None):
    """包住流式响应：第一块超过 first_s 秒、之后两块之间超过 idle_s 秒，就关掉流，抛 StreamStalled。"""
    idle = stream_idle_s() if idle_s is None else idle_s
    first = stream_first_chunk_s() if first_s is None else first_s
    it = stream.__aiter__()
    got = False
    while True:
        wait = idle if got else first
        try:
            chunk = await (asyncio.wait_for(it.__anext__(), wait) if wait > 0 else it.__anext__())
        except StopAsyncIteration:
            return
        except asyncio.TimeoutError:
            close = getattr(stream, "close", None) or getattr(stream, "aclose", None)
            if close:
                try:
                    await close()
                except Exception:
                    pass
            raise StreamStalled(i18n.t("模型 {n} 秒没有输出新内容", n=int(wait))) from None
        got = True
        yield chunk


def retry_midstream(e: Exception) -> bool:
    """流已经开了之后出的错，值不值得把这一轮重来：卡住、连接断、服务忙/临时故障可以，额度用尽和请求本身有问题不行。"""
    if isinstance(e, StreamStalled):
        return True
    if isinstance(e, ProviderLimit):
        return False
    if isinstance(e, openai.APIConnectionError):   # 含超时
        return True
    if isinstance(e, openai.APIStatusError):
        status = int(e.status_code or 0)
        return status in (408, 409) or status >= 500
    if isinstance(e, openai.APIError):   # SSE 里的 error 事件，没有状态码（比如 xAI 的 "at capacity"）
        text = f"{getattr(e, 'code', '') or ''} {e}".lower()
        return not any(c in text for c in QUOTA_CODES)
    return False


def explain(e: Exception, base_url: str = "") -> str:
    """把接口报错翻成一句人话。"""
    detail = ""
    if isinstance(e, openai.APIStatusError):
        body = e.body if isinstance(e.body, dict) else {}
        err = body.get("error") if isinstance(body.get("error"), dict) else body
        detail = str((err or {}).get("message") or e.message or "")[:200]
    if isinstance(e, openai.AuthenticationError):
        return i18n.t("密钥不对，或者已经失效（401）")
    if isinstance(e, openai.PermissionDeniedError):
        return i18n.t("没有权限（403）：可能没开通这个模型，或者账户欠费。{detail}", detail=detail)
    if isinstance(e, openai.NotFoundError):
        return i18n.t("找不到（404）：接口地址或模型名字不对。{detail}", detail=detail)
    if isinstance(e, openai.RateLimitError):
        return i18n.t("请求太多或余额不足（429）。{detail}", detail=detail)
    if isinstance(e, openai.APITimeoutError):
        return i18n.t("连接超时：{url}", url=base_url)
    if isinstance(e, openai.APIConnectionError):
        return i18n.t("连不上 {url}", url=base_url)
    if isinstance(e, openai.InternalServerError):
        return i18n.t("模型服务那边临时出了故障（{code}），一般过一会儿就好，稍后再试一次", code=e.status_code)
    if isinstance(e, openai.APIStatusError):
        return i18n.t("出错了（{code}）：{detail}", code=e.status_code, detail=detail)
    return f"{type(e).__name__}: {str(e)[:200]}"


def brief(e: Exception) -> str:
    """对话和任务里报错时用：调模型出的错翻成人话（不带英文原文和 request_id），别的错误原样。"""
    if not isinstance(e, openai.APIError):
        return str(e)
    url = getattr(getattr(e, "request", None), "url", None)
    return explain(e, f"{url.scheme}://{url.host}" if url else "")


# ---------- 模型列表 ----------
async def _list(base_url: str, key: str) -> list[str]:
    c = AsyncOpenAI(base_url=base_url, api_key=key or "none", timeout=15, max_retries=0)
    page = await c.models.list()
    return sorted({m.id for m in page.data if getattr(m, "id", None)})


async def check(base_url: str, key: str) -> dict:
    """拉一次模型列表，顺便验证地址和密钥。有的服务不提供列表（404），这时只能自己填模型名字。"""
    try:
        models = await _list(base_url, key)
        return {"ok": True, "models": models, "error": "", "note": "" if models else i18n.t("连上了，但是没有列出模型，选模型时直接填名字")}
    except openai.NotFoundError:
        return {"ok": True, "models": [], "error": "", "note": i18n.t("这个服务不提供模型列表，选模型时直接填名字")}
    except openai.AuthenticationError as e:
        return {"ok": False, "models": [], "error": explain(e) if key else i18n.t("要填 API Key 才能用"), "note": ""}
    except Exception as e:
        return {"ok": False, "models": [], "error": explain(e, base_url), "note": ""}


async def models(name: str, refresh: bool = False) -> dict:
    """这个服务有哪些模型，带上单价和能力。服务自己不列的，用 models.dev 里这一家的列表。"""
    from . import prices
    if name not in CFG["providers"]:
        raise ValueError(i18n.t("没有这个模型服务：{name}", name=name))
    m = _models.get(name)
    if refresh or not m or time.time() - m["ts"] > MODELS_TTL:
        if needs_key(name) and not api_key(name):
            m = {"ok": False, "models": [], "error": i18n.t("还没填 API Key"), "note": ""}
        else:
            m = await check(CFG["providers"][name]["base_url"], api_key(name))
        if m["ok"] and not m["models"] and (known := prices.models_of(name)):
            m.update(models=known, note=i18n.t("这个服务没有列出模型，下面是 models.dev 收录的，也可以直接填名字"))
        m["ts"] = time.time()
        _models[name] = m
    return {**m, "name": name, "items": prices.annotate(name, m["models"])}


# ---------- 增删改 ----------
def _clean_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not re.match(r"^https?://[^\s/]+", url):
        raise ValueError(i18n.t("接口地址要以 http:// 或 https:// 开头"))
    return url


def _new_name(base: str) -> str:
    base = re.sub(r"[^a-z0-9_]", "", base.lower()) or "custom"
    if not base[0].isalpha():
        base = "p" + base
    base, n, name = base[:28], 2, base[:28]
    while name in CFG["providers"]:
        name, n = f"{base}_{n}", n + 1
    return name


def same_origin(a: str, b: str) -> bool:
    """两个接口地址是不是同一个服务（协议、主机、端口都一样）。"""
    def origin(u: str):
        p = urlparse(u)
        try:
            port = p.port
        except ValueError:
            return None
        return p.scheme, (p.hostname or "").lower(), port or (443 if p.scheme == "https" else 80)
    return origin(a) is not None and origin(a) == origin(b)


def save(name: str | None, data: dict) -> str:
    """name 为空是新建。api_key 留空表示不改；clear_key 删掉界面里填的密钥（回到环境变量）。
    改到别的服务（主机或端口变了）时要重新填密钥：不然原来的密钥（可能是服务自己环境变量里的）会发到新地址去。"""
    d = _load()
    title = _stored_title((data.get("title") or "").strip()[:40])
    url = _clean_url(data.get("base_url", ""))
    preset = data.get("preset") if data.get("preset") in PRESET else None
    key = (data.get("api_key") or "").strip()
    if name is not None and name in CFG["providers"] and not key and api_key(name) \
            and not same_origin(url, CFG["providers"][name]["base_url"]):
        raise ValueError(i18n.t("换了接口地址要重新填 API Key（原来的密钥不会发给新地址）"))
    if name is None:
        name = _new_name(preset if preset and preset != "custom" else title or "custom")
        d[name] = {"title": title or PRESET.get(preset or "", {}).get("title") or name, "base_url": url, "preset": preset or "custom"}
    else:
        if name not in CFG["providers"]:
            raise ValueError(i18n.t("没有这个模型服务：{name}", name=name))
        d.setdefault(name, {}).update({"base_url": url, **({"title": title} if title else {})})
    if key:
        vault.put(key_ref(name), key)
    elif data.get("clear_key"):
        vault.delete(key_ref(name))
    _store(d)
    apply()
    _models.pop(name, None)
    return name


def users(name: str) -> list[str]:
    """哪些用途在用这个服务。"""
    out = [r for r, v in CFG["roles"].items() if v.get("provider") == name]
    if (CFG.get("embedding") or {}).get("provider") == name:
        out.append("embedding")
    return out


def delete(name: str, role_names: dict):
    if name not in CFG["providers"]:
        raise ValueError(i18n.t("没有这个模型服务：{name}", name=name))
    if CFG["providers"][name].get("source") == "config":
        raise ValueError(i18n.t("这个是 config.yaml 里写的，要在那里删"))
    if u := users(name):
        raise ValueError(i18n.t("{roles}还在用它，先换成别的模型", roles=i18n.t("、").join(i18n.t(role_names.get(x, x)) for x in u)))
    d = _load()
    d.pop(name, None)
    _store(d)
    vault.delete(key_ref(name))
    _models.pop(name, None)
    apply()


# ---------- 测试一个模型 ----------
def _png(w: int, h: int, rgb: tuple) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


RED = "data:image/png;base64," + base64.b64encode(_png(64, 64, (220, 30, 30))).decode()


def _effort_note(rejected: list) -> dict:
    if not rejected:
        return {}
    return {"effort_rejected": rejected[0],
            "effort_warning": i18n.t("这个模型不认思考强度 {effort}，已改为不带它调用", effort=rejected[0])}


async def test(provider: str, model: str, kind: str = "chat", role: str = "") -> dict:
    """真的调一次：chat 先带一张红色图片问颜色，看能不能看图；不支持图片再只发文字。embedding 算一条向量。"""
    from . import memory
    if provider not in CFG["providers"]:
        raise ValueError(i18n.t("没有这个模型服务：{name}", name=provider))
    if not (model or "").strip():
        raise ValueError(i18n.t("先选一个模型"))
    base = CFG["providers"][provider]["base_url"]
    c = AsyncOpenAI(base_url=base, api_key=api_key(provider) or "none", timeout=60, max_retries=0)
    t0 = time.time()
    ms = lambda: int((time.time() - t0) * 1000)
    if kind == "embedding":
        try:
            r = await c.embeddings.create(model=model, input=["connectivity check"])
            return {"ok": True, "dim": len(r.data[0].embedding), "ms": ms()}
        except Exception as e:
            return {"ok": False, "error": explain(e, base), "ms": ms()}

    from .config import call_kwargs
    kw = call_kwargs(role) if role in CFG["roles"] else {}   # 按这个用途的设置（思考模式等）来测

    rejected = []   # 这个用途设的思考强度被模型服务拒了（400，不带就成功）

    async def ask(content) -> str:
        args = dict(model=model, max_tokens=512, messages=[{"role": "user", "content": content}], **kw)
        try:
            r = await c.chat.completions.create(**args)
        except openai.BadRequestError:
            if not kw.get("reasoning_effort"):
                raise
            args.pop("reasoning_effort")
            r = await c.chat.completions.create(**args)
            rejected.append(kw.pop("reasoning_effort"))
            remember_effort_reject(base, model, rejected[-1])
        memory.record_usage("test", model, r.usage, provider=provider)
        msg = r.choices[0].message if r.choices else None
        return ((msg.content if msg else "") or getattr(msg, "reasoning_content", "") or "").strip()

    try:
        reply = await ask([{"type": "text", "text": "What color is this image? Reply with the color only."}, {"type": "image_url", "image_url": {"url": RED}}])
        seen = "红" in reply or "red" in reply.lower()
        if not seen:   # 请求没报错，但没认出颜色：可能是服务把图片丢掉了，参考 models.dev 的记录
            from . import prices
            seen = {False: "no", True: "unsure"}.get(prices.lookup(provider, model).get("vision"), "unsure")
        from . import media
        media.remember_test(provider, model, "yes" if seen is True else seen)   # 以后按测出来的判断要不要给它看图
        return {"ok": True, "vision": "yes" if seen is True else seen, "reply": reply[:80], "ms": ms(), **_effort_note(rejected)}
    except (openai.AuthenticationError, openai.PermissionDeniedError, openai.APIConnectionError, openai.RateLimitError) as e:
        return {"ok": False, "error": explain(e, base), "ms": ms()}
    except Exception as e:
        img_err = explain(e, base)
    try:
        t0 = time.time()
        reply = await ask("Reply with exactly: ok")
        from . import media
        media.remember_test(provider, model, "no")
        return {"ok": True, "vision": "no", "vision_error": img_err, "reply": reply[:80], "ms": ms(), **_effort_note(rejected)}
    except Exception as e:
        return {"ok": False, "error": explain(e, base), "ms": ms()}
