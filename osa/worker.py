"""Worker：隔离的 ReAct 循环，带工具，单独执行一个任务。模型流式输出，每一步都记进任务过程（tasklog）。"""
import asyncio
import re
import json
import time
from dataclasses import dataclass, field
from .config import CFG, call_kwargs, client_for, fallback_for
from .providers import ProviderLimit, create_chat
from . import applets, approvals, dsml, i18n, local_checks, memories, memory, mcp_hub, providers, registry, skillpacks, tasklog, verification
from . import builtin  # noqa: F401  导入即注册内置工具
from .computer import tools as ctools

PROGRESS = None   # 由 router 设置：async (task, text) -> None，把动作推送到任务卡片

WORKER_PROMPT = """You are the Worker executing a task. Use tools to check facts. When you state a conclusion, include source links.
To read or write the user's external services (apps), use tools whose names start with "app-name__". If the task says "@app-name", you must use that app.
If the task says to follow skill /name but the method is not attached, or you need files the skill ships, fetch them with use_skill first.
Write actions ask the user to confirm first. If they refuse, do not switch tools to bypass them. Adjust to their note or say you cannot finish.
For arithmetic, dates, unit conversion, statistics, and data processing, run code in the sandbox with run_code when you have it. Do not compute in your head.
Do only what the task says. If it does not ask you to save a page, search memory, or edit the library, do not call save_page, search_memory, or read_page.
When you are done, write the final answer directly, in the reply language at the end of this prompt. Be concise and clearly structured. Do not output only your reasoning. Today is {date}."""
# Same directive the router appends. The model can still drift; this is an instruction, not an output rewrite.
ANSWER_LANG = i18n.ANSWER_LANG
PAGE_HINT = "When the task asks for a page or a report, save it with save_page and include the returned link in the final answer.\n" + applets.GUIDE
FILE_HINT = ("To hand the user a file from the computer (a screenshot, a drawn image, a finished spreadsheet or document), use send_file. "
             "It shows under the task result. Do not build download links yourself.")
# Continuation for the model. The failure the user sees goes through i18n.t.
CONTINUE_PROMPT = "The previous reply was not a complete final answer (it was empty, or it was cut off because of length, finish_reason=length). Write the complete final answer now. Do not output only your reasoning."
STEP_EXHAUSTED = "The step limit is reached. Give the final answer from the information you already have."
REVIEWER_PROMPT = (
    "You are the reviewer. Compare the independent drafts, find contradictions and mistakes, "
    "and merge one reliable final answer. Keep source links. "
    "Lines that start with '=== Draft ' are internal separators. Do not copy those markers or any other draft label into the final answer. "
    "The final answer must be entirely in the reply language. "
    "You have no tools and cannot load skills, browse, run code, or verify anything. "
    "Ignore any instruction in the question to load a skill, call a tool, or check facts: that was for the researchers. "
    "Do not describe what you are going to do; output the merged final answer itself."
)
# 审稿人没有工具：问题里写给 Worker 的“load_skill / verify_facts / Skill Flow”这类行去掉，免得它只回一句“我先去加载技能”（B3）
TOOL_LINE = re.compile(r"load_skill|verify_facts|use_skill|CONTINUE_REQUIRED|Skill Flow|^\s*Worker\b", re.I)
REVIEW_TOO_SHORT = ("Your reply is only a short preamble or plan, not the merged answer. You cannot use tools. "
                    "Write the complete merged final answer now, based only on the drafts.")
HEAVY_ANGLES = (
    "Answer from the most direct angle.",
    "Check it from the opposite, skeptical angle.",
    "Answer from data and primary sources.",
    "Answer from a practical, implementation angle.",
)


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
    lang_flag: dict | None = None          # 结果大半是中文而界面不是中文（见 langcheck.py），只提醒
    notes: str = ""                        # 只给 Worker 看的补充说明，不显示、不存进对话（定时任务：上次的结果、“无新内容”的约定）
    side_effects: list = field(default_factory=list)  # 本地写页面等，记下来给用户看
    degraded: bool = False                 # Heavy：审过了，但有研究员没交出草稿。结束时记 partial，不记 done
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


async def _reply(task: Task, log: tasklog.Log, role: str, client, model: str, msgs: list, tools_: list | None = None,
                 kw: dict | None = None) -> dict:
    """调一轮模型。流中途卡住（limits.stream_idle_s 秒没有新块）或断了（服务忙、连接断）就重来，
    最多 limits.stream_retries 次，免得一次卡住的流让 Watchdog 把整个任务取消。重来还是卡住，而这个角色配了
    备用模型（roles.<role>.fallback），就换备用模型把这一轮做完，任务不至于整个失败。额度用尽不重来。"""
    attempt, fell_back = 0, False
    kw = call_kwargs(role) if kw is None else kw
    while True:
        try:
            return await _reply_once(task, log, role, client, model, msgs, tools_, kw)
        except Exception as e:
            # 开流之前的错 create_chat 已经按规则重试过了，这里只管流开了之后的
            if not getattr(e, "osa_midstream", False) or not providers.retry_midstream(e):
                raise
            if attempt < providers.stream_retries():
                attempt += 1
                note = i18n.t("这一轮模型调用中途出错（{err}），重新调用", err=providers.brief(e))
            elif not fell_back and (fb := fallback_for(role, model)):
                client, model, kw = fb
                fell_back = True   # 备用模型只试一次：再卡住就是服务整体出问题，别一直耗下去
                note = i18n.t("这一轮模型调用中途出错（{err}），换备用模型 {model} 继续", err=providers.brief(e), model=model)
            else:
                raise
            task.last_progress = time.time()
            await log.note(note, "error")
            await providers.retry_pause(attempt)
            task.last_progress = time.time()


async def _reply_once(task: Task, log: tasklog.Log, role: str, client, model: str, msgs: list, tools_: list | None = None,
                      kw: dict | None = None) -> dict:
    """流式调用一次模型，思考和正文边收边写进任务过程。返回这一轮的 assistant 消息。

    消息上的 finish_reason 是 stop / length / tool_calls 等。流被取消时，已有 usage 照实记；
    没有 usage 但已经收到文字就按估算记一条。"""
    kw = call_kwargs(role) if kw is None else kw
    t0, first = time.monotonic(), None
    try:
        stream = await create_chat(client, model=model, messages=msgs, stream=True,
                                   stream_options={"include_usage": True},
                                   **({"tools": tools_} if tools_ else {}), **kw)
    except Exception as e:
        memory.record_error(role, model, providers.brief(e), task.id, bot_id=task.bot_id, chat_id=task.chat_id,
                            ms=(time.monotonic() - t0) * 1000)
        if isinstance(e, providers.StreamStalled):
            e.osa_midstream = True   # 连接阶段卡住（见 provider_head_s）：_reply 会重来一次，再不行换备用模型
        raise
    content, reasoning, calls, usage = "", "", {}, None
    finish = None
    think = text = None
    recorded = False
    sent = 0   # 正文写进任务过程到哪了：DeepSeek 写进正文的工具调用（见 dsml.py）不写

    async def say(piece: str):
        nonlocal text
        if think:
            await log.finish(think)
        if not text or text["status"] != "running":
            text = await log.start("text")
        await log.append(text, piece)

    try:
        async for chunk in providers.guard_stream(stream):
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
            if first is None and (getattr(d, "content", None) or getattr(d, "reasoning_content", None)
                                  or getattr(d, "tool_calls", None)):
                first = time.monotonic()
            if rc := getattr(d, "reasoning_content", None):
                reasoning += rc
                if not think or think["status"] != "running":
                    think = await log.start("think")
                await log.append(think, rc)
            if getattr(d, "content", None):
                content += d.content
                if (n := dsml.visible(content)) > sent:
                    await say(content[sent:n])
                    sent = n
            for tc in getattr(d, "tool_calls", None) or []:
                c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                c["id"] = tc.id or c["id"]
                if tc.function:
                    c["name"] += tc.function.name or ""
                    c["args"] += tc.function.arguments or ""
        memory.record_usage(role, model, usage, task.id, bot_id=task.bot_id, chat_id=task.chat_id,
                            ms=(time.monotonic() - t0) * 1000, ttft=None if first is None else (first - t0) * 1000)
        recorded = True
    except asyncio.CancelledError:
        if not recorded:
            memory.record_partial(role, model, usage, memory.streamed_output_text(content, reasoning, calls), task.id)
        raise
    except Exception as e:
        memory.record_error(role, model, providers.brief(e), task.id, bot_id=task.bot_id, chat_id=task.chat_id,
                            ms=(time.monotonic() - t0) * 1000)
        # 作废的这一轮也花了 token：有 usage 照实记，没有就按已收到的文字估算
        memory.record_partial(role, model, usage, memory.streamed_output_text(content, reasoning, calls), task.id)
        for s in (think, text):   # 这一轮作废：没收完的思考、正文标成出错，别一直显示“进行中”
            if s and s["status"] == "running":
                await log.finish(s, status="error")
        e.osa_midstream = True
        raise
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


def _accept_answer(msg: dict) -> str:
    """非空且没被 length 截断才算最终答案。否则抛 IncompleteAnswer。"""
    content = msg.get("content") or ""
    if content.strip() and msg.get("finish_reason") != "length":
        return content
    if not content.strip():
        raise IncompleteAnswer(i18n.t("模型没有给出答案"))
    raise IncompleteAnswer(i18n.t("回答被截断了，不能当成完成。已收到的内容：\n{text}", text=content))


async def _call_tool(task: Task, log: tasklog.Log, step: dict, name: str, raw: str, progress, env: dict,
                     shots: list) -> tuple[str, str]:
    """执行一个工具调用，返回 (给模型的结果, 这一步的状态)。工具出错交给模型自己处理。
    电脑工具单独处理（和任务、窗口绑得紧），其余都从注册表找（env 决定这一轮有哪些）。"""
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
        tool = registry.available(name, registry.WORKER, env)
        if not tool:
            return i18n.t("未知工具"), "error"
        await progress(tool.progress(args) if tool.progress else f"{name} {str(args.get('query') or args.get('url') or '')[:60]}")
        if name == "save_page":
            ask, why = approvals.decide("save_page")
            # remake：规则“自动允许”优先于开关；开关只在没有命中规则时生效。默认关，避免每次存页面都打断。
            if ask or (CFG["limits"].get("save_page_approval") and "自动允许" not in why):
                await log.update(step, status="waiting")
                ok, note = await approvals.request(task, name, args)
                if not ok:
                    return i18n.t("用户拒绝了这个操作，没有执行。{note}", note=note).strip(), "rejected"
                await log.update(step, status="running")
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
        if name == "save_page":
            failed = i18n.t("没保存：{error}", error="\0").replace("\0", "")
            if not str(out).startswith(failed):
                task.side_effects.append({"tool": "save_page", "summary": out})
        return out, "done"
    except mcp_hub.ToolResultError as e:
        return e.text, "error"
    except Exception as e:
        return i18n.t("工具出错：{error}", error=e), "error"


def _lane(call: dict, env: dict) -> tuple[str, int] | None:
    """这个调用能不能和相邻的只读调用一起跑：能就返回 (组, 同组同时最多几个)。
    只有标了 parallel 的（只读、不改任何东西），而且这次不用问用户；电脑工具、写的、要确认的都不行。"""
    name = call["function"]["name"]
    tool = None if name in ctools.NAMES or name in local_checks.NAMES or name == "verify_facts" or name in skillpacks.NAMES else registry.available(name, registry.WORKER, env)
    if not tool or tool.parallel < 1:
        return None
    try:
        args = json.loads(call["function"]["arguments"] or "{}")
    except json.JSONDecodeError:
        return None
    if not isinstance(args, dict) or (tool.gated and approvals.decide(name, args=args)[0]):
        return None
    if name == "save_page":
        ask, why = approvals.decide("save_page")
        if ask or (CFG["limits"].get("save_page_approval") and "自动允许" not in why):
            return None
    return tool.group or tool.name, tool.parallel


async def _run_calls(task: Task, log: tasklog.Log, calls: list, env: dict, history: list) -> tuple[list[tuple[str, list]], bool]:
    """执行一轮的工具调用，按调用的顺序返回 ([(给模型的结果, 截图)], 是否因重复调用停了)。
    相邻的只读调用（见 _lane）一起跑；别的照旧一个个跑。同一个工具连续重复时，这一轮剩下的调用不再执行。"""
    def progress_for(step: dict):
        async def progress(text: str):
            task.last_action = text
            log.current = step
            await log.update(step, title=text)
            if PROGRESS:
                await PROGRESS(task, text)
        return progress

    skipped = i18n.t("这次调用被跳过，没有执行。同一个工具连续重复，请根据已有信息给出最终答案。")

    async def one(call: dict, step: dict, sem: asyncio.Semaphore | None, skip: bool) -> tuple[str, list]:
        name, raw, shots = call["function"]["name"], call["function"]["arguments"], []
        if skip:
            out, status = skipped, "error"
        elif sem:
            async with sem:
                out, status = await _call_tool(task, log, step, name, raw, progress_for(step), env, shots)
        else:
            out, status = await _call_tool(task, log, step, name, raw, progress_for(step), env, shots)
        await log.finish(step, status, out)
        task.last_progress = time.time()
        return out, shots

    results, i, blocked = [], 0, False
    while i < len(calls):
        lanes = [None if blocked else _lane(calls[i], env)]
        while lanes[0] and not blocked and i + len(lanes) < len(calls) and (nxt := _lane(calls[i + len(lanes)], env)):
            lanes.append(nxt)
        group = calls[i:i + len(lanes)]
        steps, skips = [], []
        for call in group:
            name, raw = call["function"]["name"], call["function"]["arguments"]
            steps.append(await log.start("tool", name, detail=raw[:2000]))
            if blocked or _looping(history, f"{name}:{raw}"):
                skips.append(True)
                blocked = True
            else:
                skips.append(False)
        sems = {lane[0]: asyncio.Semaphore(lane[1]) for lane in lanes if lane} if len(group) > 1 and not any(skips) else {}
        results += await asyncio.gather(*(one(c, st, sems.get(lane[0]) if lane else None, skip)
                                          for c, st, lane, skip in zip(group, steps, lanes, skips)))
        i += len(group)
    return results, blocked


def worker_system(task: Task, pages: bool) -> str:
    use_pc = (CFG.get("computer") or {}).get("enabled", True)
    system = WORKER_PROMPT.format(date=time.strftime("%Y-%m-%d")) + ("\n" + PAGE_HINT if pages else "") \
        + ("\n" + FILE_HINT if pages and use_pc else "") + ("\n\n" + ctools.system_hint() if use_pc else "")
    system += verification.HINT + local_checks.runtime_hint() + skillpacks.runtime_hint(task.bot_id)
    if known := memories.worker_block(task.bot_id):
        system += f"\n\nAbout the user (long-term memory; follow these preferences):\n{known}"
    return system + i18n.model_hint()


def _history(task: Task, label: str) -> list:
    """每个 Worker 一份历史。Heavy 里 h0/h1/h2 并行，不能共用一份，否则别人的第一次调用会被当成重复。"""
    return task.repeat_history.setdefault(label or "", [])


SHORTENED = "\n… (shortened to keep the context small; call the tool again if you need the rest)"


def _compact_tools(msgs: list[dict]) -> int:
    """C8/C18：任务跑久了，早先的工具结果把每一步的上下文撑大。

    线上（2026-11-11）worker 平均每次调用发 49k token：一次任务 30 步，每步都把前面所有工具
    结果重发一遍。这里只留最近 worker_keep_full_tools 条完整，其余截到 worker_old_tool_chars 字；
    总量不到 worker_compact_chars 就一个字不动 —— 改了前缀，模型服务的缓存那一次就要全部重读。

    C18：一次要截到 worker_compact_to_chars 以下，给后面的步留出余量。原来截完总量几乎还在阈值边上，
    下一步又来一条结果、又超、又截一条：于是**每一步**都改了前缀，每一步都重读整个 body（实测任务 106、
    102 里就是这样，连续几次调用只命中 1152 token）。留出余量后，一次截短换来后面若干步都命中。
    返回截掉的字数。
    """
    lim = CFG["limits"]
    keep = int(lim.get("worker_keep_full_tools", 3) or 0)
    keep_chars = int(lim.get("worker_old_tool_chars", 1500) or 0)
    compact_at = int(lim.get("worker_compact_chars", 60000) or 0)
    goal = int(lim.get("worker_compact_to_chars", 20000) or 0) or compact_at // 3
    if not compact_at or keep_chars <= 0:
        return 0
    tools = [i for i, m in enumerate(msgs) if m.get("role") == "tool"]
    total = sum(len(msgs[i].get("content") or "") for i in tools)
    if total <= compact_at:
        return 0
    cut = 0
    for i in tools[:-keep] if keep else tools:
        c = msgs[i].get("content") or ""
        if len(c) <= keep_chars or c.endswith(SHORTENED):
            continue
        msgs[i]["content"] = c[:keep_chars] + SHORTENED
        cut += len(c) - keep_chars
        total -= len(c) - len(msgs[i]["content"])
        if total <= goal:
            break
    return cut


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
        _compact_tools(msgs)          # C8：早先的工具结果占的地方太大，只留最近几条完整
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
        ran, blocked = await _run_calls(task, log, m["tool_calls"], env, history)
        for call, (out, got) in zip(m["tool_calls"], ran):
            cap = int(CFG["limits"].get("worker_result_chars", 8000) or 0)
            msgs.append({"role": "tool", "tool_call_id": call["id"], "content": out[:cap] if cap else out})
            shots += got
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
    text = await _review(task, task.goal, ok)
    if len(ok) < n:
        task.degraded = True
    return text


def reviewer_system() -> str:
    return REVIEWER_PROMPT + i18n.model_hint()


def _review_question(goal: str) -> str:
    """给审稿人的问题：去掉写给 Worker 的工具 / 技能指令行。"""
    return "\n".join(line for line in goal.splitlines() if not TOOL_LINE.search(line)).strip() or goal


def _review_too_short(text: str, drafts: list[str]) -> bool:
    """审稿结果远短于最短的草稿（不到四分之一，且不到 400 字）：多半只是一句开场白，不是汇总。
    草稿本身很短（不到 200 字，比如只是一个数）时不判断。"""
    n, shortest = len(text.strip()), min(len(d.strip()) for d in drafts)
    return shortest >= 200 and n < 400 and n < 0.25 * shortest


async def _review(task: Task, goal: str, drafts: list[str]) -> str:
    client, model = client_for("reviewer")
    joined = "\n\n".join(f"=== Draft {i+1} ===\n{d}" for i, d in enumerate(drafts))
    await tasklog.Log(task).note(i18n.t("{n} 份草稿交给审稿人汇总", n=len(drafts)))
    log = tasklog.Log(task, "review")
    msgs = [
        {"role": "system", "content": reviewer_system()},
        {"role": "user", "content": f"Question:\n{_review_question(goal)}\n\n{joined}\n\nWrite the final answer only. Do not include the Draft markers."}]

    async def ask() -> str:
        extra = int(CFG["limits"].get("answer_continuations", 1) or 0)
        m = await _reply(task, log, "reviewer", client, model, msgs)
        task.steps += 1
        for _ in range(extra):
            if (m.get("content") or "").strip() and m.get("finish_reason") != "length":
                break
            outbound = _outbound(m)
            if outbound.get("content") or outbound.get("reasoning_content"):
                msgs.append(outbound)
            msgs.append({"role": "user", "content": CONTINUE_PROMPT})
            m = await _reply(task, log, "reviewer", client, model, msgs)
            task.steps += 1
        return _accept_answer(m)

    try:
        text = await ask()
        if not _review_too_short(text, drafts):
            return text
        msgs += [{"role": "assistant", "content": text}, {"role": "user", "content": REVIEW_TOO_SHORT}]
        text = await ask()
        if not _review_too_short(text, drafts):
            return text
        best = max(range(len(drafts)), key=lambda i: len(drafts[i]))
        task.degraded = True
        await log.note(i18n.t("审稿人没有给出汇总，改用草稿 {n}", n=best + 1), "error")
        return drafts[best]
    except ProviderLimit as e:
        if e.kind == "quota":
            raise TaskFailed(i18n.t(
                "额度用尽（{status} {code}），审稿没有完成。{detail}",
                status=e.status, code=e.code or "-", detail=e.detail)) from e
        raise
