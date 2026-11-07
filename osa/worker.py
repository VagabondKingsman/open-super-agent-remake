"""Worker：隔离的 ReAct 循环，带工具，单独执行一个任务。模型流式输出，每一步都记进任务过程（tasklog）。"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from .config import CFG, call_kwargs, client_for
from .providers import ProviderLimit, create_chat
from . import approvals, i18n, library, memories, memory, mcp_hub, search, skillpacks, tasklog, tools, verification, local_checks
from .computer import tools as ctools

PROGRESS = None   # 由 router 设置：async (task, text) -> None，把动作推送到任务卡片
PAGES_CHANGED = None   # 由 server 设置：async () -> None，资料库有新页面时通知前端

WORKER_PROMPT = """你是执行任务的 Worker。用工具查证事实，给出结论时附上来源链接。
需要读写用户的外部服务（应用）时，使用名字带“应用名__”前缀的工具；任务里写了“@应用名”就必须用那个应用。
写操作会先请用户确认；被拒绝时不要换个工具绕过去，按用户的意见调整或说明无法完成。
只做任务里写明的事。任务没要求保存页面、搜索记忆或改资料库时，不要调用 save_page、search_memory、read_page。
完成后直接输出最终答案（{lang}，简洁、结构清晰）。不要只输出思考过程。今天是 {date}。"""
# 最终答案用什么语言。模型仍可能跑偏，这里只是指令，不做输出校验。
ANSWER_LANG = {
    "vi": "必须用越南语；只有任务原文是别的语言时才用那种语言，不要换成第三种语言",
    "zh": "中文",
    "en": "必须用英文；只有任务原文是别的语言时才用那种语言，不要换成第三种语言",
}
PAGE_HINT = "任务要求做成页面或报告时，用 save_page 保存，最终答案里附上返回的链接。"
# 写给模型的续写提示，保持中文。用户看见的失败说明走 i18n.t。
CONTINUE_PROMPT = "上一次没有给出完整的最终答案（内容为空，或因为长度被截断，finish_reason=length）。请直接写出完整最终答案，不要只输出思考过程。"


class IncompleteAnswer(Exception):
    """最终答案是空的，或截断后仍不能当成完成。message 已经是界面语言。"""


class TaskFailed(Exception):
    """任务以失败结束。message 已经是界面语言，Router 不再包一层。"""


class _NotStarted(Exception):
    """额度已经用尽，这个研究员还没调用模型。"""



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
    recent_calls: list = field(default_factory=list)  # 单 Worker 的最近调用，给 Watchdog 看
    repeat_history: dict = field(default_factory=dict)  # label -> 该 Worker 自己的重复检测历史
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
    quiet_ok: bool = False                 # 定时任务：结果只有“无新内容”时不发结果消息（见 routines.QUIET）
    quiet: bool = False                    # 这次确实没有新内容
    notes: str = ""                        # 只给 Worker 看的补充说明，不显示、不存进对话（定时任务：上次的结果、“无新内容”的约定）
    side_effects: list = field(default_factory=list)  # 本地写页面等，记下来给用户看
    degraded: bool = False                 # Heavy：审过了，但有研究员没交出草稿。结束时记 partial，不记 done


def _public(self) -> dict:
    return {"id": self.id, "goal": self.goal, "mode": self.mode, "status": self.status, "steps": self.steps,
            "bot_id": self.bot_id, "chat_id": self.chat_id, "started": self.started,
            "waiting_approval": self.waiting_approval, "last_action": self.last_action, "elapsed": round(time.time() - self.started),
            "quiet": self.quiet}


Task.public = _public


async def run_worker(task: Task, goal: str, label: str = "") -> str:
    ctools.CLAIM.set(f"{task.id}:{label}")
    try:
        return await _run_worker(task, goal, label)
    finally:
        await ctools.release()   # 任务结束（含取消、失败）就把电脑让给排队的任务


def _outbound(msg: dict) -> dict:
    """送回模型的 assistant 消息。finish_reason 只给本进程看，不能原样传给接口。"""
    return {k: v for k, v in msg.items() if k != "finish_reason"}


async def _reply(task: Task, log: tasklog.Log, role: str, client, model: str, msgs: list, tools_: list | None = None) -> dict:
    """流式调用一次模型，思考和正文边收边写进任务过程。返回这一轮的 assistant 消息。

    消息上的 finish_reason 是 stop / length / tool_calls 等。流被取消时，已有 usage 照实记；
    没有 usage 但已经收到文字就按估算记一条。"""
    stream = await create_chat(client, model=model, messages=msgs, stream=True,
                               stream_options={"include_usage": True},
                               **({"tools": tools_} if tools_ else {}), **call_kwargs(role))
    content, reasoning, calls, usage = "", "", {}, None
    finish = None
    think = text = None
    recorded = False
    try:
        async for chunk in stream:
            task.last_progress = time.time()   # 还在出字就算有进展，Watchdog 不会当成卡住
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if getattr(choice, "finish_reason", None):
                finish = choice.finish_reason
            d = choice.delta
            if d is None:
                continue
            if rc := getattr(d, "reasoning_content", None):
                reasoning += rc
                if not think or think["status"] != "running":
                    think = await log.start("think")
                await log.append(think, rc)
            if getattr(d, "content", None):
                content += d.content
                if think:
                    await log.finish(think)
                if not text or text["status"] != "running":
                    text = await log.start("text")
                await log.append(text, d.content)
            for tc in getattr(d, "tool_calls", None) or []:
                c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                c["id"] = tc.id or c["id"]
                if tc.function:
                    c["name"] += tc.function.name or ""
                    c["args"] += tc.function.arguments or ""
        memory.record_usage(role, model, usage, task.id)
        recorded = True
    except asyncio.CancelledError:
        if not recorded:
            memory.record_partial(role, model, usage, memory.streamed_output_text(content, reasoning, calls), task.id)
        raise
    if think:
        await log.finish(think)
    if text:
        await log.finish(text, kind="say" if calls else "answer")
    msg = {"role": "assistant", "finish_reason": finish}
    if content:
        msg["content"] = content
    if reasoning:   # DeepSeek 思考模式：带工具的请求要把 reasoning_content 原样传回
        msg["reasoning_content"] = reasoning
    if calls:
        msg["tool_calls"] = [{"id": c["id"] or f"call_{k}", "type": "function",
                              "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                             for k, c in sorted(calls.items(), key=lambda kv: kv[0] or 0)]
    return msg


def _accept_answer(msg: dict) -> str:
    """非空且没被 length 截断才算最终答案。否则抛 IncompleteAnswer。"""
    content = msg.get("content") or ""
    if content.strip() and msg.get("finish_reason") != "length":
        return content
    if not content.strip():
        raise IncompleteAnswer(i18n.t("模型没有给出答案"))
    raise IncompleteAnswer(i18n.t("回答被截断了，不能当成完成。已收到的内容：\n{text}", text=content))


async def _tool(task: Task, log: tasklog.Log, step: dict, name: str, raw: str, progress, pages: bool,
                shots: list) -> tuple[str, str]:
    """执行一个工具调用，返回 (给模型的结果, 这一步的状态)。工具出错交给模型自己处理。"""
    try:
        args = json.loads(raw or "{}")
        if name in local_checks.NAMES:
            return local_checks.tool(name, args), "done"
        if name == "verify_facts":
            return verification.tool(args), "done"
        if name in skillpacks.NAMES:
            return skillpacks.tool(task.bot_id, name, args), "done"
        if name in ctools.NAMES:
            out, shot = await ctools.call(task, name, args, progress)
            if shot:
                shots.append(shot)
            return out, "done"
        if name == "search_memory":
            await progress(i18n.t("查记忆和资料库：{query}", query=str(args.get("query", ""))[:40]))
            return await search.tool(task.bot_id, args), "done"
        if name == "read_page":
            await progress(i18n.t("读页面 #{id}", id=args.get("page_id")))
            return library.tool_read_page(args), "done"
        if name == "save_page" and pages:
            await progress(i18n.t("保存页面：{title}", title=str(args.get("title", ""))[:40]))
            ask, why = approvals.decide("save_page")
            # 规则“自动允许”优先于开关；开关只在没有命中规则时生效。默认关，避免每次存页面都打断。
            if ask or (CFG["limits"].get("save_page_approval") and "自动允许" not in why):
                await log.update(step, status="waiting")
                ok, note = await approvals.request(task, name, args)
                if not ok:
                    return i18n.t("用户拒绝了这个操作，没有执行。{note}", note=note).strip(), "rejected"
                await log.update(step, status="running")
            out = library.tool_save_page(task.bot_id, args, task.id)
            failed = i18n.t("没保存：{error}", error="\0").replace("\0", "")
            if not out.startswith(failed):
                task.side_effects.append({"tool": "save_page", "summary": out})
            if PAGES_CHANGED:
                await PAGES_CHANGED()
            return out, "done"
        what = str(args.get("query") or args.get("url") or "")[:60]
        await progress(i18n.t("搜索：{what}", what=what) if name == "web_search" else
                       i18n.t("读取网页：{what}", what=what) if name == "fetch_url" else f"{name} {what}")
        fn = tools.lookup(name)
        if fn and name in mcp_hub.TOOLS and approvals.decide(name)[0]:
            await log.update(step, status="waiting")
            ok, note = await approvals.request(task, name, args)
            if not ok:
                return i18n.t("用户拒绝了这个操作，没有执行。{note}", note=note).strip(), "rejected"
            await log.update(step, status="running")
        if not fn:
            return i18n.t("未知工具"), "error"
        return await fn(**args), "done"
    except mcp_hub.ToolResultError as e:
        return e.text, "error"
    except Exception as e:
        return i18n.t("工具出错：{error}", error=e), "error"


def worker_system(task: Task, pages: bool) -> str:
    use_pc = (CFG.get("computer") or {}).get("enabled", True)
    system = WORKER_PROMPT.format(date=time.strftime("%Y-%m-%d"), lang=ANSWER_LANG[i18n.lang()]) + ("\n" + PAGE_HINT if pages else "") \
        + ("\n\n" + ctools.SYSTEM_HINT if use_pc else "")
    system += verification.HINT + local_checks.runtime_hint() + skillpacks.runtime_hint(task.bot_id) + i18n.model_hint()
    if known := memories.worker_block(task.bot_id):
        system += f"\n\n关于用户（长期记忆，做事时遵守其中的偏好）：\n{known}"
    return system


def _history(task: Task, label: str) -> list:
    """每个 Worker 一份历史。Heavy 里 h0/h1/h2 并行，不能共用一份，否则别人的第一次调用会被当成重复。"""
    return task.repeat_history.setdefault(label or "", [])


def _looping(history: list, sig: str) -> bool:
    """同一个工具调用在这份历史里连续出现 repeat_tool_limit 次就停。0 表示不查。"""
    limit = int(CFG["limits"].get("repeat_tool_limit", 3) or 0)
    history.append(sig)
    del history[:-8]
    return limit > 1 and len(history) >= limit and len(set(history[-limit:])) == 1


async def _run_worker(task: Task, goal: str, label: str = "") -> str:
    client, model = client_for("worker")
    use_pc = (CFG.get("computer") or {}).get("enabled", True)
    pages = not label   # Heavy 模式的几个 Worker 只出草稿，不各自存页面
    system = worker_system(task, pages)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": goal}]
    schemas = local_checks.SCHEMAS + [verification.SCHEMA] + skillpacks.SCHEMAS + tools.schemas() + ([library.SAVE_PAGE] if pages else []) + [library.READ_PAGE, search.SEARCH_TOOL] \
        + (ctools.SCHEMAS if use_pc else [])
    log = tasklog.Log(task, label)
    continuations = 0
    extra = int(CFG["limits"].get("answer_continuations", 1) or 0)

    async def progress(text: str):
        task.last_action = text
        if log.current:
            await log.update(log.current, title=text)
        if PROGRESS:
            await PROGRESS(task, text)

    stopped = False
    for _ in range(CFG["limits"]["worker_max_steps"]):
        ctools.prune_images(msgs)
        m = await _reply(task, log, "worker", client, model, msgs, schemas)
        task.steps += 1
        task.last_progress = time.time()
        if not m.get("tool_calls"):
            content = (m.get("content") or "").strip()
            if content and m.get("finish_reason") != "length":
                return m.get("content") or ""
            if continuations < extra:
                continuations += 1
                outbound = _outbound(m)
                if outbound.get("content") or outbound.get("reasoning_content"):
                    msgs.append(outbound)
                msgs.append({"role": "user", "content": CONTINUE_PROMPT})
                continue
            return _accept_answer(m)   # 空答案或仍被截断：抛 IncompleteAnswer，不当完成
        msgs.append(_outbound(m))
        shots = []   # 截图要等这一轮的工具结果都追加完再附上
        history = _history(task, label)
        skipped = i18n.t("这次调用被跳过，没有执行。同一个工具连续重复，请根据已有信息给出最终答案。")
        blocked = False
        for call in m["tool_calls"]:
            name, raw = call["function"]["name"], call["function"]["arguments"]
            step = log.current = await log.start("tool", name, detail=raw[:2000])
            # 同一条 assistant 消息里后面的调用也要有 tool result，只是不再执行。
            if blocked or _looping(history, f"{name}:{raw}"):
                out, status, blocked = skipped, "error", True
            else:
                out, status = await _tool(task, log, step, name, raw, progress, pages, shots)
            msgs.append({"role": "tool", "tool_call_id": call["id"], "content": out[:8000]})
            await log.finish(step, status, out)
            task.last_progress = time.time()
        if not label:
            task.recent_calls = list(history)
        if shots:
            msgs.append(ctools.image_message(shots[-1]))
        if blocked:
            stopped = True
            break
    if not stopped:
        await log.note(i18n.t("步数用完了，根据已有信息写结果"))
        msgs.append({"role": "user", "content": "步数用完了，请根据已有信息给出最终答案。"})
    m = await _reply(task, log, "worker", client, model, msgs)
    task.steps += 1
    return _accept_answer(m)


def heavy_plan() -> tuple[int, int, int]:
    """(研究员人数, 同时调用模型的上限, 交给审稿人所需的最少草稿)。"""
    n = max(1, int(CFG["heavy"]["workers"]))
    concurrency = max(1, int(CFG["heavy"].get("concurrency") or 1))
    raw = CFG["heavy"].get("min_drafts")
    if raw is None:
        need = max(1, (n + 1) // 2)
    else:
        need = max(1, min(n, int(raw)))
    return n, min(concurrency, n), need


async def run_heavy(task: Task) -> str:
    """Heavy 模式：N 个 Worker 各自做一遍，草稿够数才交给 Reviewer。

    同时在跑的人数是 heavy.concurrency（默认 1）。有人撞上额度用尽就停掉还没跑的，
    并且不叫审稿人。草稿少于 heavy.min_drafts 同样不叫审稿人，任务失败。
    有人失败但草稿够数时仍汇总，调用方把结果记成 partial。
    """
    n, concurrency, need = heavy_plan()
    angles = ["从最直接的角度", "从反面/质疑的角度核查", "从数据和一手来源角度", "从实践/落地角度"]
    await tasklog.Log(task).note(i18n.t("{n} 个研究员分头做，做完汇总", n=n))
    goal = task.goal + task.notes
    sem = asyncio.Semaphore(concurrency)
    stop = asyncio.Event()
    pending: list[asyncio.Task] = []

    async def one(i: int):
        try:
            async with sem:
                if stop.is_set():
                    raise _NotStarted()
                return await run_worker(
                    task, f"{goal}\n\n（你是第 {i+1} 个独立研究员，请{angles[i % len(angles)]}回答）", f"h{i}")
        except ProviderLimit as e:
            if e.kind == "quota":
                stop.set()
                current = asyncio.current_task()
                for other in pending:
                    if other is not current and not other.done():
                        other.cancel()
            raise

    pending = [asyncio.create_task(one(i)) for i in range(n)]
    drafts = await asyncio.gather(*pending, return_exceptions=True)
    quota = next((d for d in drafts if isinstance(d, ProviderLimit) and d.kind == "quota"), None)
    for i, d in enumerate(drafts):
        if isinstance(d, (_NotStarted, asyncio.CancelledError)):
            continue
        if isinstance(d, Exception):
            await tasklog.Log(task, f"h{i}").note(i18n.t("出错：{error}", error=d), "error")
    if quota is not None:
        raise TaskFailed(i18n.t(
            "额度用尽（{status} {code}），已停止这个 Heavy 任务，没有交给审稿人。{detail}",
            status=quota.status, code=quota.code or "-", detail=quota.detail))
    ok = [d for d in drafts if isinstance(d, str) and d.strip()]
    if len(ok) < need:
        raise TaskFailed(i18n.t(
            "草稿不够：{got}/{n} 份可用，至少要 {need} 份才交给审稿人。这次没有汇总。",
            got=len(ok), n=n, need=need))
    text = await _review(task, goal, ok)
    if len(ok) < n:
        task.degraded = True
    return text


async def _review(task: Task, goal: str, drafts: list[str]) -> str:
    client, model = client_for("reviewer")
    joined = "\n\n".join(f"=== 方案 {i+1} ===\n{d}" for i, d in enumerate(drafts))
    await tasklog.Log(task).note(i18n.t("{n} 份草稿交给审稿人汇总", n=len(drafts)))
    log = tasklog.Log(task, "review")
    msgs = [
        {"role": "system", "content": "你是审稿人。比较几份独立答案，找出矛盾和错误，合成一份最可靠的最终答案，保留来源链接。"
                                      + i18n.model_hint()},
        {"role": "user", "content": f"问题：{goal}\n\n{joined}"}]
    try:
        extra = int(CFG["limits"].get("answer_continuations", 1) or 0)
        m = await _reply(task, log, "reviewer", client, model, msgs)
        task.steps += 1
        for _ in range(extra):
            if (m.get("content") or "").strip() and m.get("finish_reason") != "length":
                return m.get("content") or ""
            outbound = _outbound(m)
            if outbound.get("content") or outbound.get("reasoning_content"):
                msgs.append(outbound)
            msgs.append({"role": "user", "content": CONTINUE_PROMPT})
            m = await _reply(task, log, "reviewer", client, model, msgs)
            task.steps += 1
        return _accept_answer(m)
    except ProviderLimit as e:
        if e.kind == "quota":
            raise TaskFailed(i18n.t(
                "额度用尽（{status} {code}），审稿没有完成。{detail}",
                status=e.status, code=e.code or "-", detail=e.detail)) from e
        raise
