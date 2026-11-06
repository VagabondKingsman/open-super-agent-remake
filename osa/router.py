"""Router：常驻会话，负责和用户对话、派发任务。自己不执行工具（对应 DeepSeek 设计里 Router 无 shell）。

一个 Bot 一个 Router，既在私聊里说话，也在它所在的群聊里说话；每一轮都明确是在哪个对话里。"""

from .i18n import s as _s
import asyncio
import json
import time
from .computer import tools as ctools
from .config import CFG, call_kwargs, client_for
from . import approvals, bots, dm, library, memories, memory, routines, search, skills, tasklog
from . import worker as worker_mod
from .worker import Task, run_worker, run_heavy

from . import i18n

def _p(key: str, **kw) -> str:
    return i18n.prompt(key, **kw)


MESSAGE_BOT = {"type": "function", "function": {"name": "message_bot",
    "description": "私信另一个 Bot，请它帮忙做事。它在自己的私聊里处理，回信会自动回到当前对话，你到时再接着说",
    "parameters": {"type": "object", "properties": {
        "to": {"type": "string", "description": "Bot 的名字"},
        "text": {"type": "string", "description": "要它做什么，写完整、自包含（它看不到这里的对话）"}},
        "required": ["to", "text"]}}}

HANDOFF = {"type": "function", "function": {"name": "handoff", "description": "在群聊里把工作交给另一个 Bot，它会马上接着做",
    "parameters": {"type": "object", "properties": {
        "to": {"type": "string", "description": "成员的名字"},
        "request": {"type": "string", "description": "要它做什么，写完整（它能看到群里之前的消息）"}},
        "required": ["to", "request"]}}}

DIRECT_PC = {"computer_screenshot", "computer_click", "computer_type",
             "computer_key", "computer_scroll", "browser_open", "browser_snapshot", "browser_click",
             "browser_type", "browser_key", "browser_scroll", "browser_back", "browser_read"}

ROUTER_TOOLS = [*[s for s in ctools.SCHEMAS if s["function"]["name"] in DIRECT_PC],
    {"type": "function", "function": {"name": "dispatch", "description": "派发后台任务",
        "parameters": {"type": "object", "properties": {
            "goal": {"type": "string", "description": "完整、自包含的任务描述"},
            "mode": {"type": "string", "enum": ["single", "heavy"]},
            "handoff_to": {"type": "string", "description": "只在群聊里用：任务完成后把结果交给哪个成员接着做"},
            "handoff_note": {"type": "string", "description": "交接时要对方做什么"}}, "required": ["goal"]}}},
    {"type": "function", "function": {"name": "save_skill", "description": "保存或覆盖一个技能（可复用的做事方法）",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "简短的名字，用于 /名字 调用，不含空格"},
            "description": {"type": "string", "description": "一句话说明什么时候用"},
            "body": {"type": "string", "description": "完整的做法：步骤、要用的网站或应用、输出格式"}},
            "required": ["name", "body"]}}},
    {"type": "function", "function": {"name": "create_routine", "description": "新建定时任务",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "名字；webhook 类只能用字母数字 - _"},
            "prompt": {"type": "string", "description": "每次运行要做的事，写完整"},
            "skill": {"type": "string", "description": "可选：每次按哪个技能做（不带 /）"},
            "kind": {"type": "string", "enum": ["daily", "every", "webhook"]},
            "times": {"type": "array", "items": {"type": "string"}, "description": "daily 用：HH:MM 列表"},
            "days": {"type": "array", "items": {"type": "integer"}, "description": "daily 用：周几运行，周一=1，留空=每天"},
            "minutes": {"type": "integer", "description": "every 用：间隔分钟，至少 5"}},
            "required": ["name", "kind"]}}},
    {"type": "function", "function": {"name": "remember", "description": "记下一条长期记忆（以后的对话都会带着）",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "独立完整的一句话，例如“用户希望回答先给结论”"},
            "shared": {"type": "boolean", "description": "关于用户本人的基本事实（名字、时区、所在城市等）为 true，所有 Bot 共享"},
            "replace_id": {"type": "integer", "description": "可选：用这条替换已有的那条记忆"}},
            "required": ["text"]}}},
    {"type": "function", "function": {"name": "forget", "description": "删除一条长期记忆",
        "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}}},
    library.SAVE_PAGE,
    library.READ_PAGE,
    search.SEARCH_TOOL,
    {"type": "function", "function": {"name": "list_tasks", "description": "查看任务状态",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "cancel_task", "description": "取消任务",
        "parameters": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}}},
    {"type": "function", "function": {"name": "resolve_approval", "description": "处理一个待确认的写操作",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"}, "approve": {"type": "boolean"},
            "note": {"type": "string", "description": "用户附带的意见，例如修改要求"},
            "always": {"type": "boolean", "description": "用户明确说以后同类操作都不用问时为 true"}}, "required": ["id", "approve"]}}},
    {"type": "function", "function": {"name": "recall", "description": "按 id 取回早先消息原文",
        "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}}},
    {"type": "function", "function": {"name": "look_at_screen",
        "description": "看一眼共用电脑现在的屏幕（截图 + 当前窗口标题）。用户问屏幕上有什么、某个任务做到哪了、"
                       "或者你要判断下一步该派什么任务时用。只看不操作；要操作就派任务。",
        "parameters": {"type": "object", "properties": {}}}},
]


TASKS: dict[int, Task] = {}       # 所有 Bot 的任务，Watchdog 统一巡检
RUNTIMES: dict[int, "Router"] = {}
notify = None                     # 由 server 设置：async (event) -> None


async def _progress(task, text: str):
    if notify:
        await notify({"type": "task", "chat_id": task.chat_id, "bot_id": task.bot_id, "task": task.public()})

worker_mod.PROGRESS = _progress


def runtime(bot_id: int) -> "Router":
    if bot_id not in RUNTIMES:
        RUNTIMES[bot_id] = Router(bot_id)
    return RUNTIMES[bot_id]


def cancel(tid: int, reason: str) -> str:
    t = TASKS.get(tid)
    return runtime(t.bot_id).cancel(tid, reason) if t else _s('audit_00b1f8d0b9', v0=tid)


class Router:
    """一个 Bot 的常驻会话。一次处理一条消息；派出去的 Worker 在后台并行。"""

    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self.lock = asyncio.Lock()
        self.chat: dict = {}              # 本轮在哪个对话里说话（_think 开始时设置）
        self.turn: dict = {}              # 本轮的来由（respond 设置）：欠谁回信、私信深度

    @property
    def bot(self) -> dict:
        return bots.get(self.bot_id)

    @property
    def chat_id(self) -> int:
        """这个 Bot 的私聊。群聊里说话时用 self.chat（本轮所在的对话）。"""
        return self.bot["chat_id"]

    @property
    def tasks(self) -> dict[int, Task]:
        return {i: t for i, t in TASKS.items() if t.bot_id == self.bot_id}

    async def emit(self, event: dict, chat_id: int | None = None):
        if notify:
            await notify({"chat_id": chat_id or self.chat_id, "bot_id": self.bot_id} | event)

    async def add(self, role: str, content: str, chat_id: int | None = None, **meta) -> int:
        cid = chat_id or self.chat_id
        mid = memory.add(role, content, cid, self.bot_id, **meta)
        await self.emit({"type": "message", "message": {"id": mid, "ts": time.time(), "role": role,
                         "content": content, "meta": meta, "bot_id": self.bot_id}}, cid)
        return mid

    def _over_budget(self) -> bool:
        return memory.tokens_today() > CFG["limits"]["daily_token_budget"]

    async def handle_user(self, text: str, via: str = ""):
        """用户在私聊里发了一条消息。via：从哪个聊天软件发来的（网页上发的为空）。"""
        meta = {"via": via} if via else {}
        if hit := skills.parse(self.bot_id, text):
            meta |= {"skill": hit[0]["name"], "skill_prompt": skills.expand(*hit)}
        await self.add("user", text, **meta)
        await self.respond(self.chat_id)

    async def respond(self, chat_id: int, turn: dict | None = None):
        """在某个对话里说一轮话。群聊由 groups 决定轮到谁。
        turn 是这一轮的来由（见 dm.py）：reply 是这一轮欠谁回信，depth 是私信的深度，woke 是被谁的私信或回信叫醒的。"""
        async with self.lock:
            self.turn = turn or {}
            owed = self.turn.get("reply")
            try:
                try:
                    shown = await self._think(bots.chat(chat_id))
                except Exception as e:
                    if owed:
                        await dm.answer(self.bot_id, owed, _s('audit_ead955c039', v0=(self.bot or {}).get('name', 'Bot'), v1=e), chat_id)
                    raise
                # 欠着回信：没派任务、也没再私信别人的话，这一轮的回复就是回信（派了的由任务结果、对方回信接着送）
                if owed and not self._turn_tasks and not self._turn_dms:
                    await dm.answer(self.bot_id, owed, shown or _s('audit_d74b82b92d'), chat_id)
            finally:
                self.turn = {}

    async def _stream(self, client, model, msgs, sid: str, started: float, use_tools: bool = True):
        """流式调用一次模型，边收边推送正文和思考过程。返回 (正文, 思考, 工具调用列表)。"""
        tools = i18n.localize_tools(
            ROUTER_TOOLS + ([HANDOFF] if self.chat["kind"] == "group" else []) +
            ([MESSAGE_BOT] if len(bots.list_bots()) > 1 else []))
        cid = self.chat["id"]
        stream = await client.chat.completions.create(
            model=model, messages=msgs, stream=True, **({"tools": tools} if use_tools else {}),
            stream_options={"include_usage": True}, **call_kwargs("router"))
        content, reasoning, calls, usage = "", "", {}, None
        async for chunk in stream:
            if chunk.usage:
                usage = chunk.usage
            if not chunk.choices:
                continue
            d = chunk.choices[0].delta
            if rc := getattr(d, "reasoning_content", None):
                reasoning += rc
                await self.emit({"type": "stream", "sid": sid, "thinking": rc}, cid)
            if d.content:
                content += d.content
                await self.emit({"type": "stream", "sid": sid, "delta": d.content}, cid)
            for tc in d.tool_calls or []:
                c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                c["id"] = tc.id or c["id"]
                if tc.function:
                    c["name"] += tc.function.name or ""
                    c["args"] += tc.function.arguments or ""
        memory.record_usage("router", model, usage)
        return content, reasoning, [calls[k] for k in sorted(calls)]

    def _group_block(self, chat: dict) -> str:
        if chat["kind"] != "group":
            return ""
        lines = []
        for i in chat["bot_ids"]:
            m = bots.get(i)
            if m:
                role = (m["instructions"] or _s('audit_5854c5a19c')).replace("\n", " ")[:120]
                lines.append(f"- {m['name']}{_s('audit_2f8947c172') if i == self.bot_id else ''}{_s('audit_c77068c2ed') if i == chat['lead'] else ''}：{role}")
        lead = (_s('audit_156c9bd2cb')) if chat["lead"] == self.bot_id else \
            _s('audit_6017453651')
        return _p("GROUP_PROMPT", title=chat["title"], members="\n".join(lines), lead=lead)

    def _turn_block(self) -> str:
        woke = self.turn.get("woke")
        if not woke:
            return ""
        name = bots.get(woke["from"])["name"] if bots.get(woke["from"]) else _s('audit_ca59d8427a')
        if woke["kind"] == "dm":
            return _p("DM_TURN", name=name)
        owed = self.turn.get("reply")
        if owed:
            o = bots.get(owed["bot"])
            return _p("REPLY_TURN", name=name) + _p("REPLY_OWED", owed=o["name"] if o else i18n.s("awaiting_bot"), name=name)
        return _p("REPLY_TURN", name=name) + _p("REPLY_SHOWN")

    def _others(self) -> str:
        rows = [b for b in bots.list_bots() if b["id"] != self.bot_id]
        lines = [f"- {b['name']}：{(b['instructions'] or _s('audit_9570425417')).replace(chr(10), ' ')[:80]}" for b in rows[:30]]
        if len(rows) > 30:
            lines.append(_s('audit_1498494371', v0=len(rows) - 30))
        return "\n".join(lines) or _s('audit_b3171f0565')

    async def _think(self, chat: dict):
        client, model = client_for("router")
        b = self.bot
        self.chat = chat
        cid = chat["id"]
        last = memory.conn.execute("select content from messages where chat_id=? and role='user' order by id desc limit 1",
                                   (cid,)).fetchone()
        woke = self.turn.get("woke")
        related = await memories.related(self.bot_id, woke["text"] if woke else (last[0] if last else ""))
        if started := self.turn.get("started"):
            started()   # 下面就读对话了：这之前到的私信、回信都看得到，之后到的另起一轮（见 dm.py）
        msgs = [{"role": "system", "content": _p("ROUTER_PROMPT",
            name=b["name"], instructions=b["instructions"] or _s('audit_657b3ee25e'),
            date=time.strftime("%Y-%m-%d"), tasks=self._task_list(), skills=skills.summary(self.bot_id),
            routines=self._routine_list(), capabilities=self._capabilities(), memories=memories.prompt_block(self.bot_id, related),
            approvals=approvals.summary(self.bot_id), group=self._group_block(chat), others=self._others(),
            turn=self._turn_block())}] \
            + memory.context(cid, self.bot_id if chat["kind"] == "group" else None, me=self.bot_id)
        sid, started = f"s{time.time_ns()}", time.time()
        self._turn_tasks = []             # 本轮派发的任务，挂在这条回复下面显示
        self._turn_dms = 0                # 本轮发出的私信
        shown, thinking, shots = "", "", []
        await self.emit({"type": "stream_start", "sid": sid}, cid)
        try:
            for _ in range(10):
                content, reasoning, calls = await self._stream(client, model, msgs, sid, started)
                shown += content
                thinking += reasoning
                if not calls:
                    break
                msgs.append({"role": "assistant", "content": content, "reasoning_content": reasoning,
                             "tool_calls": [{"id": c["id"], "type": "function",
                                             "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                                            for c in calls]})
                for c in calls:
                    try:
                        args = json.loads(c["args"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    out = await self._tool(c["name"], args)
                    if isinstance(out, tuple):          # look_at_screen：文字 + 截图
                        out, png = out
                        shots.append(png)
                    msgs.append({"role": "tool", "tool_call_id": c["id"], "content": out})
                if shots:   # 图片要放在所有 tool 消息之后；只在本轮用，不存进记录
                    msgs.append(ctools.image_message(shots[-1], _s('audit_09f61ea103')))
                    shots = []
                if shown and not shown.endswith("\n"):
                    shown += "\n\n"
                    await self.emit({"type": "stream", "sid": sid, "delta": "\n\n"}, cid)
            if not shown.strip():   # 工具轮数用完还没开口：关掉工具，逼它给一句回复
                content, reasoning, _ = await self._stream(client, model, msgs, sid, started, use_tools=False)
                shown, thinking = content, thinking + reasoning
        finally:
            await self.emit({"type": "stream_end", "sid": sid}, cid)
        await self.add("assistant", shown.strip(), cid, reasoning=reasoning, thinking=thinking,
                       thought_s=round(time.time() - started, 1), sid=sid, tasks=self._turn_tasks)
        return shown.strip()

    def _member(self, name: str) -> dict | None:
        """群里按名字找成员（不区分大小写，去掉开头的 @）。"""
        key = (name or "").strip().lstrip("@").lower()
        for i in self.chat["bot_ids"]:
            m = bots.get(i)
            if m and m["name"].lower() == key:
                return m
        return None

    async def _tool(self, name: str, args: dict) -> str:
        if name == "dispatch":
            if self._over_budget():
                return _s('audit_51308b240d')
            handoff = None
            if args.get("handoff_to") and self.chat["kind"] == "group":
                to = self._member(args["handoff_to"])
                if not to or to["id"] == self.bot_id:
                    return _s('audit_9464ec679b', v0=args['handoff_to'])
                handoff = {"to": to["id"], "note": args.get("handoff_note") or ""}
                from . import groups
                groups.expect(self.chat["id"], to["id"])
            task = await self.dispatch(args["goal"], args.get("mode", "single"), chat_id=self.chat["id"], handoff=handoff,
                                       reply=self.turn.get("reply"), depth=self.turn.get("depth", 0))
            self._turn_tasks.append(task.id)
            if handoff:
                return _s('audit_ae361a0c06', v0=task.id, v1=to['name'])
            if task.reply:
                return _s('audit_9506ddd435', v0=task.id, v1=dm._name(task.reply['bot']))
            return _s('audit_f850cb7c33', v0=task.id)
        if name == "message_bot":
            to = bots.by_name(args.get("to", ""))
            if not to or to["id"] == self.bot_id:
                others = "、".join(b["name"] for b in bots.list_bots() if b["id"] != self.bot_id)
                return _s('audit_27f5f05137', v0=args.get('to'), v1=others or _s('audit_72077749f7'))
            if self.chat["kind"] == "group" and to["id"] in self.chat["bot_ids"]:
                return _s('audit_7efa74a2b2', v0=to['name'])
            out = await dm.send(self.bot_id, to, args.get("text", ""), self.chat["id"],
                                self.turn.get("reply"), self.turn.get("depth", 0))
            if out.startswith(_s('audit_15fa749f87')):
                self._turn_dms += 1
            return out
        if name == "handoff":
            if self.chat["kind"] != "group":
                return _s('audit_2876c4da2f')
            to = self._member(args.get("to", ""))
            if not to or to["id"] == self.bot_id:
                return _s('audit_f04fc34682', v0=args.get('to'))
            from . import groups
            await groups.handoff(self.chat["id"], self.bot_id, to["id"], args.get("request", ""))
            return _s('audit_03283ed8d2', v0=to['name'])
        if name == "save_skill":
            try:
                s = skills.save(self.bot_id, args.get("name", ""), args.get("body", ""), args.get("description", ""), "chat")
            except ValueError as e:
                return _s('audit_b480594004', v0=e)
            await self.emit({"type": "skills_changed"})
            return _s('audit_361bc34a36', v0=s['name'])
        if name == "create_routine":
            kind = args.get("kind")
            trig = {"kind": kind, "times": args.get("times") or [], "days": args.get("days") or [],
                    "minutes": args.get("minutes")}
            try:
                r = routines.save(self.bot_id, {"name": args.get("name", ""), "prompt": args.get("prompt", ""),
                                                "skill": args.get("skill", ""), "trigger": trig})
            except (ValueError, TypeError) as e:
                return _s('audit_4dbfa56697', v0=e)
            await self.emit({"type": "routines_changed"})
            when = routines.describe(r["trigger"])
            if r["next_run"]:
                when += _s('audit_90e59ce604') + time.strftime("%m-%d %H:%M", time.localtime(r["next_run"]))
            if kind == "webhook":
                when += _s('audit_8070f3dc39', v0=r['name'])
            return _s('audit_649b7fe635', v0=r['name'], v1=when)
        if name == "remember":
            return await self._remember(args)
        if name == "forget":
            mid = args.get("id")
            if not isinstance(mid, int) or not memories.visible(mid, self.bot_id):
                return _s('audit_6f70561d43', v0=mid)
            memories.delete(mid)
            await self.emit({"type": "memories_changed"})
            return _s('audit_057e95952e', v0=mid)
        if name == "save_page":
            out = library.tool_save_page(self.bot_id, args)
            await self.emit({"type": "pages_changed"})
            return out
        if name == "list_tasks":
            return self._task_list()
        if name == "cancel_task":
            woke = self.turn.get("woke")
            if not woke:
                return self.cancel(args["task_id"], _s('audit_337611aec4'))
            t, owed = self.tasks.get(args["task_id"]), self.turn.get("reply")
            if t and t.reply and owed and dm.same(t.reply, owed):
                t.reply = None   # 还是回给同一个 Bot：这一轮的回复或新派的任务会接着回它，不用再说一声“已取消”
            return self.cancel(args["task_id"], _s('audit_392cf1bf28', v0=self.bot['name'], v1=dm._name(woke['from'])))
        if name == "resolve_approval":
            return approvals.resolve(args["id"], args["approve"], args.get("note", ""), bool(args.get("always")))
        if name == "recall":
            return memory.recall(args["id"], self.chat["id"])
        if name == "search_memory":
            return await search.tool(self.bot_id, args)
        if name == "read_page":
            return library.tool_read_page(args)
        if name == "look_at_screen":
            return await self._look()
        if name in DIRECT_PC:
            return await self._direct(name, args)
        return _s('audit_60cd83a713')

    async def _remember(self, args: dict) -> str:
        owner = None if args.get("shared") else self.bot_id
        rid = args.get("replace_id")
        try:
            if isinstance(rid, int) and memories.visible(rid, self.bot_id):
                # 没说 shared 就保持原来的归属，免得改一条共享事实时把它变成私有的
                m = memories.update(rid, args.get("text", ""), owner if "shared" in args else memories.get(rid)["bot_id"])
            else:
                m = memories.add(owner, args.get("text", ""), "chat")
        except ValueError as e:
            return _s('audit_068985281f', v0=e)
        await self.emit({"type": "memories_changed"})
        return _s('audit_f53573d0d4', v0=m['id'], v1=_s('audit_fa7dc2dc1a') if m['shared'] else _s('audit_d17b39e953'), v2=m['text'])

    async def _direct(self, name: str, args: dict):
        """Router 自己动手做简单的电脑操作；电脑被任务占着就不等，让模型决定要不要先取消任务。"""
        from types import SimpleNamespace
        from . import computer
        c = computer.get()
        key = f"chat-{self.bot_id}"
        if c.owner and c.owner != key:
            return _s('audit_88a2cb73ac', v0=c.owner_label)
        if c.controller == "human":
            return _s('audit_cc1123998d')
        if (await c.status())["state"] != "running":
            await c.start()
        token = ctools.CLAIM.set(key)
        try:
            fake = SimpleNamespace(id=_s('audit_e6222f4687', v0=self.bot['name']), bot_id=self.bot_id, chat_id=self.chat_id)
            async def noop(_): pass
            text, png = await ctools.call(fake, name, args, noop)
            await c.release(key)   # 一步一放，不挡后台任务
        finally:
            ctools.CLAIM.reset(token)
        return (text, png) if png else text

    async def _look(self):
        from . import computer
        c = computer.get()
        try:
            if (await c.status())["state"] != "running":
                return _s('audit_3fbaabf360')
            png = await c.screenshot()
            title = (await c.exec("DISPLAY=:1 xdotool getactivewindow getwindowname 2>/dev/null", timeout=10)).stdout.strip()
        except Exception as e:
            return _s('audit_9b5fadead5', v0=e)
        who = _s('audit_e0bc08c2cb', v0=c.owner_label) if c.owner else _s('audit_837e7a109a')
        if c.controller == "human":
            who = _s('audit_12bbdf292b')
        return (_s('audit_c24dd21a25', v0=title or _s('audit_72077749f7'), v1=who), png)

    def _capabilities(self) -> str:
        from . import catalog, mcp_hub, tools
        lines = [f"- {n}：{d}" for n, (_, d, _) in tools.TOOLS.items()]
        if (CFG.get("computer") or {}).get("enabled", True):
            lines.append(_s('audit_b969a7f5b3'))
        groups: dict[str, list[str]] = {}
        for full in mcp_hub.TOOLS:
            server, _, tool = full.partition("__")
            groups.setdefault(server, []).append(tool)
        def label(n: str) -> str:
            t = catalog.title(n)
            return f"@{n}" if t == "@" + n else f"@{n}（{t}）"
        lines += [_s('audit_5bb6ba1a30', v0=label(srv), v1=', '.join(ts)) for srv, ts in groups.items()]
        off = [n for n in mcp_hub.all_apps() if n not in groups]
        if off:
            lines.append(_s('audit_7ef4dbd1fc', v0=', '.join((label(n) for n in off))))
        return "\n".join(lines)

    async def dispatch(self, goal: str, mode: str = "single", background: bool = False,
                       on_done=None, label: str = "", chat_id: int | None = None, handoff: dict | None = None,
                       reply: dict | None = None, depth: int = 0) -> Task:
        """派一个后台任务。定时任务也走这里（background=True，确认卡片会过期）。
        chat_id 是任务卡片和结果出现的对话（默认私聊）；确认卡片总是发到私聊。
        reply：因私信派的任务，做完把结果作为回信送回去（见 dm.py）。"""
        cid = chat_id or self.chat_id
        tid = await self.add("task", _s('audit_302b4261f3', v0=label + ' ' if label else '', v1=goal), cid, kind="dispatch",
                             mode=mode, status="running", **({"handoff_to": handoff["to"]} if handoff else {}),
                             **({"reply_to": reply["bot"]} if reply else {}))
        task = Task(id=tid, goal=goal, mode=mode, bot_id=self.bot_id, chat_id=cid, approval_chat_id=self.chat_id,
                    background=background, on_done=on_done, handoff=handoff, reply=reply, depth=depth)
        task.handle = asyncio.create_task(self._run(task))
        TASKS[tid] = task
        await self.emit({"type": "task", "task": task.public()}, cid)
        return task

    def _routine_list(self) -> str:
        return "\n".join(f"- {r['name']}（{routines.describe(r['trigger'])}{'' if r['enabled'] else _s('audit_e41798aa3a')}）"
                         for r in routines.list_for(self.bot_id)) or _s('audit_5dbd015496')

    def _task_list(self) -> str:
        return "\n".join(_s('audit_823e22252a', v0=t.id, v1=_s('audit_25a45621ed') if t.waiting_approval else t.status, v2=t.mode, v3=t.steps, v4=t.goal[:50])
                         for t in self.tasks.values()) or _s('audit_15652e6de7')

    async def _run(self, task: Task):
        try:
            task.result = await (run_heavy(task) if task.mode == "heavy" else run_worker(task, task.goal))
            task.status = "done"
            if not task.background:   # 定时任务有自己的运行记录，不记进“做过的事”
                memories.log_work(self.bot_id, task.id, task.goal)
        except asyncio.CancelledError:
            asked = task.status == "cancelled"   # cancel() 先标了状态；服务关闭时被取消的不算
            task.status = "cancelled"
            if task.handoff:
                from . import groups
                groups.unexpect(task.chat_id, task.handoff["to"])
            if task.reply and asked:
                asyncio.create_task(dm.after_task(task))
            await self._done(task)
            return
        except Exception as e:
            task.status, task.result = "failed", _s('audit_ad0519c7e0', v0=e)
        await tasklog.close(task, task.status, task.result if task.status == "failed" else "")
        memory.update_meta(task.id, status=task.status, elapsed=round(time.time() - task.started), steps=task.steps)
        await self.add("task", _s('audit_04abb034fe', v0=task.id, v1=task.result), task.chat_id, kind="result", task_id=task.id,
                       status=task.status, elapsed=round(time.time() - task.started))
        await self.emit({"type": "task", "task": task.public()}, task.chat_id)
        if task.handoff:
            from . import groups
            asyncio.create_task(groups.after_task(task))
        if task.reply:
            asyncio.create_task(dm.after_task(task))
        await self._done(task)

    async def _done(self, task: Task):
        if task.on_done:
            try:
                await task.on_done(task)
            except Exception:
                pass

    def cancel(self, tid: int, reason: str) -> str:
        t = self.tasks.get(tid)
        if not t or t.status != "running":
            return _s('audit_6f7c328a66', v0=tid)
        approvals.cancel_for_task(tid)
        t.handle.cancel()
        t.status, t.result = "cancelled", _s('audit_1f8dfcbb1d', v0=reason)
        memory.update_meta(tid, status="cancelled", elapsed=round(time.time() - t.started), steps=t.steps)
        asyncio.create_task(tasklog.close(t, "cancelled", _s('audit_1f8dfcbb1d', v0=reason)))
        asyncio.create_task(self.add("task", _s('audit_15af67908c', v0=tid, v1=reason), t.chat_id, kind="cancel", task_id=tid))
        asyncio.create_task(self.emit({"type": "task", "task": t.public()}, t.chat_id))
        return _s('audit_dd1c646ca1', v0=tid)
