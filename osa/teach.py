"""演示一遍（Teach a task）：用户在共用电脑上做一遍，Bot 把录到的操作整理成技能草稿，用户审核后保存。

- 开始：电脑没被任务占着时，先占住（任务会排队），在电脑里启动录制进程（cdp_helper.py 的 record），再把控制权交给用户。
- 录制只记浏览器里的操作：打开的网址、点击的元素、输入的内容（密码类只记 ******）、选择、回车。
- 结束：停掉录制，交还控制权，把操作排成文字交给模型，生成技能草稿（名字、说明、做法）；不自动保存。
- 最长 MAX_S 秒，到时自动结束并生成草稿，通过 teach 事件推给前端。
"""

from .i18n import s as _s
import asyncio
import json
import re
import time
from urllib.parse import urlparse
from .config import call_kwargs, client_for
from . import computer, memory, skills

MAX_S = 600
KEY = "teach"
state: dict | None = None      # {"bot_id", "started", "note", "file"}
notify = None                  # 由 server 设置
_timer: asyncio.Task | None = None


def public() -> dict | None:
    return {k: state[k] for k in ("bot_id", "started", "note")} | {"max_s": MAX_S} if state else None


async def _changed(extra: dict | None = None, pc: int | None = None):
    if notify:
        if pc is not None:   # 接手 / 交还要马上反映到电脑画面上
            await notify({"type": "computer", "computer": await computer.public_state(pc)})
        await notify({"type": "teach", "teach": public()} | (extra or {}))


async def start(bot_id: int, note: str = "") -> dict:
    global state, _timer
    if state:
        raise ValueError(_s('audit_5dfe435c23'))
    c = computer.get()
    if c.owner:
        raise ValueError(_s('audit_51f260123a', v0=c.owner_label))
    await c.start()
    await c.claim(KEY, _s('audit_68c5a791ae'))
    path = f"/tmp/osa-rec-{int(time.time())}.jsonl"
    try:
        await c.browser("rec_start", as_human=True, file=path, max_s=MAX_S + 30)
    except Exception:
        await c.release(KEY)
        raise
    c.takeover()
    state = {"bot_id": bot_id, "started": time.time(), "note": (note or "").strip()[:500], "file": path}
    _timer = asyncio.create_task(_auto_stop(state["started"]))
    await _changed(pc=bot_id)
    return public()


async def _auto_stop(started: float):
    await asyncio.sleep(MAX_S)
    if state and state["started"] == started:
        try:
            result = await stop()
            await _changed({"bot_id": result["bot_id"], "draft": result["draft"], "steps": result["steps"], "auto": True})
        except Exception as e:
            await _changed({"error": _s('audit_79b5db0ee2', v0=e)})


async def _finish() -> tuple[dict, list[dict]]:
    """停掉录制、交还电脑，返回 (录制信息, 录到的操作)。"""
    global state, _timer
    if not state:
        raise ValueError(_s('audit_638d704a8f'))
    s, state = state, None
    if _timer and _timer is not asyncio.current_task():
        _timer.cancel()
    _timer = None
    c = computer.get()
    try:
        r = await c.browser("rec_stop", as_human=True, file=s["file"])
        events = r.get("events") or []
    finally:
        c.handback()
        await c.release(KEY)
        await _changed(pc=s["bot_id"])
    return s, events


async def cancel():
    await _finish()


async def stop() -> dict:
    s, events = await _finish()
    steps = describe(events, s["started"])
    if not steps:
        raise ValueError(_s('audit_3bf2bc52aa'))
    draft = await draft_skill(steps, s["note"])
    return {"bot_id": s["bot_id"], "draft": draft, "steps": steps}


# ---------- 整理 ----------
def describe(events: list[dict], started: float) -> list[str]:
    """把录到的事件排成一行一步的文字；合并重复的输入，去掉连续的同一网址。"""
    out, last_url, last = [], "", None
    for e in events:
        kind = e.get("type")
        sig = json.dumps({k: v for k, v in e.items() if k not in ("t", "title", "url")}, ensure_ascii=False, sort_keys=True)
        if kind == "input" and last and last[0] == "input" and last[1] == e.get("field"):
            out.pop()            # 同一个输入框连续记了几次（回车时一次、失去焦点时一次），只留最后一次
        elif sig == (last[2] if last else None) and kind != "navigate":
            continue
        when = time.strftime("%M:%S", time.gmtime(max(0, (e.get("t") or started) - started)))
        if kind == "navigate":
            url = e.get("url", "")
            if url == last_url:
                continue
            last_url = url
            verb = _s('audit_7fff8897be') if e.get("start") else _s('audit_86669b1e7a') if e.get("new_tab") else _s('audit_5df11f8bfb')
            line = f"{verb} {url}" + (f"（{e['title']}）" if e.get("title") else "")
        elif kind == "click":
            line = _s('audit_3b9cf5b57c', v0=e.get('kind', _s('audit_74f529b607')), v1=e.get('name') or _s('audit_5e30dd0e88')) + (f" → {e['href']}" if e.get("href") else "")
        elif kind == "input":
            line = _s('audit_a9a0e3c2fd', v0=e.get('field') or _s('audit_02be516690'), v1=e.get('value', '')) + (_s('audit_8ac4dfbcaa') if e.get("secret") else "") \
                + (_s('audit_76f8bcf9a8') if e.get("submit") else "")
        elif kind == "select":
            line = _s('audit_c1cc8a7f30', v0=e.get('field') or _s('audit_2c2c1ef2a4'), v1=e.get('value', ''))
        elif kind == "check":
            line = f"{_s('audit_dc28a37577') if e.get('checked') else _s('audit_2e9d3f1a84')}「{e.get('field', '')}」"
        elif kind == "key":
            line = _s('audit_bf8c32138b', v0=e.get('key'))
        else:
            continue
        if kind != "navigate" and e.get("url") and urlparse(e["url"]).netloc != urlparse(last_url).netloc:
            line += _s('audit_1ba9c91ece', v0=urlparse(e['url']).netloc)
        out.append(f"{when} {line}")
        last = (kind, e.get("field"), sig)
    return out[-300:]


DRAFT_PROMPT = _s('audit_036378d027')


def _parse(text: str) -> dict:
    """模型偶尔会在 JSON 外面包代码块或多说一句：先整段解析，不行就取最外层的 {...}。"""
    for s in (text, (m.group(0) if (m := re.search(r"\{[\s\S]*\}", text or "")) else "")):
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                return d
        except ValueError:
            pass
    return {}


async def draft_skill(steps: list[str], note: str = "") -> dict:
    client, model = client_for("router")
    user = (_s('audit_968020e28e', v0=note) if note else "") + _s('audit_7aaaf21266') + "\n".join(steps)
    d = {}
    for _ in range(2):   # 解析不出来就再问一次
        resp = await client.chat.completions.create(model=model, messages=[
            {"role": "system", "content": _s("audit_036378d027")}, {"role": "user", "content": user}],
            response_format={"type": "json_object"}, **call_kwargs("router"))
        memory.record_usage("router", model, resp.usage)
        d = _parse(resp.choices[0].message.content or "")
        if d.get("body"):
            break
    name = re.sub(r"[^\w一-鿿-]", "", str(d.get("name") or ""))[:40]
    if not name or not skills.NAME_RE.match(name):
        name = _s('audit_6d2a6282a2', v0=time.strftime('%m%d%H%M'))
    body = str(d.get("body") or "").strip() or _s('audit_7a1f5f635d') + "\n".join(steps)
    return {"name": name, "description": str(d.get("description") or note or "")[:200], "body": body[:8000]}
