"""Worker：隔离的 ReAct 循环，带工具，单独执行一个任务。模型流式输出，每一步都记进任务过程（tasklog）。"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from .config import CFG, call_kwargs, client_for
from . import applets, approvals, dsml, i18n, library, local_checks, memories, memory, providers, registry, skillpacks, tasklog, verification
from . import builtin  # noqa: F401  导入即注册内置工具
from .computer import tools as ctools

PROGRESS = None   # 由 router 设置：async (task, text) -> None，把动作推送到任务卡片

WORKER_PROMPT = """你是执行任务的 Worker。用工具查证事实，给出结论时附上来源链接。
需要读写用户的外部服务（应用）时，使用名字带“应用名__”前缀的工具；任务里写了“@应用名”就必须用那个应用。
任务里写了按技能 /名字 做、却没附上做法或要用技能带的文件时，先用 use_skill 取。
写操作会先请用户确认；被拒绝时不要换个工具绕过去，按用户的意见调整或说明无法完成。
算数、日期、单位换算、统计和处理数据，有 run_code 时用它在沙箱里跑代码算，不要心算。
完成后直接输出最终答案（{lang}，简洁、结构清晰）。今天是 {date}。"""
# 最终答案用什么语言：中文界面和以前一样；英文界面默认英文
ANSWER_LANG = {"zh": "中文", "en": "默认用英文，任务是用别的语言写的就用那种语言"}
PAGE_HINT = "任务要求做成页面或报告时，用 save_page 保存，最终答案里附上返回的链接。\n" + applets.GUIDE
FILE_HINT = "要把电脑里的文件（截图、画好的图、做好的表格和文档）交给用户时用 send_file，它们会显示在任务结果下面；不要自己拼下载链接。"



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
    files: list = field(default_factory=list)   # send_file 发的文件（附件，见 media.py），显示在任务结果下面
    apps: list = field(default_factory=list)    # 用到的应用界面（MCP Apps，见 mcpapps.py），显示在任务结果下面


def _public(self) -> dict:
    return {"id": self.id, "goal": self.goal, "mode": self.mode, "status": self.status, "steps": self.steps,
            "bot_id": self.bot_id, "chat_id": self.chat_id, "started": self.started,
            "waiting_approval": self.waiting_approval, "last_action": self.last_action, "elapsed": round(time.time() - self.started),
            "quiet": self.quiet}


Task.public = _public


async def run_worker(task: Task, goal: str, label: str = "") -> str:
    ctools.CLAIM.set(f"{task.id}:{label}")
    memory.WHO.set({"bot_id": task.bot_id, "chat_id": task.chat_id, "task_id": task.id})   # 任务里的模型调用（画图等）记到这个任务上
    try:
        return await _run_worker(task, goal, label)
    finally:
        await ctools.release()   # 任务结束（含取消、失败）就把电脑让给排队的任务


def _outbound(msg: dict) -> dict:
    """送回模型的 assistant 消息。finish_reason 只给本进程看，不能原样传给接口。"""
    return {k: v for k, v in msg.items() if k != "finish_reason"}


async def _reply(task: Task, log: tasklog.Log, role: str, client, model: str, msgs: list, tools_: list | None = None) -> dict:
    """流式调用一次模型，思考和正文边收边写进任务过程。返回这一轮的 assistant 消息，可以直接接到 msgs 后面。"""
    t0, first = time.monotonic(), None
    try:
        stream = await client.chat.completions.create(model=model, messages=msgs, stream=True,
                                                      stream_options={"include_usage": True},
                                                      **({"tools": tools_} if tools_ else {}), **call_kwargs(role))
    except Exception as e:
        memory.record_error(role, model, providers.brief(e), task.id, bot_id=task.bot_id, chat_id=task.chat_id,
                            ms=(time.monotonic() - t0) * 1000)
        raise
    content, reasoning, calls, usage = "", "", {}, None
    finish = None
    think = text = None
    sent = 0   # 正文写进任务过程到哪了：DeepSeek 写进正文的工具调用（见 dsml.py）不写

    async def say(piece: str):
        nonlocal text
        if think:
            await log.finish(think)
        if not text or text["status"] != "running":
            text = await log.start("text")
        await log.append(text, piece)

    try:
        async for chunk in stream:
            task.last_progress = time.time()   # 还在出字就算有进展，Watchdog 不会当成卡住
            if chunk.usage:
                usage = chunk.usage
            if not chunk.choices:
                continue
            d = chunk.choices[0].delta
            if first is None and (d.content or getattr(d, "reasoning_content", None) or d.tool_calls):
                first = time.monotonic()
            if rc := getattr(d, "reasoning_content", None):
                reasoning += rc
                if not think or think["status"] != "running":
                    think = await log.start("think")
                await log.append(think, rc)
            if d.content:
                content += d.content
                if (n := dsml.visible(content)) > sent:
                    await say(content[sent:n])
                    sent = n
            for tc in d.tool_calls or []:
                c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                c["id"] = tc.id or c["id"]
                if tc.function:
                    c["name"] += tc.function.name or ""
                    c["args"] += tc.function.arguments or ""
    except Exception as e:
        memory.record_error(role, model, providers.brief(e), task.id, bot_id=task.bot_id, chat_id=task.chat_id,
                            ms=(time.monotonic() - t0) * 1000)
        raise
    memory.record_usage(role, model, usage, task.id, bot_id=task.bot_id, chat_id=task.chat_id,
                        ms=(time.monotonic() - t0) * 1000, ttft=None if first is None else (first - t0) * 1000)
    content, leaked = dsml.split(content)
    if len(content) > sent:   # 压着的结尾不是标记，或者标记后面还有话
        await say(content[sent:])
    if not calls and tools_:
        calls = dict(enumerate(leaked))
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


async def _tool(task: Task, log: tasklog.Log, step: dict, name: str, raw: str, progress, env: dict,
                shots: list) -> tuple[str, str]:
    """调一个工具；调完发 tool_done 事件（只读，插件能看不能改，不等它们）。"""
    out, status = await _call_tool(task, log, step, name, raw, progress, env, shots)
    if registry.listening("tool_done"):
        from . import bots
        try:
            args = json.loads(raw or "{}")
        except json.JSONDecodeError:
            args = {}
        registry.fire("tool_done", scope="worker", bot=bots.get(task.bot_id) or {"id": task.bot_id}, chat_id=task.chat_id,
                      task=task.public(), name=name, args=args, result=out, status=status)
    return out, status


async def _call_tool(task: Task, log: tasklog.Log, step: dict, name: str, raw: str, progress, env: dict,
                     shots: list) -> tuple[str, str]:
    """执行一个工具调用，返回 (给模型的结果, 这一步的状态)。工具出错交给模型自己处理。
    电脑工具单独处理（和任务、窗口绑得紧），其余都从注册表找（env 决定这一轮有哪些）。"""
    try:
        args = json.loads(raw or "{}")
        if name in ctools.NAMES:
            out, shot = await ctools.call(task, name, args, progress)
            if shot:
                shots.append(shot)
            return out, "done"
        tool = registry.available(name, registry.WORKER, env)
        if not tool:
            return "未知工具", "error"
        await progress(tool.progress(args) if tool.progress else f"{name} {str(args.get('query') or args.get('url') or '')[:60]}")
        if tool.gated and approvals.decide(name, args=args)[0]:
            await log.update(step, status="waiting")
            ok, note = await approvals.request(task, name, args)
            if not ok:
                return i18n.t("用户拒绝了这个操作，没有执行。{note}", note=note).strip(), "rejected"
            await log.update(step, status="running")
        from . import bots
        out = await tool.run(registry.Call(registry.WORKER, bots.get(task.bot_id) or {"id": task.bot_id}, task.chat_id,
                                           task.approval_chat_id or task.chat_id, args, task=task, files=task.files, apps=task.apps, env=env))
        if isinstance(out, tuple):   # (文字, 截图)
            if out[1]:
                shots.append(out[1])
            out = out[0]
        return out, "done"
    except Exception as e:
        return i18n.t("工具出错：{error}", error=e), "error"


def worker_system(task: Task, pages: bool) -> str:
    use_pc = (CFG.get("computer") or {}).get("enabled", True)
    system = WORKER_PROMPT.format(date=time.strftime("%Y-%m-%d")) + ("\n" + PAGE_HINT if pages else "") \
        + ("\n\n" + ctools.SYSTEM_HINT if use_pc else "")
    system += verification.HINT + local_checks.runtime_hint() + skillpacks.runtime_hint(task.bot_id)
    if known := memories.worker_block(task.bot_id):
        system += f"\n\nAbout the user (long-term memory; follow these preferences):\n{known}"
    return system + i18n.model_hint()


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
    system = WORKER_PROMPT.format(date=time.strftime("%Y-%m-%d"), lang=ANSWER_LANG[i18n.lang()]) + ("\n" + PAGE_HINT if pages else "") \
        + ("\n" + FILE_HINT if pages and use_pc else "") + ("\n\n" + ctools.system_hint() if use_pc else "")
    if known := memories.worker_block(task.bot_id):
        system += f"\n\n关于用户（长期记忆，做事时遵守其中的偏好）：\n{known}"
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": goal}]
    env = {"scope": registry.WORKER, "pages": pages, "use_pc": use_pc}
    schemas = registry.schemas(registry.WORKER, env) + (ctools.schemas() if use_pc else [])
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
            out, status = await _tool(task, log, step, name, raw, progress, env, shots)
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
        msgs.append({"role": "user", "content": STEP_EXHAUSTED})
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
                    task, f"{goal}\n\n(You are independent researcher {i+1}. {HEAVY_ANGLES[i % len(HEAVY_ANGLES)]})", f"h{i}")
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


def reviewer_system() -> str:
    return REVIEWER_PROMPT + i18n.model_hint()


async def _review(task: Task, goal: str, drafts: list[str]) -> str:
    client, model = client_for("reviewer")
    joined = "\n\n".join(f"=== Draft {i+1} ===\n{d}" for i, d in enumerate(drafts))
    await tasklog.Log(task).note(i18n.t("{n} 份草稿交给审稿人汇总", n=len(drafts)))
    log = tasklog.Log(task, "review")
    msgs = [
        {"role": "system", "content": reviewer_system()},
        {"role": "user", "content": f"Question:\n{goal}\n\n{joined}\n\nWrite the final answer only. Do not include the Draft markers."}]
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
