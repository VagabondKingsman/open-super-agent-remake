"""Locale packs for system prompts and backend user-facing strings.

Set OSA_LOCALE=vi|en|zh (default: vi). Falls back to English, never silently to Chinese in Vietnamese mode.
Keys stay stable across locales so upstream merges stay clean.
"""
from __future__ import annotations

import os
from functools import lru_cache
from importlib import import_module
from typing import Any

SUPPORTED = ("vi", "en", "zh")
DEFAULT = "vi"
FALLBACKS = ("en",)

_override: str | None = None


def set_locale(loc: str | None) -> str:
    """Runtime locale override (Settings API). Pass None to clear."""
    global _override
    loc = (loc or "").strip().lower() or None
    if loc and loc not in SUPPORTED:
        raise ValueError(f"unsupported locale: {loc}")
    _override = loc
    clear_cache()
    return get_locale()


def get_locale() -> str:
    if _override in SUPPORTED:
        return _override  # type: ignore
    loc = (os.environ.get("OSA_LOCALE") or DEFAULT).strip().lower()
    return loc if loc in SUPPORTED else DEFAULT


@lru_cache(maxsize=8)
def _pack(locale: str) -> Any:
    return import_module(f"osa.locales.{locale}")


def _resolve(locale: str, attr: str, default: str | None = None) -> str:
    for loc in (locale, *FALLBACKS):
        if loc not in SUPPORTED:
            continue
        mod = _pack(loc)
        if hasattr(mod, attr):
            return getattr(mod, attr)
    if default is not None:
        return default
    raise AttributeError(f"i18n key missing: {attr}")


def prompt(key: str, **kwargs) -> str:
    """Load a prompt template by key and format placeholders."""
    text = _resolve(get_locale(), key)
    return text.format(**kwargs) if kwargs else text


@lru_cache(maxsize=8)
def _strings(locale: str) -> dict:
    import json
    from pathlib import Path
    path = Path(__file__).parent / "locales" / locale / "strings.json"
    return {**getattr(_pack(locale), "STRINGS", {}),
            **(json.loads(path.read_text()) if path.exists() else {})}


def strings() -> dict:
    """Current strings for standalone helpers; no credentials or user data."""
    out = {}
    for locale in reversed((get_locale(), *FALLBACKS)):
        out.update(_strings(locale))
    return out


def s(key: str, **kwargs) -> str:
    """Short user-facing string from the current locale pack."""
    for candidate in (get_locale(), *FALLBACKS):
        values = _strings(candidate)
        if key in values:
            text = values[key]
            return text.format(**kwargs) if kwargs else text
    return key


def clear_cache():
    _pack.cache_clear()
    _strings.cache_clear()


def tool_pack() -> dict:
    """Tool schema text overlays for the current locale."""
    import json
    from pathlib import Path
    loc = get_locale()
    for candidate in (loc, *FALLBACKS):
        path = Path(__file__).parent / "locales" / candidate / "tools.json"
        if path.exists():
            return json.loads(path.read_text())
    return {}


def localize_tools(schemas: list) -> list:
    """Return a deep-copied tool schema list with descriptions overlaid from locale packs."""
    from copy import deepcopy
    pack = tool_pack()
    out = []
    for schema in schemas:
        s = deepcopy(schema)
        fn = (s.get("function") or {}).get("name")
        if fn and fn in pack:
            info = pack[fn]
            if info.get("description"):
                s["function"]["description"] = info["description"]
            props = (s["function"].get("parameters") or {}).get("properties") or {}
            for pname, pdesc in (info.get("params") or {}).items():
                if pname in props and isinstance(props[pname], dict):
                    props[pname]["description"] = pdesc
        out.append(s)
    return out


def task_dispatch_goal(text: str) -> str:
    import re
    return re.sub(r"^\[(?:任务已派发|Đã giao task|Task dispatched)\]\s*", "", text or "")


def task_result_body(text: str) -> str:
    import re
    return re.sub(r"^\[(?:任务 #\d+ 结果|Kết quả task #\d+|Task #\d+ result)\]\s*", "", text or "")


LEGACY_ROUTINE_DEFAULTS = ("legacy_routine_news", "legacy_routine_github", "legacy_routine_github_filter")


def legacy_routine_default(text: str) -> str:
    """Translate only exact upstream seeded defaults, never arbitrary user instructions."""
    for key in LEGACY_ROUTINE_DEFAULTS:
        if any(text == _strings(loc).get(key) for loc in SUPPORTED):
            return s(key)
    return text


def _legacy_schedule(text: str) -> str:
    import re
    if match := re.fullmatch(r"每\s*(\d+)\s*(小时|分钟)", text):
        return s("routine_every_hours" if match[2] == "小时" else "routine_every_minutes", n=match[1])
    if text.startswith("每天 "):
        return s("routine_daily", times=text[3:].replace("、", s("list_join")))
    if match := re.fullmatch(r"每周([一二三四五六日、]+) (.+)", text):
        days = s("list_join").join(s(f"weekday_{'一二三四五六日'.index(day) + 1}") for day in match[1] if day != "、")
        return s("routine_weekly", days=days, times=match[2].replace("、", s("list_join")))
    if text in ("收到 webhook 时", "收到 webhook", "webhook"):
        return s("routine_webhook")
    return text


def localize_task_goal(text: str) -> str:
    """Read-time projection of known old task chrome; leaves free-form content untouched."""
    import re
    text = task_dispatch_goal(text)
    if get_locale() == "zh":
        return text
    text = re.sub(r"\[定时任务 ([^\]]+)\]", lambda m: s("routine_task_label", name=m[1]), text)
    text = re.sub(r"这是定时任务「([^」]+)」（([^）]+)）的一次运行。",
                  lambda m: s("routine_run_intro", name=m[1], when=_legacy_schedule(m[2])), text)
    text = re.sub(r"^要求：", lambda _: s("routine_run_prompt", prompt=""), text, flags=re.M)
    text = re.sub(r"^按技能 /([^\s]+) 的做法执行：", lambda m: s("routine_run_skill", name=m[1], body="").rstrip(), text, flags=re.M)
    text = re.sub(r"^触发事件：", lambda _: s("routine_run_event", event="").rstrip(), text, flags=re.M)
    for key in LEGACY_ROUTINE_DEFAULTS:
        old = _strings("zh").get(key)
        if old:
            text = text.replace(old, s(key))
    return text
