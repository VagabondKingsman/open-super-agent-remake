"""Bot 管理 Bot：查看、新建、修改、删除（Router 的 get_bot / create_bot / update_bot / delete_bot 工具）。

谁能做什么：
- 主 Bot 管所有 Bot：查看、新建、修改（包括它自己）、删除（不能删主 Bot，也就是不能删它自己）。
- 别的 Bot 只有 update_bot，只能改它自己；要新建、删除或改别的 Bot，私信主 Bot（提示词里写着）。
确认：
- 新建、修改、删除每次都先弹卡片（不能“总是允许”），卡片在发起的 Bot 的私聊里，同意才做；查看不用确认。
  修改的卡片上有职责的改动（删掉的划掉、加上的标出来），删除的卡片上写着会一起删掉什么。
- 和画图一样不让 Router 干等：工具马上返回，卡片和改动在后台进行；用户也能在对话里说“建吧”（resolve_approval）。
- 等确认的时候情况可能变了（同名的建了、要改的 Bot 被删了），同意后按原来的参数再检查一遍才做。
结果：
- 做成了在调用的那个对话里记一条（kind=bot_created / bot_updated / bot_deleted，界面上能点过去），侧栏马上变。
- 有了结果（做成、用户没同意、没做成）就叫醒发起的 Bot 在那个对话里接着说一轮（dm.wake，kind=botadmin），它才知道结果，
  好去做答应过的事（比如私信新 Bot 交代事情）。用户没同意又没附意见、也没有 Bot 等着的，不叫醒。
  是别的 Bot 私信托它做的，那一轮的回复不当场送回，等有了结果，叫醒的这一轮的回复作为回信送回去（同 dispatch）。
"""
import asyncio
import difflib
import re
import time
from types import SimpleNamespace
from . import approvals, bots, dm, i18n, memories, routines, skills
from .memory import conn

MAX_SKILLS = 10          # 一次带上或改的技能
MAX_INSTRUCTIONS = 4000
MAX_SKILL_SHOWN = 3000   # 查看时每个技能的做法最多给模型看这么多，要全文用 skill 参数
CARD_LIMIT = 12000       # 卡片参数（JSON）的长度：职责最长 4000 字，改动里新旧两份都有
CARD_SHOWN = "Approval card shown"   # tool-result prefix; router counts these as waits

_SKILL_ITEMS = {"type": "object", "properties": {
    "name": {"type": "string", "description": "short name, used to invoke it as /name; no spaces"},
    "description": {"type": "string", "description": "one sentence on when to use it"},
    "body": {"type": "string", "description": "the full method: steps, websites or apps to use, output format"}},
    "required": ["name", "body"]}
_AVATAR = {"type": "object", "description": "optional: avatar, a shape plus a color",
           "properties": {"shape": {"type": "string", "enum": bots.SHAPES},
                          "color": {"type": "string", "enum": bots.COLORS}}}

GET_BOT = {"type": "function", "function": {
    "name": "get_bot",
    "description": "View Bot profiles; no confirmation needed. Without name: an overview of all Bots (start of the role, number of skills and routines, which groups, when last chatted, "
                   "whether tasks are running); with name: the full profile of that Bot (full role, skills and methods, routines, groups, running tasks). "
                   "Use it to see the original text before changing a role or skills",
    "parameters": {"type": "object", "properties": {
        "name": {"type": "string", "description": "optional: the Bot's name"},
        "skill": {"type": "string", "description": "optional: only show the full method of this one of its skills (without /)"}}}}}

CREATE_BOT = {"type": "function", "function": {
    "name": "create_bot",
    "description": "Create a new Bot. A card is shown first for the user to confirm (with the name, role and skills); once approved it is created automatically. "
                   "When there is an outcome (created, not approved, failed) you get another turn to speak; whatever should happen after it is created (e.g. DM it instructions) is done then.",
    "parameters": {"type": "object", "properties": {
        "name": {"type": "string", "description": "name, at most 40 characters, must not duplicate an existing Bot"},
        "instructions": {"type": "string", "description": "its role and way of working, written in full: what it is responsible for, how, and any hard constraints. "
                                                          "Other Bots also use this text to decide what to ask it"},
        "avatar": _AVATAR,
        "skills": {"type": "array", "description": f"optional: skills (reusable methods) to give it, at most {MAX_SKILLS}",
                   "items": _SKILL_ITEMS}},
        "required": ["name", "instructions"]}}}


def _update_schema(primary: bool) -> dict:
    who = "which Bot to change (its current name); to change yourself, put your own name" if primary else "put your own name: you are not the primary Bot and can only change yourself"
    return {"type": "function", "function": {
        "name": "update_bot",
        "description": ("Change a Bot" if primary else "Change yourself") + ": name, role, avatar, skills; fill in only what changes. "
                       "A card is shown first for the user to confirm (showing before and after); once approved the change is applied automatically; when there is an outcome you get another turn to speak",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": who},
            "new_name": {"type": "string", "description": "optional: new name, at most 40 characters"},
            "instructions": {"type": "string", "description": "optional: the complete role after the change: the full text, not just the changes. "
                                                              "First read the original with get_bot, change only what must change, and copy the rest word for word"},
            "avatar": _AVATAR,
            "skills": {"type": "array", "description": f"optional: skills to add, or to replace entirely when the name matches (write the full method), at most {MAX_SKILLS}",
                       "items": _SKILL_ITEMS},
            "remove_skills": {"type": "array", "items": {"type": "string"}, "description": "optional: its skills to remove, by name (without /)"}},
            "required": ["name"]}}}


DELETE_BOT = {"type": "function", "function": {
    "name": "delete_bot",
    "description": "Delete a Bot together with its DM history, skills, routines and its own memories; this cannot be undone. It leaves its groups and its running tasks stop. "
                   "Use only when the user explicitly asks to delete. A card is shown first for the user to confirm and it is deleted only once approved; when there is an outcome you get another turn to speak",
    "parameters": {"type": "object", "properties": {
        "name": {"type": "string", "description": "name of the Bot to delete"},
        "reason": {"type": "string", "description": "why it is being deleted; shown to the user on the card"}},
        "required": ["name"]}}}

TOOLS = {"get_bot", "create_bot", "update_bot", "delete_bot"}


def tools_for(bot: dict) -> list[dict]:
    """主 Bot 四个都有；别的 Bot 只有 update_bot（只能改自己）。"""
    if bot.get("is_primary"):
        return [GET_BOT, CREATE_BOT, _update_schema(True), DELETE_BOT]
    return [_update_schema(False)]


# 结果写进对话的样子：(做成了, 没同意, 没同意附了意见, 没做成)。kind 是做成那一条的 meta.kind
TEXT = {
    "create_bot": ("bot_created", i18n.N_("[已新建 Bot「{name}」]"), i18n.N_("[没新建 Bot「{name}」]"),
                   i18n.N_("[没新建 Bot「{name}」：{note}]"), i18n.N_("[没建成 Bot「{name}」：{error}]")),
    "update_bot": ("bot_updated", i18n.N_("[已修改 Bot「{name}」：{what}]"), i18n.N_("[没修改 Bot「{name}」]"),
                   i18n.N_("[没修改 Bot「{name}」：{note}]"), i18n.N_("[没改成 Bot「{name}」：{error}]")),
    "delete_bot": ("bot_deleted", i18n.N_("[已删除 Bot「{name}」]"), i18n.N_("[没删除 Bot「{name}」]"),
                   i18n.N_("[没删除 Bot「{name}」：{note}]"), i18n.N_("[没删成 Bot「{name}」：{error}]")),
}
GOAL = {"create_bot": i18n.N_("新建 Bot"), "update_bot": i18n.N_("修改 Bot"), "delete_bot": i18n.N_("删除 Bot")}

_running: set[asyncio.Task] = set()   # 后台等确认、做改动的，留个引用免得被回收


# ---------- 检查参数（不行报 ValueError，写给模型看） ----------
def _name(name, exclude: int | None = None) -> str:
    name = str(name or "").strip().lstrip("@").strip()
    if not name:
        raise ValueError("The name is empty")
    if len(name) > 40:
        raise ValueError("The name can be at most 40 characters")
    if (b := bots.by_name(name)) and b["id"] != exclude:
        raise ValueError(f"A Bot named {b['name']} already exists; pick another name" + (", or just reach it with message_bot" if exclude is None else ""))
    return name


def _instructions(text) -> str:
    text = str(text or "").strip()
    if not text:
        raise ValueError("The role is empty: state what it is responsible for and how")
    if len(text) > MAX_INSTRUCTIONS:
        raise ValueError(f"The role is too long ({len(text)} characters); at most {MAX_INSTRUCTIONS}, shorten it")
    return text


def _avatar(a) -> dict | None:
    if not isinstance(a, dict) or not (a.get("shape") or a.get("color")):
        return None
    shape, color = a.get("shape"), str(a.get("color") or "")
    if shape and shape not in bots.SHAPES:
        raise ValueError(f"The avatar shape must be one of {', '.join(bots.SHAPES)}")
    if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError(f"The avatar color must be #RRGGBB, e.g. {bots.COLORS[0]}")
    return {k: v for k, v in (("shape", shape), ("color", color.lower())) if v}


def _skills(items) -> list[dict]:
    if not isinstance(items, list):
        items = []
    if len(items) > MAX_SKILLS:
        raise ValueError(f"At most {MAX_SKILLS} skills at a time")
    out, seen = [], set()
    for s in items:
        s = s if isinstance(s, dict) else {}
        try:
            n = skills._check(str(s.get("name") or ""), str(s.get("body") or ""))
        except ValueError as e:
            raise ValueError(f"Skill {s.get('name') or '(unnamed)'}: {e}") from None
        if n in seen:
            raise ValueError(f"Skill /{n} is listed twice")
        seen.add(n)
        out.append({"name": n, "description": str(s.get("description") or "")[:200], "body": str(s["body"])})
    return out


def _target(name) -> dict:
    b = bots.by_name(str(name or ""))
    if not b:
        others = ", ".join(x["name"] for x in bots.list_bots())
        raise ValueError(f"No Bot named {name} (it was not created or has been deleted, even if memory says it exists). Existing: {others}")
    return b


def _own_skills(bot_id: int) -> dict[str, dict]:
    return {s["name"]: s for s in skills.list_for(bot_id) if s["bot_id"] == bot_id}


def _skill_line(s: dict) -> str:
    return f"/{s['name']}：{s['description'] or s['body'][:60]}"


def plan_create(me: dict, args: dict) -> dict:
    if not me.get("is_primary"):
        raise ValueError(f"Only the primary Bot ({bots.primary_name()}) can create Bots; DM it with message_bot and state the name and role clearly")
    name = _name(args.get("name"))
    if len(bots.list_bots()) >= bots.MAX_BOTS:
        raise ValueError(f"There are already {bots.MAX_BOTS} Bots, the limit; ask the user to delete unused ones first")
    plan = {"name": name, "instructions": _instructions(args.get("instructions")),
            "avatar": _avatar(args.get("avatar")), "skills": _skills(args.get("skills"))}
    shown = {"名字": name, "职责": plan["instructions"], "技能": [_skill_line(s) for s in plan["skills"]]}
    if plan["avatar"]:
        shown["头像"] = plan["avatar"]
    return {**plan, "label": name, "shown": shown}


def _diff(old: str, new: str) -> list[list]:
    """职责的改动，按分句比：[[0, 没变的], [-1, 删掉的], [1, 加上的], …]。中文一句一句地比，比逐字比好读。"""
    split = lambda s: [x for x in re.split(r"(?<=[。！？；;!?\n])", s) if x]
    a, b = split(old), split(new)
    out: list[list] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        for sign, part in [(0, a[i1:i2])] if op == "equal" else [(-1, a[i1:i2]), (1, b[j1:j2])]:
            if not part:
                continue
            if out and out[-1][0] == sign:
                out[-1][1] += "".join(part)
            else:
                out.append([sign, "".join(part)])
    return out


def plan_update(me: dict, args: dict) -> dict:
    t = _target(args.get("name"))
    if not me.get("is_primary") and t["id"] != me["id"]:
        raise ValueError(f"You can only change yourself. To change {t['name']}, DM the primary Bot \"{bots.primary_name()}\" and state clearly what to change it to")
    plan: dict = {"id": t["id"]}
    shown: dict = {"Bot": t["name"], "编号": t["id"]}
    what: list[str] = []
    new_name = str(args.get("new_name") or "").strip().lstrip("@").strip()
    if new_name and new_name != t["name"]:
        plan["name"] = shown["新名字"] = _name(new_name, exclude=t["id"])
        what.append(i18n.t("名字改成 {name}", name=new_name))
    text = str(args.get("instructions") or "").strip()
    if text and text != t["instructions"].strip():
        plan["instructions"] = shown["职责"] = _instructions(text)
        shown["职责改动"] = _diff(t["instructions"], text)
        what.append(i18n.t("职责"))
    av = _avatar(args.get("avatar"))
    if av:
        old = t["avatar"]
        new = {"shape": av.get("shape") or old["shape"], "color": av.get("color") or old["color"]}
        if new != {"shape": old["shape"], "color": old["color"]} or old.get("image"):
            plan["avatar"] = shown["头像"] = new   # 有图片头像的，换成形状和颜色就不再用那张图
            if old.get("image"):
                shown["不再用图片头像"] = True
            what.append(i18n.t("头像"))
    own = _own_skills(t["id"])
    add = _skills(args.get("skills"))
    drop = [str(n or "").strip().lstrip("/") for n in (args.get("remove_skills") or []) if str(n or "").strip()]
    for n in drop:
        if n not in own:
            mine = ", ".join("/" + x for x in own) or "none"
            raise ValueError(f"{t['name']} has no skill of its own /{n} (shared skills cannot be deleted here). Its own skills: {mine}")
        if any(s["name"] == n for s in add):
            raise ValueError(f"Skill /{n} is both removed and changed; keep only one")
    if add or drop:
        if len(own) - len(drop) + len([s for s in add if s["name"] not in own]) > skills.MAX_PER_BOT:
            raise ValueError(f"At most {skills.MAX_PER_BOT} skills per Bot")
        plan["skills"], plan["remove_skills"] = add, sorted(set(drop))
        if new := [_skill_line(s) for s in add if s["name"] not in own]:
            shown["新技能"] = new
        if changed := [_skill_line(s) for s in add if s["name"] in own]:
            shown["改技能"] = changed
        if plan["remove_skills"]:
            shown["删技能"] = ["/" + n for n in plan["remove_skills"]]
        what.append(i18n.t("技能") + " " + " ".join(f"/{n}" for n in [*(s["name"] for s in add), *plan["remove_skills"]]))
    if len(plan) == 1:
        raise ValueError("Nothing to change: the changes match the current state, or nothing was filled in. Fill in at least one of name, role, avatar, skills")
    return {**plan, "label": t["name"], "shown": shown, "what": i18n.t("、").join(what)}


def _footprint(b: dict) -> dict:
    """删掉一个 Bot 会一起删掉什么。"""
    from . import router
    n_msgs = conn.execute("select count(*) from messages where chat_id=?", (b["chat_id"],)).fetchone()[0] if b["chat_id"] else 0
    in_groups = [c for c in bots.list_chats() if c["kind"] == "group" and b["id"] in c["bot_ids"]]
    return {"会删掉": {"消息": n_msgs, "技能": len(_own_skills(b["id"])), "定时任务和事件": len(routines.list_for(b["id"])),
                    "记忆": len(memories.list_for(b["id"])["own"])},
            "群聊": [c["title"] for c in in_groups],
            "在做的任务": sum(1 for t in router.TASKS.values() if t.bot_id == b["id"] and t.status == "running")}


def plan_delete(me: dict, args: dict) -> dict:
    if not me.get("is_primary"):
        raise ValueError(f"Only the primary Bot ({bots.primary_name()}) can delete Bots")
    t = _target(args.get("name"))
    if t["id"] == me["id"] or t["is_primary"]:
        raise ValueError("The primary Bot cannot be deleted. To delete it, ask the user to first make another Bot primary in Settings")
    shown = {"Bot": t["name"], "编号": t["id"], **_footprint(t)}
    if reason := str(args.get("reason") or "").strip():
        shown["原因"] = reason[:500]
    return {"id": t["id"], "label": t["name"], "shown": shown}


PLAN = {"create_bot": plan_create, "update_bot": plan_update, "delete_bot": plan_delete}
# 用户能在卡片上直接改的：卡片参数的键 → 工具参数。新建和修改时的职责（改后的全文）
EDITABLE = {"create_bot": {"职责": "instructions"}, "update_bot": {"职责": "instructions"}}


# ---------- 做 ----------
async def remove(bot_id: int):
    """删掉一个 Bot 和它的一切（网页上删和主 Bot 删都走这里）：停掉它在做的任务，删私聊、技能、定时任务、它自己的记忆；
    群里移出；聊天软件绑着它的私聊的，改成和主 Bot 对话。共享的用户事实、资料库里的页面留着。主 Bot 不能删（ValueError）。"""
    from . import channels, router
    b = bots.get(bot_id)
    if not b:
        return
    if b["is_primary"]:
        raise ValueError(i18n.t("主 Bot 不能删除，先把别的 Bot 设为主 Bot"))
    for t in list(router.TASKS.values()):
        if t.bot_id == bot_id and t.status == "running":
            router.cancel(t.id, i18n.t("Bot 已删除"))
    approvals.cancel_for_bot(bot_id)
    bots.delete(bot_id)
    routines.delete_for_bot(bot_id)
    memories.delete_for_bot(bot_id)
    conn.execute("delete from skills where bot_id=?", (bot_id,))
    conn.commit()
    router.RUNTIMES.pop(bot_id, None)
    channels.chat_removed(b["chat_id"])


async def _apply(tool: str, plan: dict, chat_id: int, post, emit) -> str:
    """同意后做。返回记进对话的那条（做成了）。"""
    kind, done = TEXT[tool][0], TEXT[tool][1]
    if tool == "create_bot":
        b = bots.create(plan["name"], plan["avatar"], plan["instructions"])
        for s in plan["skills"]:
            skills.save(b["id"], s["name"], s["body"], s["description"], "chat")
        text = i18n.t(done, name=b["name"])
        meta = {"new_bot": b["id"]}
    elif tool == "update_bot":
        for n in plan.get("remove_skills") or []:
            if s := _own_skills(plan["id"]).get(n):
                skills.delete(s["id"])
        for s in plan.get("skills") or []:
            skills.save(plan["id"], s["name"], s["body"], s["description"], "chat")
        b = bots.update(plan["id"], name=plan.get("name"), instructions=plan.get("instructions"), avatar=plan.get("avatar"))
        text = i18n.t(done, name=b["name"], what=plan["what"])
        meta = {"bot": b["id"]}
    else:
        await remove(plan["id"])
        text = i18n.t(done, name=plan["label"])
        meta = {}
    await emit({"type": "bots_changed"})
    if plan.get("skills") or plan.get("remove_skills"):
        await emit({"type": "skills_changed"})
    await post("task", text, chat_id, kind=kind, **meta)
    return text


async def call(tool: str, bot: dict, chat_id: int, private_chat_id: int, args: dict, post, emit,
               owed: dict | None = None, depth: int = 0) -> str:
    """Router 调的入口。bot：谁在调；chat_id：结果记在哪个对话；private_chat_id：卡片发到哪（它的私聊）。
    post 是 Router.add：(role, content, chat_id, **meta)；emit 是 Router.emit。
    owed、depth：这一轮欠谁回信、私信深度（见 dm.py），有了结果叫醒它时带上。"""
    if tool == "get_bot":
        return view(bot, args)
    verb = {"create_bot": "create", "update_bot": "change", "delete_bot": "delete"}[tool]
    try:
        plan = PLAN[tool](bot, args)
    except ValueError as e:
        return f"Did not {verb}: {e}"
    shown = plan["shown"] | ({"请求方": dm._name(owed["bot"])} if owed else {})
    fake = SimpleNamespace(id=f"对话·{bot['name']}", bot_id=bot["id"], chat_id=chat_id, approval_chat_id=private_chat_id,
                           goal=i18n.t(GOAL[tool]), background=False, waiting_approval=None)
    _, _, no, no_note, failed = TEXT[tool]
    label = plan["label"]

    async def tell(text: str, edited: list[str] | None = None):
        """叫醒发起的 Bot 在这个对话里接着说一轮（见 dm.wake），它从最近的系统通知里看到结果。
        edited：用户在卡片上改过哪些（卡片参数的键），它要以改过的为准。"""
        await dm.wake(bot["id"], chat_id, {"reply": owed, "depth": depth, "woke": {
            "kind": "botadmin", "from": bot["id"], "text": text, **({"edited": edited} if edited else {})}})

    editable = EDITABLE.get(tool, {})

    async def wait_and_do():
        ok, note = await approvals.request(fake, tool, shown, once=True, limit=CARD_LIMIT,
                                           editable=tuple(k for k in editable if k in shown))
        if not bots.get(bot["id"]):   # 等的时候发起的 Bot 自己被删了
            return
        if not ok:   # 记一笔：下一轮模型知道用户没同意（和附带的意见），不会以为做成了
            text = i18n.t(no_note, name=label, note=note) if note else i18n.t(no, name=label)
            await post("task", text, chat_id, kind="note")
            if note or owed:   # 用户附了意见要它改，或者有 Bot 等着结果
                await tell(text)
            return
        # 用户在卡片上改过的（已经写回 shown）换进参数里
        edited = [k for k in editable if k in shown and shown[k] != plan["shown"][k]]
        final = {**args, **{editable[k]: shown[k] for k in edited}}
        try:
            fresh = PLAN[tool](bots.get(bot["id"]), final)   # 等确认的时候情况可能变了：再检查一遍
            text = await _apply(tool, fresh, chat_id, post, emit)
        except ValueError as e:
            text = i18n.t(failed, name=label, error=e)
            await post("task", text, chat_id, kind="note")
        await tell(text, edited)

    t = asyncio.create_task(wait_and_do())
    _running.add(t)
    t.add_done_callback(_running.discard)
    what = {"create_bot": f"create Bot \"{label}\"", "update_bot": f"change Bot \"{label}\"", "delete_bot": f"delete Bot \"{label}\""}[tool]
    after = f"; your reply then goes to {dm._name(owed['bot'])} as the answer" if owed else ""
    return (f"{CARD_SHOWN} ({what}); the card is in your private chat. Once the user approves, it will {verb} it automatically. "
            f"When there is an outcome you get another turn to speak{after}; whatever should happen afterwards (e.g. DM the new Bot instructions) is done then. "
            f"For now just briefly ask the user to confirm; do not say it is already done.")


# ---------- 查看 ----------
def _when(ts) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)) if ts else "never chatted"


def _chat_stats(b: dict) -> tuple[int, float | None]:
    if not b["chat_id"]:
        return 0, None
    n, last = conn.execute("select count(*), max(ts) from messages where chat_id=?", (b["chat_id"],)).fetchone()
    return n, last


def _groups_of(bot_id: int) -> list[dict]:
    return [c for c in bots.list_chats() if c["kind"] == "group" and bot_id in c["bot_ids"]]


def _running_tasks(bot_id: int) -> list:
    from . import router
    return [t for t in router.TASKS.values() if t.bot_id == bot_id and t.status == "running"]


def _overview(me: dict) -> str:
    rows = bots.list_bots()
    lines = [f"{len(rows)} Bots (at most {bots.MAX_BOTS}):"]
    for b in rows:
        tags = [x for x in ("primary Bot" if b["is_primary"] else "", "that is you" if b["id"] == me["id"] else "") if x]
        _, last = _chat_stats(b)
        role = (b["instructions"] or "role not stated").replace("\n", " ")
        rs = routines.list_for(b["id"])
        ne = sum(1 for r in rs if routines.is_event(r))
        stats = [f"{len(_own_skills(b['id']))} skills", f"{len(rs) - ne} routines"] + ([f"{ne} events"] if ne else [])
        if g := _groups_of(b["id"]):
            stats.append(f"in {len(g)} groups")
        if r := _running_tasks(b["id"]):
            stats.append(f"running {len(r)} tasks")
        stats.append(f"last DM: {_when(last)}")
        lines.append(f"- {b['name']}{' (' + ', '.join(tags) + ')' if tags else ''}: {role[:60]}{'…' if len(role) > 60 else ''}"
                     f" | {', '.join(stats)}")
    lines.append("To see a Bot's full role and skills, call get_bot with name.")
    return "\n".join(lines)


def _detail(b: dict, me: dict) -> str:
    n, last = _chat_stats(b)
    av = b["avatar"]
    head = [f"{b['name']} ({'primary Bot' if b['is_primary'] else 'regular Bot'}{', that is you' if b['id'] == me['id'] else ''})",
            f"Created {_when(b['created'])}; avatar: {av.get('shape')} {av.get('color')}{' (an image is used)' if av.get('image') else ''}",
            f"DM: {n} messages, latest {_when(last)}",
            "Role:", b["instructions"] or "(not written)"]
    own = list(_own_skills(b["id"]).values())
    shared = [s for s in skills.list_for(b["id"]) if s["bot_id"] is None and s["name"] not in {x["name"] for x in own}]
    parts = ["\n".join(head), f"Its own skills ({len(own)}):" if own else "Its own skills: none"]
    budget = 12000
    for s in own:
        body = s["body"] if len(s["body"]) <= MAX_SKILL_SHOWN else \
            s["body"][:MAX_SKILL_SHOWN] + f"\n… ({len(s['body']) - MAX_SKILL_SHOWN} more characters; for the full text use the skill parameter of get_bot)"
        if budget - len(body) < 0:
            body = f"(method too long to list; to read it use the skill parameter of get_bot: {s['name']})"
        budget -= len(body)
        parts.append(f"/{s['name']}: {s['description'] or '(no description)'}\nMethod:\n{body}")
    if shared:
        parts.append("Skills shared by all Bots: " + " ".join("/" + s["name"] for s in shared))
    rs = routines.list_for(b["id"])
    for label, part in (("Routines", [r for r in rs if not routines.is_event(r)]), ("Events", [r for r in rs if routines.is_event(r)])):
        parts.append(f"{label}: " + ("\n" + "\n".join(
            f"- #{r['id']} {r['name']}({routines.describe(r['trigger'], in_lang='en')}{'' if r['enabled'] else ', paused'}): {r['prompt'][:100]}"
            for r in part) if part else "none"))
    gs = _groups_of(b["id"])
    parts.append("Groups: " + (", ".join(f"\"{c['title']}\"" + (" (coordinator)" if c["lead"] == b["id"] else "") for c in gs) or "none"))
    ts = _running_tasks(b["id"])
    parts.append("Running tasks: " + ("\n" + "\n".join(f"- #{t.id} {t.goal[:80]}" for t in ts) if ts else "none"))
    parts.append(f"Long-term memory: it has noted {len(memories.list_for(b['id'])['own'])} items (only it can see their content)")
    return "\n\n".join(parts)


def view(me: dict, args: dict) -> str:
    """get_bot 工具。"""
    name = str(args.get("name") or "").strip()
    if not name:
        return _overview(me)
    b = bots.by_name(name)
    if not b:
        others = ", ".join(x["name"] for x in bots.list_bots())
        return f"No Bot named {name} (it was not created or has been deleted, even if memory says it exists). Existing: {others}"
    if sk := str(args.get("skill") or "").strip().lstrip("/"):
        s = _own_skills(b["id"]).get(sk) or skills.find(b["id"], sk)
        if not s:
            return f"{b['name']} has no skill /{sk}. Skills it can use: " + (" ".join("/" + x["name"] for x in skills.list_for(b["id"])) or "none")
        whose = "shared by all Bots" if s["bot_id"] is None else "its own"
        return f"Skill /{s['name']} of {b['name']} ({whose}): {s['description'] or '(no description)'}\nMethod:\n{s['body']}"
    return _detail(b, me)
