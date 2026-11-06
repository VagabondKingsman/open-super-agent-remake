"""定时任务（Routines），取代原来的 triggers。

每个 Bot 自己的定时任务，三种触发方式：
- daily：每天（或每周几）的固定时间，times=["09:00"]，days=[1..7]（周一=1，留空表示每天）
- every：每隔 minutes 分钟
- webhook：POST /hooks/<名字>；事件先过关键词过滤（include / exclude），再过 LLM 过滤（llm_filter）
触发后直接派一个后台任务给这个 Bot（确认卡片会过期），结果出现在 Bot 的对话里。
每个定时任务保留最近 20 次运行记录；上一次还没跑完时，这一次跳过。
"""

from .i18n import s as _s
import asyncio
import json
import re
import time
from . import i18n
from .config import CFG, call_kwargs, client_for
from .memory import conn
from . import memory, skills

conn.execute("""create table if not exists routines(
  id integer primary key, bot_id integer, name text, prompt text default '', skill text default '',
  trigger text, enabled integer default 1, next_run real, created real, updated real)""")
conn.execute("""create table if not exists routine_runs(
  id integer primary key, routine_id integer, ts real, source text, status text, task_id integer,
  detail text default '', finished real)""")
conn.commit()

MAX_PER_BOT = 50
KEEP_RUNS = 20
KINDS = ("daily", "every", "webhook")
FIRING: set[int] = set()          # Reserve a routine before awaiting webhook filters.
RUNNING: dict[int, int] = {}      # routine_id -> 正在跑的 run id
notify = None                     # 由 server 设置


def _row(r) -> dict:
    i, bot_id, name, prompt, skill, trig, enabled, next_run, created, updated = r
    trigger = json.loads(trig or "{}")
    if trigger.get("llm_filter"):
        trigger["llm_filter"] = i18n.legacy_routine_default(trigger["llm_filter"])
    return {"id": i, "bot_id": bot_id, "name": name, "prompt": i18n.legacy_routine_default(prompt or ""), "skill": skill or "",
            "trigger": trigger, "enabled": bool(enabled), "next_run": next_run,
            "created": created, "updated": updated, "running": i in RUNNING,
            "last_run": last_run(i)}

_COLS = "id, bot_id, name, prompt, skill, trigger, enabled, next_run, created, updated"


def list_for(bot_id: int | None = None) -> list[dict]:
    q, a = (f"select {_COLS} from routines where bot_id=? order by id", (bot_id,)) if bot_id is not None \
        else (f"select {_COLS} from routines order by id", ())
    return [_row(r) for r in conn.execute(q, a)]


def get(rid: int) -> dict | None:
    r = conn.execute(f"select {_COLS} from routines where id=?", (rid,)).fetchone()
    return _row(r) if r else None


def by_hook(name: str) -> dict | None:
    return next((r for r in list_for() if r["name"] == name and r["trigger"].get("kind") == "webhook"), None)


def last_run(rid: int) -> dict | None:
    r = conn.execute("select id, ts, source, status, task_id, detail, finished from routine_runs "
                     "where routine_id=? order by id desc limit 1", (rid,)).fetchone()
    return _run(r) if r else None


def _run(r) -> dict:
    i, ts, source, status, task_id, detail, finished = r
    return {"id": i, "ts": ts, "source": source, "status": status, "task_id": task_id,
            "detail": detail, "finished": finished}


def runs(rid: int) -> list[dict]:
    return [_run(r) for r in conn.execute("select id, ts, source, status, task_id, detail, finished "
                                          "from routine_runs where routine_id=? order by id desc limit ?", (rid, KEEP_RUNS))]


# ---------- 时间计算 ----------
def _clean_trigger(t: dict) -> dict:
    if not isinstance(t, dict) or t.get("kind") not in KINDS:
        raise ValueError(i18n.s("routine_trigger_invalid"))
    kind = t["kind"]
    if kind == "daily":
        raw_times = t.get("times") or []
        if not isinstance(raw_times, list) or any(not isinstance(x, str) for x in raw_times):
            raise ValueError(i18n.s("routine_time_format"))
        times = [x.strip() for x in raw_times if x.strip()]
        if not times or not all(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", x) for x in times):
            raise ValueError(i18n.s("routine_time_format"))
        raw_days = t.get("days") or []
        if not isinstance(raw_days, list):
            raise ValueError(i18n.s("routine_days_invalid"))
        try:
            if any(isinstance(d, bool) or str(d) not in {str(i) for i in range(1, 8)} for d in raw_days):
                raise ValueError
            days = sorted({int(d) for d in raw_days})
        except (TypeError, ValueError):
            raise ValueError(i18n.s("routine_days_invalid")) from None
        return {"kind": kind, "times": sorted(set(times)), "days": days}
    if kind == "every":
        try:
            value = t.get("minutes") or 0
            if isinstance(value, bool) or isinstance(value, float) and not value.is_integer():
                raise ValueError
            m = int(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(i18n.s("routine_every_min")) from None
        if m < 5:
            raise ValueError(i18n.s("routine_every_min"))
        return {"kind": kind, "minutes": m}
    def words(k):
        value = t.get(k) or []
        if not isinstance(value, list) or any(not isinstance(w, str) for w in value):
            raise ValueError(i18n.s("routine_keywords_invalid"))
        return [w.strip() for w in value if w.strip()]
    rule = t.get("llm_filter") or ""
    if not isinstance(rule, str):
        raise ValueError(i18n.s("routine_filter_invalid"))
    return {"kind": kind, "include": words("include"), "exclude": words("exclude"), "llm_filter": rule.strip()}


def next_after(trig: dict, now: float) -> float | None:
    if trig["kind"] == "every":
        return now + trig["minutes"] * 60
    if trig["kind"] != "daily":
        return None
    base = time.localtime(now)
    for add in range(8):
        day = time.mktime((base.tm_year, base.tm_mon, base.tm_mday + add, 0, 0, 0, 0, 0, -1))
        if trig["days"] and time.localtime(day).tm_wday + 1 not in trig["days"]:
            continue
        for hm in trig["times"]:
            h, m = map(int, hm.split(":"))
            ts = time.mktime((base.tm_year, base.tm_mon, base.tm_mday + add, h, m, 0, 0, 0, -1))
            if ts > now:
                return ts
    return None


def describe(trig: dict) -> str:
    join = i18n.s("list_join")
    if trig["kind"] == "every":
        m = trig["minutes"]
        if m % 60 == 0:
            return i18n.s("routine_every_hours", n=m // 60)
        return i18n.s("routine_every_minutes", n=m)
    if trig["kind"] == "daily":
        times = join.join(trig["times"])
        if not trig["days"] or len(trig["days"]) == 7:
            return i18n.s("routine_daily", times=times)
        days = join.join(i18n.s(f"weekday_{d}") for d in trig["days"])
        return i18n.s("routine_weekly", days=days, times=times)
    return i18n.s("routine_webhook")


# ---------- 增删改 ----------
def save(bot_id: int, data: dict, rid: int | None = None) -> dict:
    old = get(rid) if rid else None
    if rid and not old:
        raise ValueError(i18n.s("routine_missing"))
    cur = old or {"name": "", "prompt": "", "skill": "", "trigger": {}, "enabled": True}
    name = (data.get("name", cur["name"]) or "").strip()[:40]
    prompt = (data.get("prompt", cur["prompt"]) or "").strip()[:4000]
    skill = (data.get("skill", cur["skill"]) or "").strip().lstrip("/")
    trig = _clean_trigger(data.get("trigger") or cur["trigger"])
    enabled = bool(data.get("enabled", cur["enabled"]))
    if not name:
        raise ValueError(i18n.s("routine_name_empty"))
    if not prompt and not skill:
        raise ValueError(i18n.s("routine_need_prompt"))
    if skill and not skills.find(bot_id, skill):
        raise ValueError(i18n.s("routine_no_skill", skill=skill))
    if trig["kind"] == "webhook":
        if not re.fullmatch(r"[\w-]{1,40}", name):
            raise ValueError(i18n.s("routine_webhook_name"))
        other = by_hook(name)
        if other and other["id"] != rid:
            raise ValueError(i18n.s("routine_webhook_dup", name=name))
    now = time.time()
    nxt = next_after(trig, now)
    if not rid:
        if conn.execute("select count(*) from routines where bot_id=?", (bot_id,)).fetchone()[0] >= MAX_PER_BOT:
            raise ValueError(i18n.s("routine_max", n=MAX_PER_BOT))
        rid = conn.execute("insert into routines(bot_id, name, prompt, skill, trigger, enabled, next_run, created, updated) "
                           "values(?,?,?,?,?,?,?,?,?)", (bot_id, name, prompt, skill, json.dumps(trig, ensure_ascii=False),
                                                       int(enabled), nxt, now, now)).lastrowid
    else:
        keep_next = old["trigger"] == trig and old["next_run"] and old["next_run"] > now
        conn.execute("update routines set name=?, prompt=?, skill=?, trigger=?, enabled=?, next_run=?, updated=? where id=?",
                     (name, prompt, skill, json.dumps(trig, ensure_ascii=False), int(enabled),
                      old["next_run"] if keep_next else nxt, now, rid))
    conn.commit()
    return get(rid)


def set_enabled(rid: int, on: bool) -> dict:
    r = get(rid)
    nxt = next_after(r["trigger"], time.time()) if on else r["next_run"]
    conn.execute("update routines set enabled=?, next_run=? where id=?", (int(on), nxt, rid))
    conn.commit()
    return get(rid)


def delete(rid: int):
    conn.execute("delete from routine_runs where routine_id=?", (rid,))
    conn.execute("delete from routines where id=?", (rid,))
    conn.commit()


def delete_for_bot(bot_id: int):
    for r in list_for(bot_id):
        delete(r["id"])


# ---------- 运行 ----------
def _record(rid: int, source: str, status: str, detail: str = "", task_id: int | None = None) -> int:
    now = time.time()
    run_id = conn.execute("insert into routine_runs(routine_id, ts, source, status, task_id, detail, finished) "
                          "values(?,?,?,?,?,?,?)", (rid, now, source, status, task_id, detail[:300],
                                                    None if status == "running" else now)).lastrowid
    conn.execute("""delete from routine_runs where routine_id=? and id not in
        (select id from routine_runs where routine_id=? order by id desc limit ?)""", (rid, rid, KEEP_RUNS))
    conn.commit()
    return run_id


def _finish(run_id: int, status: str, detail: str):
    conn.execute("update routine_runs set status=?, detail=?, finished=? where id=?",
                 (status, detail[:300], time.time(), run_id))
    conn.commit()


async def _changed(r: dict):
    if notify:
        await notify({"type": "routines_changed", "bot_id": r["bot_id"]})


def _keyword_filter(trig: dict, text: str) -> str | None:
    low = text.lower()
    if any(w.lower() in low for w in trig.get("exclude", [])):
        return _s('audit_7afde3ad9f')
    inc = trig.get("include", [])
    if inc and not any(w.lower() in low for w in inc):
        return _s('audit_0da91c2898')
    return None


async def _llm_filter(rule: str, text: str) -> tuple[bool, str]:
    client, model = client_for("filter")
    resp = await client.chat.completions.create(model=model, messages=[
        {"role": "system", "content": _s('audit_f986d84969')},
        {"role": "user", "content": _s('audit_7124ecabc7', v0=rule, v1=text[:6000])}],
        response_format={"type": "json_object"}, **call_kwargs("filter"))
    memory.record_usage("filter", model, resp.usage)
    try:
        d = json.loads(resp.choices[0].message.content)
        return bool(d.get("handle")), d.get("reason", "")
    except Exception:
        return True, _s('audit_13ad72fc91')


def goal_for(r: dict, event: str = "") -> str:
    parts = [i18n.s("routine_run_intro", name=r["name"], when=describe(r["trigger"]))]
    if r["skill"] and (s := skills.find(r["bot_id"], r["skill"])):
        parts.append(i18n.s("routine_run_skill", name=s["name"], body=s["body"]))
    if r["prompt"]:
        parts.append(i18n.s("routine_run_prompt", prompt=r["prompt"]))
    if event:
        parts.append(i18n.s("routine_run_event", event=event))
    return "\n\n".join(parts)


async def fire(r: dict, source: str, event: str = "") -> dict:
    """Reserve before the first await so simultaneous webhook filters cannot dispatch twice."""
    rid = r["id"]
    if rid in FIRING:
        reason = i18n.s("routine_skip_running")
        _record(rid, source, "skipped", reason)
        await _changed(r)
        return {"accepted": False, "reason": reason}
    FIRING.add(rid)
    try:
        return await _fire(r, source, event)
    finally:
        FIRING.discard(rid)


async def _fire(r: dict, source: str, event: str = "") -> dict:
    """运行一次。source：schedule / webhook / test。返回是否受理。"""
    from . import bots, router
    rid = r["id"]
    if rid in RUNNING:
        _record(rid, source, "skipped", i18n.s("routine_skip_running"))
        await _changed(r)
        return {"accepted": False, "reason": i18n.s("routine_skip_running")}
    if r["trigger"].get("kind") == "webhook" and source == "webhook":
        if reason := _keyword_filter(r["trigger"], event):
            _record(rid, source, "filtered", reason)
            await _changed(r)
            return {"accepted": False, "stage": "rule", "reason": reason}
        if rule := r["trigger"].get("llm_filter"):
            ok, reason = await _llm_filter(rule, event)
            if not ok:
                _record(rid, source, "filtered", i18n.s("routine_llm_filter", reason=reason))
                await _changed(r)
                return {"accepted": False, "stage": "llm", "reason": reason}
    if not bots.get(r["bot_id"]):
        return {"accepted": False, "reason": i18n.s("routine_bot_missing")}
    run_id = _record(rid, source, "running")
    RUNNING[rid] = run_id

    async def done(task):
        RUNNING.pop(rid, None)
        _finish(run_id, task.status, task.result[:300])
        await _changed(r)

    try:
        rt = router.runtime(r["bot_id"])
        task = await rt.dispatch(goal_for(r, event), background=True, on_done=done,
                                 label=i18n.s("routine_task_label", name=r["name"]))
    except Exception as e:
        RUNNING.pop(rid, None)
        _finish(run_id, "failed", str(e))
        await _changed(r)
        return {"accepted": False, "reason": str(e)}
    conn.execute("update routine_runs set task_id=? where id=?", (task.id, run_id))
    conn.commit()
    await _changed(r)
    return {"accepted": True, "task_id": task.id}


async def scheduler():
    """每 20 秒看一次哪些定时任务到点了。错过的（比如服务停着）只补跑一次。"""
    while True:
        await asyncio.sleep(20)
        now = time.time()
        for r in list_for():
            if not r["enabled"] or not r["next_run"] or r["next_run"] > now:
                continue
            conn.execute("update routines set next_run=? where id=?", (next_after(r["trigger"], now), r["id"]))
            conn.commit()
            try:
                await fire(r, "schedule")
            except Exception as e:
                _record(r["id"], "schedule", "failed", str(e))


def import_legacy(bot_id: int):
    """把 config.yaml 里旧的 triggers 导入成主 Bot 的定时任务，只做一次。"""
    if conn.execute("select 1 from settings where key='triggers_imported'").fetchone():
        return
    for t in CFG.get("triggers") or []:
        try:
            if t.get("type") == "webhook":
                trig = {"kind": "webhook", "include": t.get("include", []), "exclude": t.get("exclude", []),
                        "llm_filter": t.get("llm_filter", "")}
            elif t.get("every"):
                trig = {"kind": "every", "minutes": max(5, int(t["every"]) // 60)}
            else:
                trig = {"kind": "daily", "times": t.get("at") or ["09:00"]}
            prompt = (t.get("prompt") or t["name"]).replace("{event}", "").strip()
            save(bot_id, {"name": t["name"], "prompt": prompt, "trigger": trig, "enabled": t.get("enabled", True)})
        except Exception:
            pass
    conn.execute("insert or replace into settings(key, value) values('triggers_imported', '1')")
    conn.commit()
