"""Worker：隔离的 ReAct 循环，带工具，单独执行一个任务。模型流式输出，每一步都记进任务过程（tasklog）。"""

from .i18n import s as _s
import asyncio
import json
import time
from dataclasses import dataclass, field
from .config import CFG, call_kwargs, client_for
from . import approvals, library, memories, memory, mcp_hub, search, tasklog, tools
from .computer import tools as ctools

PROGRESS = None   # 由 router 设置：async (task, text) -> None，把动作推送到任务卡片
PAGES_CHANGED = None   # 由 server 设置：async () -> None，资料库有新页面时通知前端

from . import i18n



@dataclass
class Task:
    id: int
    goal: str
    mode: str = "single"                   # single | heavy
    bot_id: int = 0
    chat_id: int = 0
    status: str = "running"                # running | done | failed | cancelled
    started: float = field(default_factory=time.time)
    last_progress: float = field(default_factory=time.time)
    steps: int = 0
    recent_calls: list = field(default_factory=list)
    waiting_approval: int | None = None    # 正在等用户确认的请求 id
    background: bool = False               # 定时 / webhook 触发的任务：确认卡片会过期
    paused_s: float = 0                    # 等用户确认花掉的时间，不算进超时
    last_action: str = ""                  # 最近一个动作，显示在任务卡片上
    result: str = ""
    handle: asyncio.Task | None = None
    on_done: object = None                 # 定时任务用：async (task) -> None，任务结束时调用
    approval_chat_id: int = 0              # 确认卡片发到哪个对话：总是 Bot 的私聊（群聊里派的任务也一样）
    handoff: dict | None = None            # 群聊：做完后把结果交给谁 {"to": bot_id, "note": str}
    reply: dict | None = None              # 因私信派的任务：做完把结果作为回信送给谁（见 dm.py）
    depth: int = 0                         # 派任务那一轮的私信深度，交接、回信沿用


def _public(self) -> dict:
    return {"id": self.id, "goal": self.goal, "mode": self.mode, "status": self.status, "steps": self.steps,
            "bot_id": self.bot_id, "chat_id": self.chat_id, "started": self.started,
            "waiting_approval": self.waiting_approval, "last_action": self.last_action, "elapsed": round(time.time() - self.started)}


Task.public = _public


async def run_worker(task: Task, goal: str, label: str = "") -> str:
    ctools.CLAIM.set(f"{task.id}:{label}")
    try:
        return await _run_worker(task, goal, label)
    finally:
        await ctools.release()   # 任务结束（含取消、失败）就把电脑让给排队的任务


async def _reply(task: Task, log: tasklog.Log, role: str, client, model: str, msgs: list, tools_: list | None = None) -> dict:
    """流式调用一次模型，思考和正文边收边写进任务过程。返回这一轮的 assistant 消息，可以直接接到 msgs 后面。"""
    stream = await client.chat.completions.create(model=model, messages=msgs, stream=True,
                                                  stream_options={"include_usage": True},
                                                  **({"tools": tools_} if tools_ else {}), **call_kwargs(role))
    content, reasoning, calls, usage = "", "", {}, None
    think = text = None
    async for chunk in stream:
        task.last_progress = time.time()   # 还在出字就算有进展，Watchdog 不会当成卡住
        if chunk.usage:
            usage = chunk.usage
        if not chunk.choices:
            continue
        d = chunk.choices[0].delta
        if rc := getattr(d, "reasoning_content", None):
            reasoning += rc
            if not think or think["status"] != "running":
                think = await log.start("think")
            await log.append(think, rc)
        if d.content:
            content += d.content
            if think:
                await log.finish(think)
            if not text or text["status"] != "running":
                text = await log.start("text")
            await log.append(text, d.content)
        for tc in d.tool_calls or []:
            c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
            c["id"] = tc.id or c["id"]
            if tc.function:
                c["name"] += tc.function.name or ""
                c["args"] += tc.function.arguments or ""
    memory.record_usage(role, model, usage, task.id)
    if think:
        await log.finish(think)
    if text:
        await log.finish(text, kind="say" if calls else "answer")
    msg = {"role": "assistant"}
    if content:
        msg["content"] = content
    if reasoning:   # DeepSeek 思考模式：带工具的请求要把 reasoning_content 原样传回
        msg["reasoning_content"] = reasoning
    if calls:
        msg["tool_calls"] = [{"id": c["id"] or f"call_{k}", "type": "function",
                              "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                             for k, c in sorted(calls.items(), key=lambda kv: kv[0] or 0)]
    return msg


async def _tool(task: Task, log: tasklog.Log, step: dict, name: str, raw: str, progress, pages: bool,
                shots: list) -> tuple[str, str]:
    """执行一个工具调用，返回 (给模型的结果, 这一步的状态)。工具出错交给模型自己处理。"""
    try:
        args = json.loads(raw or "{}")
        if name in ctools.NAMES:
            out, shot = await ctools.call(task, name, args, progress)
            if shot:
                shots.append(shot)
            return out, "done"
        if name == "search_memory":
            await progress(i18n.s("prog_search_memory", q=str(args.get("query", ""))[:40]))
            return await search.tool(task.bot_id, args), "done"
        if name == "read_page":
            await progress(i18n.s("prog_read_page", id=args.get("page_id")))
            return library.tool_read_page(args), "done"
        if name == "save_page" and pages:
            await progress(i18n.s("prog_save_page", title=str(args.get("title", ""))[:40]))
            out = library.tool_save_page(task.bot_id, args, task.id)
            if PAGES_CHANGED:
                await PAGES_CHANGED()
            return out, "done"
        await progress({"web_search": i18n.s("prog_web_search"), "fetch_url": i18n.s("prog_fetch_url")}.get(name, name + " ")
                       + str(args.get("query") or args.get("url") or "")[:60])
        fn = tools.lookup(name)
        if fn and name in mcp_hub.TOOLS and approvals.decide(name)[0]:
            await log.update(step, status="waiting")
            ok, note = await approvals.request(task, name, args)
            if not ok:
                return i18n.s("tool_rejected", note=note or "").strip(), "rejected"
            await log.update(step, status="running")
        return (await fn(**args) if fn else i18n.s("tool_unknown")), "done"
    except Exception as e:
        return i18n.s("tool_error", e=e), "error"


async def _run_worker(task: Task, goal: str, label: str = "") -> str:
    client, model = client_for("worker")
    use_pc = (CFG.get("computer") or {}).get("enabled", True)
    pages = not label   # Heavy 模式的几个 Worker 只出草稿，不各自存页面
    system = i18n.prompt("WORKER_PROMPT", date=time.strftime("%Y-%m-%d")) + ("\n" + i18n.prompt("PAGE_HINT") if pages else "") \
        + ("\n\n" + i18n.prompt("SYSTEM_HINT") if use_pc else "")
    if known := memories.worker_block(task.bot_id):
        system += f"\n\n{i18n.s('worker_memory_prefix')}\n{known}"
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": goal}]
    schemas = i18n.localize_tools(
        tools.schemas() + ([library.SAVE_PAGE] if pages else []) + [library.READ_PAGE, search.SEARCH_TOOL]
        + (ctools.SCHEMAS if use_pc else []))
    log = tasklog.Log(task, label)

    async def progress(text: str):
        task.last_action = text
        if log.current:
            await log.update(log.current, title=text)
        if PROGRESS:
            await PROGRESS(task, text)

    for _ in range(CFG["limits"]["worker_max_steps"]):
        ctools.prune_images(msgs)
        m = await _reply(task, log, "worker", client, model, msgs, schemas)
        task.steps += 1
        task.last_progress = time.time()
        if not m.get("tool_calls"):
            return m.get("content") or ""
        msgs.append(m)
        shots = []   # 截图要等这一轮的工具结果都追加完再附上
        for call in m["tool_calls"]:
            name, raw = call["function"]["name"], call["function"]["arguments"]
            task.recent_calls = (task.recent_calls + [f"{name}:{raw}"])[-6:]
            step = log.current = await log.start("tool", name, detail=raw[:2000])
            out, status = await _tool(task, log, step, name, raw, progress, pages, shots)
            msgs.append({"role": "tool", "tool_call_id": call["id"], "content": out[:8000]})
            await log.finish(step, status, out)
            task.last_progress = time.time()
        if shots:
            msgs.append(ctools.image_message(shots[-1]))
    await log.note(_s('audit_c64c6a8e6c'))
    msgs.append({"role": "user", "content": _s('audit_d35bb90aba')})
    m = await _reply(task, log, "worker", client, model, msgs)
    return m.get("content") or ""


async def run_heavy(task: Task) -> str:
    """Heavy 模式：N 个 Worker 独立并行解题，Reviewer 互审后汇总。"""
    n = CFG["heavy"]["workers"]
    angles = [_s('audit_c7e2158d8a'), _s('audit_e9549aadca'), _s('audit_129253b067'), _s('audit_83caaf0b6b')]
    await tasklog.Log(task).note(_s('audit_672ff8258b', v0=n))
    drafts = await asyncio.gather(*[
        run_worker(task, _s('audit_9bd16b31e2', v0=task.goal, v1=i + 1, v2=angles[i % len(angles)]), f"h{i}")
        for i in range(n)], return_exceptions=True)
    for i, d in enumerate(drafts):
        if isinstance(d, Exception):
            await tasklog.Log(task, f"h{i}").note(_s('audit_1f38aff486', v0=d), "error")
    drafts = [d for d in drafts if isinstance(d, str)]
    client, model = client_for("reviewer")
    joined = "\n\n".join(_s('audit_33f8e036e9', v0=i + 1, v1=d) for i, d in enumerate(drafts))
    await tasklog.Log(task).note(_s('audit_b74cb95e35', v0=len(drafts)))
    m = await _reply(task, tasklog.Log(task, "review"), "reviewer", client, model, [
        {"role": "system", "content": _s('audit_ed2efa014b')},
        {"role": "user", "content": _s('audit_56671e8a4e', v0=task.goal, v1=joined)}])
    return m.get("content") or ""
