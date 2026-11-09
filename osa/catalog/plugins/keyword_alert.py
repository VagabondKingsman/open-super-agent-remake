"""关键词提醒：哪个对话里（群聊、别的 Bot 的私聊、Telegram、钉钉……）出现了你关心的词，在一个 Bot 的私聊里提醒你一声。

比如盯着“紧急”“urgent”“线上故障”：消息发在别处、你没在看时，也能在常看的那个私聊里看到。
设置：keywords（要盯的词，列表，不分大小写）；bot（提醒发到哪个 Bot 的私聊，名字，不填是主 Bot）；
cooldown_minutes（同一个对话里同一个词，多久之内只提醒一次，默认 30）。
只是旁观（订阅 user_message 事件）：不调模型、不花钱，不影响消息本身。发在提醒用的那个私聊里的消息不提醒。
"""
import re
import time
from osa import bots, i18n

META = {"title": "关键词提醒", "version": "1.0", "author": "open-super-agent", "inject": ["messenger"],
        "config": {"keywords": [], "bot": "", "cooldown_minutes": 30}}
VIA = {"telegram": "Telegram", "feishu": i18n.N_("飞书"), "dingtalk": i18n.N_("钉钉"), "wecom": i18n.N_("企业微信"), "discord": "Discord"}
SNIPPET = 80


def hits(text: str, keywords: list[str]) -> list[str]:
    low = (text or "").lower()
    return [k for k in keywords if k.lower() in low]


def snippet(text: str, word: str, n: int = SNIPPET) -> str:
    """词附近的一段：前面留一点，后面多留一点。"""
    t = re.sub(r"\s+", " ", text or "").strip()
    i = t.lower().find(word.lower())
    a = max(0, i - n // 3) if i >= 0 else 0
    out = t[a:a + n]
    return ("…" if a > 0 else "") + out + ("…" if a + n < len(t) else "")


def where(chat: dict, via: str) -> str:
    title = chat.get("title") or f"#{chat.get('id')}"
    s = i18n.t("群「{title}」", title=title) if chat.get("kind") == "group" else i18n.t("和「{title}」的私聊", title=title)
    if chat.get("parent"):
        s = i18n.t("{where}的讨论串", where=s)
    if via:
        s = i18n.t("{where}（{via}）", where=s, via=i18n.t(VIA[via]) if via in VIA else via)
    return s


class Cooldown:
    """同一个对话里同一个词，cooldown 秒内只放行一次。"""

    def __init__(self, seconds: float):
        self.seconds = seconds
        self.last: dict[tuple, float] = {}

    def allow(self, chat_id, word: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        key = (chat_id, word.lower())
        if now - self.last.get(key, -1e18) < self.seconds:
            return False
        self.last[key] = now
        if len(self.last) > 1000:   # 别越攒越多：扔掉冷却早过了的
            self.last = {k: t for k, t in self.last.items() if now - t < self.seconds}
        return True


def notice(chat: dict, via: str, text: str, words: list[str]) -> str:
    quoted = i18n.t("、").join(i18n.t("「{word}」", word=w) for w in words)
    return i18n.t("🔔 {where}里有人提到了{words}：{snippet}", where=where(chat, via), words=quoted, snippet=snippet(text, words[0]))


def apply(ctx):
    kws = ctx.config.get("keywords")
    if isinstance(kws, str):
        kws = re.split(r"[\n,，]+", kws)
    kws = list(dict.fromkeys(str(k).strip() for k in kws or [] if str(k).strip()))
    if not kws:
        raise ValueError(i18n.t("先在设置里填 keywords（要盯的词的列表，比如 [\"紧急\", \"urgent\"]）"))
    try:
        cool = Cooldown(max(0.0, float(ctx.config.get("cooldown_minutes", 30) or 0)) * 60)
    except (TypeError, ValueError):
        raise ValueError(i18n.t("cooldown_minutes 要是分钟数")) from None
    name = ctx.config.get("bot") or None
    messenger = ctx.services["messenger"]

    async def on_message(chat, text, via="", **_):
        words = hits(text, kws)          # 绝大多数消息到这里就结束了，只做一次字符串查找
        if not words or not isinstance(chat, dict):
            return
        b = bots.by_name(name) if name else bots.primary()
        if not b:
            ctx.log.warning("关键词提醒：没有 Bot %s", name)
            return
        if b["chat_id"] in (chat.get("id"), chat.get("parent")):
            return                       # 就在提醒用的私聊里说的，不用再提醒
        root = chat.get("parent") or chat.get("id")
        words = [w for w in words if cool.allow(root, w)]
        if not words:
            return
        try:
            await messenger.post(notice(chat, via, text, words), bot=b["id"])
        except Exception as e:
            ctx.log.warning("关键词提醒没发出去：%s", e)

    ctx.on("user_message", on_message)
