"""Bộ eval offline: chạy từng kịch bản (scenarios/*.yaml) qua vòng lặp thật của OSAR với mô hình giả theo kịch bản.

Router, Worker, gọi tool, thẻ xác nhận, sandbox check_patch, routine, DB… đều chạy thật; chỉ mô hình là giả
(tests/fakellm.py, đi qua AsyncOpenAI thật bằng httpx.MockTransport). Không gọi mạng thật: socket ra ngoài
127.0.0.1 bị chặn và ghi lại, kịch bản nào chạm mạng thật là FAIL.

Một kịch bản là một file YAML. Các khóa (xem docs/vi/eval.md):
  id, title, area, lang, bots, group, setup, script, input | trigger, actions, expect, xfail, needs
"""
import asyncio
import json
import socket
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import yaml

from conftest import find, settle, until
from fakellm import Call, HttpError, Stall
from osa import (approvals, bots, i18n, local_checks, memories, memory, prices, providers, registry, router, routines,
                 server, skills, vault, watchdog)
from osa.config import CFG

DIR = Path(__file__).parent / "scenarios"
KEYS = {"id", "title", "area", "lang", "bots", "group", "setup", "script", "input", "trigger", "actions", "expect",
        "xfail", "needs", "notes", "safety"}


def load_all() -> list[dict]:
    out = []
    for p in sorted(DIR.glob("*.yaml")):
        s = yaml.safe_load(p.read_text(encoding="utf-8"))
        unknown = set(s) - KEYS
        if unknown:
            raise ValueError(f"{p.name}: unknown keys {sorted(unknown)}")
        if s.get("id") != p.stem:
            raise ValueError(f"{p.name}: id must equal the file name ({s.get('id')!r})")
        for k in ("title", "area", "expect"):
            if k not in s:
                raise ValueError(f"{p.name}: missing {k}")
        out.append(s)
    return out


# ---------- mạng: chỉ được đi loopback ----------
class NetGuard:
    def __init__(self):
        self.blocked: list[str] = []
        self._orig = socket.socket.connect

    def __enter__(self):
        guard = self

        def connect(sock, address):
            host = address[0] if isinstance(address, tuple) else str(address)
            if sock.family == socket.AF_UNIX or host in ("127.0.0.1", "::1", "localhost"):
                return guard._orig(sock, address)
            guard.blocked.append(str(address))
            raise OSError("osa evals: real network is blocked")
        socket.socket.connect = connect
        return self

    def __exit__(self, *exc):
        socket.socket.connect = self._orig


# ---------- máy tính giả ----------
from osa.computer.base import Computer, ExecResult  # noqa: E402


class FakeComputer(Computer):
    """Không có máy thật: mỗi thao tác trình duyệt được ghi vào ops, file nằm trong fs."""
    backend = "docker"

    def __init__(self):
        super().__init__(0)
        self.ops: list[str] = []
        self.fs: dict[str, str] = {}
        self.url = ""

    async def status(self) -> dict:
        return {"state": "running"}

    async def start(self):
        pass

    async def exec(self, cmd: str, timeout: int = 120, stdin: str | None = None) -> ExecResult:
        self.ops.append("exec")
        return ExecResult(0, "", "")

    async def page_shot(self, key: str) -> bytes:
        return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (64).to_bytes(4, "big") * 2 + b"\x08\x02\x00\x00\x00"

    async def write_bytes(self, path: str, data: bytes):
        self.ops.append("write")
        self.fs[path] = data.decode()

    async def read_bytes(self, path: str, limit: int = 1 << 20) -> bytes:
        self.ops.append("read_file")
        return self.fs.get(path, "").encode()[:limit]

    async def _helper_run(self, payload: dict) -> dict:
        op = payload["op"]
        self.ops.append(op)
        if op == "open":
            self.url = payload.get("url", "")
        page = {"window": 1, "browser": "b1", "ok": True, "url": self.url or "about:blank", "title": "Example Domain",
                "text": "Example Domain. This domain is for use in examples."}
        if op == "read":   # same shapes as cdp_helper: read gives text + offset/total, the rest a snapshot
            return page | {"offset": 0, "total": len(page["text"])}
        return page | {"elements": ["[1] link \"More information\""], "scroll": "0%"}


# ---------- chạy một kịch bản ----------
class Run:
    def __init__(self, scn: dict, llm, events, make_bot, mcp_tool, monkeypatch, tmp_path):
        self.s, self.llm, self.events, self.make_bot, self.mcp_tool = scn, llm, events, make_bot, mcp_tool
        self.mp, self.tmp = monkeypatch, tmp_path
        self.bots: dict[str, dict] = {}
        self.group: dict | None = None
        self.mcp_calls: dict[str, list] = {}
        self.router_tools: list[str] = []
        self.computer: FakeComputer | None = None
        self.routine: dict | None = None
        self.watchdog: asyncio.Task | None = None
        self.turns: list[asyncio.Task] = []
        self.listener_port = 0
        self.listener_hits = 0
        self.cleanups: list = []
        self.served: list[str] = []      # model replies served (for the step trace)
        # message ids are reused after a bot (and its chat) is deleted, so a run is told apart by time and bot, not by id
        self.t0 = time.time()
        self.failures: list[str] = []

    # ----- tiện ích -----
    def bot(self, name: str) -> dict:
        return self.bots[name]

    def chat_of(self, who: str) -> int:
        if who == "group":
            return self.group["id"]
        return self.bots[who]["chat_id"]

    def tasks(self) -> list:
        ids = {b["id"] for b in self.bots.values()}
        return [t for _, t in sorted(router.TASKS.items()) if t.bot_id in ids and t.started >= self.t0]

    def pending(self) -> list[dict]:
        return [it for it in approvals.pending.values() if not it["future"].done()
                and any(it["bot_id"] == b["id"] for b in self.bots.values())]

    def cards(self, status: str | None = None) -> list[dict]:
        ids = {b["id"] for b in self.bots.values()}
        return [e for e in self.events.of("approval") if (e.get("bot_id") in ids or e.get("chat_id") in
                {b["chat_id"] for b in self.bots.values()}) and (status is None or e.get("status") == status)]

    def tool_steps(self) -> list[dict]:
        ids = [t.id for t in self.tasks()]
        if not ids:
            return []
        rows = memory.conn.execute(
            f"select task_id, name, status, body from task_steps where kind='tool' and ts >= ? "
            f"and task_id in ({','.join('?' * len(ids))}) order by id", [self.t0, *ids]).fetchall()
        return [{"task_id": r[0], "name": r[1], "status": r[2], "body": r[3] or ""} for r in rows]

    def usage(self) -> dict:
        rows = memory.conn.execute("select cache_hit, cache_miss, output, err from llm_calls where ts >= ?",
                                   (self.t0,)).fetchall()
        hit = sum(r[0] or 0 for r in rows)
        miss = sum(r[1] or 0 for r in rows)
        out = sum(r[2] or 0 for r in rows)
        r = CFG["roles"]["worker"]
        cost = prices.cost(r["provider"], r["model"], hit, miss, out, False) or 0.0
        return {"calls": len(rows), "errors": sum(1 for r in rows if r[3]), "tokens_in": hit + miss, "tokens_out": out,
                "cost_usd": round(float(cost), 6)}

    def llm_text(self) -> str:
        """Everything the model was shown or emitted: message texts, tool results and tool-call arguments (unescaped)."""
        out = []
        for _, _, body in self.llm.requests:
            for m in body["messages"]:
                c = m.get("content")
                if isinstance(c, list):
                    out += [p.get("text", "") for p in c if isinstance(p, dict)]
                elif c:
                    out.append(str(c))
                for tc in m.get("tool_calls") or []:
                    out.append(tc["function"].get("arguments") or "")
        return "\n".join(out)

    # ----- kịch bản → câu trả lời của mô hình -----
    def _resolve(self, v, body):
        if isinstance(v, dict):
            return {k: self._resolve(x, body) for k, x in v.items()}
        if isinstance(v, list):
            return [self._resolve(x, body) for x in v]
        if isinstance(v, str) and "$listener.port" in v:
            v = v.replace("$listener.port", str(self.listener_port))
        if not isinstance(v, str) or not v.startswith("$"):
            return v
        if v.startswith("$tool."):   # field of the JSON in the last tool message the model saw
            last = next(m for m in reversed(body["messages"]) if m["role"] == "tool")
            return json.loads(last["content"])[v[6:]]
        if v.startswith("$bot."):
            return self.bots[v[5:]]["name"]
        if v == "$approval.id":
            p = self.pending()
            return p[0]["id"] if p else -1
        if v.startswith("$file:"):
            return (Path(__file__).parent / "fixtures" / v[6:]).read_text(encoding="utf-8")
        return v

    def reply(self, spec):
        if isinstance(spec, str):
            return spec
        if "say" in spec:
            return spec["say"]
        if "stall" in spec:
            return Stall()
        if "http_error" in spec:
            return HttpError(int(spec["http_error"]), spec.get("body") or {"error": {"message": "fake"}})
        calls = spec.get("calls") or [spec]

        def build(body):
            return [Call(c["call"], self._resolve(c.get("args") or {}, body)) for c in calls]
        return build

    # ----- setup -----
    async def setup(self):
        s = self.s
        if lang := s.get("lang"):
            self.mp.setattr(i18n, "_lang", lang)
        for name in s.get("bots") or ["Solo"]:
            b = self.make_bot(f"{name}{id(self) % 100000}", "")
            self.bots[name] = b
            self.cleanups.append(lambda b=b: (routines.delete_for_bot(b["id"]), memories.delete_for_bot(b["id"]),
                                              bots.delete(b["id"])))
        if s.get("group"):
            ids = [b["id"] for b in self.bots.values()]
            self.group = bots.create_group(ids, lead=ids[0])
        for item in s.get("setup") or []:
            (kind, arg), = item.items()
            await getattr(self, f"setup_{kind}")(arg)
        for who, replies in (s.get("script") or {}).items():
            role, _, name = who.partition(":")
            key = f"{role}:{self.bots[name]['name']}" if name else role
            self.llm.script(key, *[self.reply(r) for r in replies])
        # router tool calls actually executed
        off = registry.Context("eval:observer").on("tool_done", lambda **kw: self.router_tools.append(kw["name"])
                                                    if kw.get("scope") == "router" else None)
        self.cleanups.append(off)

    async def setup_limits(self, arg: dict):
        lim = dict(CFG["limits"])
        for k, v in arg.items():
            lim[k] = memory.tokens_today() + int(v) if k == "daily_token_budget" else v
        self.mp.setitem(CFG, "limits", lim)

    async def setup_no_retry_pause(self, _):
        async def no_wait(attempt):
            pass
        self.mp.setattr(providers, "retry_pause", no_wait)

    async def setup_watchdog(self, _):
        self.watchdog = asyncio.create_task(watchdog.watchdog())
        self.cleanups.append(self.watchdog.cancel)

    async def setup_fixture_repo(self, arg: dict):
        repo = self.tmp / arg["name"]
        repo.mkdir()
        for rel, text in arg["files"].items():
            (repo / rel).write_text(text)
        conf = self.tmp / "local-checks.json"
        conf.write_text(json.dumps({arg["name"]: {"path": str(repo), "files": list(arg["files"]),
                                                  "tests": arg["tests"]}}))
        self.mp.setattr(local_checks, "registry_file", lambda: conf)
        self.mp.setattr(local_checks.memory, "db_path", self.tmp / "osa.db")
        self.repo = repo

    async def setup_mcp_tool(self, arg: dict):
        name = arg["name"]
        self.mcp_calls[name] = []
        fail_first = int(arg.get("fail_first", 0))
        sleep = float(arg.get("sleep", 0))
        secret = arg.get("secret")
        returns = arg.get("returns", "ok")

        async def fn(**kw):
            self.mcp_calls[name].append(kw)
            if sleep:
                await asyncio.sleep(sleep)
            if len(self.mcp_calls[name]) <= fail_first:
                raise RuntimeError(arg.get("error", "503 upstream unavailable"))
            if secret:   # like an MCP server whose env has {vault:NAME}: resolved only when it runs
                missing: list = []
                from osa import mcp_hub
                token = mcp_hub._resolve(secret, missing)
                if missing or not token:
                    return "unauthorized"
                return returns
            return returns.format(**kw) if kw else returns
        props = {p: {"type": "string"} for p in arg.get("params", [])}
        schema = {"type": "function", "function": {"name": name, "description": arg.get("description", name),
                                                   "parameters": {"type": "object", "properties": props}}}
        self.mcp_tool(name, fn, schema, confirm=bool(arg.get("confirm")))

    async def setup_host_listener(self, _):
        """A TCP port open on the host's 127.0.0.1, so a sandbox escape to host loopback would actually connect."""
        async def accept(reader, writer):
            self.listener_hits += 1
            writer.close()
        srv = await asyncio.start_server(accept, "127.0.0.1", 0)
        self.listener_port = srv.sockets[0].getsockname()[1]
        self.cleanups.append(srv.close)

    async def setup_vault(self, arg: dict):
        for k, v in arg.items():
            vault.put(k, v)
            self.cleanups.append(lambda k=k: vault.delete(k))

    async def setup_computer(self, _):
        from osa import computer
        self.computer = FakeComputer()
        self.mp.setitem(CFG, "computer", {**(CFG.get("computer") or {}), "enabled": True})
        self.mp.setitem(computer._computers, computer.SHARED, self.computer)
        self.mp.setattr(computer, "backend_name", lambda: FakeComputer.backend)

    async def setup_skill(self, arg: dict):
        b = self.bots[arg.get("bot") or next(iter(self.bots))]
        skills.save(b["id"], arg["name"], arg["body"], arg.get("description", ""), "manual")

    async def setup_routine(self, arg: dict):
        b = self.bots[arg.get("bot") or next(iter(self.bots))]
        self.routine = routines.save(b["id"], {"name": f"{arg['name']}{b['id']}", "prompt": arg["prompt"],
                                               "trigger": arg["trigger"]})

    # ----- chạy -----
    async def drive(self):
        s = self.s
        if inp := s.get("input"):
            who = inp.get("to") or next(iter(self.bots))
            chat = self.group if inp.get("in") == "group" else bots.chat(self.chat_of(who))
            self.turns.append(asyncio.create_task(server.safe_handle(chat, inp["text"])))
            await asyncio.sleep(0)
        if trig := s.get("trigger"):
            await getattr(self, f"trigger_{trig['kind']}")(trig)
        for act in s.get("actions") or []:
            (kind, arg), = act.items()
            await getattr(self, f"act_{kind}")(arg)
        await self.idle()

    async def idle(self, timeout: float = 15):
        if self.turns:   # the user's turn has to finish first, or there may be no task yet to wait for
            await asyncio.wait_for(asyncio.gather(*self.turns), timeout)
        await until(lambda: all(t.status != "running" for t in self.tasks()) and
                    (not self.routine or self.routine["id"] not in routines.RUNNING), timeout=timeout, what="tasks finished")
        if self.watchdog:   # its loop never ends; settle() would wait for it until the timeout
            self.watchdog.cancel()
        await settle(timeout)

    async def trigger_schedule(self, trig):
        r = routines.get(self.routine["id"])
        due = r["next_run"]
        # tick() looks at every routine in the DB; other tests' routines must not fire (and eat this script) here
        self.mp.setattr(routines, "list_for", lambda bot_id=None: [routines.get(r["id"])])
        await routines.tick(due - 60)
        if routines.runs(r["id"]):
            self.failures.append("routine fired before its time")
        await routines.tick(due + 1)
        await until(lambda: routines.runs(r["id"]), what="routine run recorded")

    async def trigger_webhook(self, trig):
        r = routines.get(self.routine["id"])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://127.0.0.1") as c:
            res = await c.post(f"/hooks/{r['trigger']['key']}", json=trig.get("payload") or {})
        if res.status_code != 200 or not res.json().get("accepted"):
            self.failures.append(f"webhook not accepted: {res.status_code} {res.text[:200]}")
        await until(lambda: routines.runs(r["id"]), what="event run recorded")

    async def act_wait(self, what):
        if what == "approval":
            await until(self.pending, what="approval card")
        elif what == "task":
            await until(lambda: any(t.status == "running" for t in self.tasks()), what="running task")
        elif what == "tool":
            await until(lambda: any(self.mcp_calls.values()), what="tool call started")
        elif what == "idle":
            await self.idle()
        else:
            raise ValueError(f"unknown wait {what!r}")

    async def act_approve(self, arg):
        await self._resolve_card(True, arg or {})

    async def act_deny(self, arg):
        await self._resolve_card(False, arg or {})

    async def _resolve_card(self, ok: bool, arg: dict):
        p = await until(self.pending, what="approval card")
        approvals.resolve(p[0]["id"], ok, arg.get("note", ""), scope=arg.get("scope"))

    async def act_cancel(self, arg):
        t = await until(lambda: [t for t in self.tasks() if t.status == "running"], what="running task")
        router.cancel(t[0].id, i18n.t("用户要求取消"))

    async def act_say(self, arg):
        """Người dùng nói thêm một câu (không đợi task đang chờ thẻ xác nhận)."""
        who = arg.get("to") or next(iter(self.bots))
        await server.safe_handle(bots.chat(self.chat_of(who)), arg["text"])

    async def act_wait_llm(self, who):
        """Đợi tới khi Router của Bot này được gọi, rồi cho lượt đó chạy xong."""
        name = self.bots[who]["name"]
        await until(lambda: self.llm.bodies("router", name), what=f"{who} router turn")
        rt = router.runtime(self.bots[who]["id"])
        await asyncio.sleep(0.05)
        async with rt.lock:
            pass

    async def act_cleanup_cards(self, _):
        for it in self.pending():
            approvals.resolve(it["id"], False, "eval cleanup")

    # ----- chấm -----
    def check(self, net: NetGuard) -> dict:
        e = self.s["expect"]
        fail = self.failures
        tasks = self.tasks()
        steps = self.tool_steps()
        executed = [x["name"] for x in steps if x["status"] == "done"] + self.router_tools
        rejected = [x["name"] for x in steps if x["status"] == "rejected"]

        def want(cond, msg):
            if not cond:
                fail.append(msg)

        if "tasks" in e:
            want(len(tasks) == e["tasks"], f"tasks: want {e['tasks']}, got {[(t.id, t.bot_id, t.goal[:40]) for t in tasks]}")
        if "task_status" in e:
            got = [t.status for t in tasks]
            want(got and all(x == e["task_status"] for x in got),
                 f"task_status: want {e['task_status']}, got {[(t.status, (t.result or '')[:160]) for t in tasks]}")
        for text in e.get("result_contains") or []:
            want(any(text in (t.result or "") for t in tasks), f"no task result contains {text!r}")
        for name in e.get("executed") or []:
            want(name in executed, f"tool {name} not executed (steps: {[(x['name'], x['status'], x['body'][:120]) for x in steps]})")
        for name in e.get("not_executed") or []:
            want(name not in executed, f"tool {name} executed but must not be")
        for name in e.get("rejected") or []:
            want(name in rejected, f"tool {name} not rejected (rejected: {rejected})")
        for name, n in (e.get("mcp_calls") or {}).items():
            want(len(self.mcp_calls.get(name, [])) == n, f"mcp {name}: want {n} calls, got {len(self.mcp_calls.get(name, []))}")
        for name, text in (e.get("tool_output") or {}).items():
            want(any(x["name"] == name and text in x["body"] for x in steps), f"no {name} output contains {text!r}")
        if "approvals" in e:
            a = e["approvals"]
            raised = self.cards("pending")
            if "raised" in a:
                want(len(raised) == a["raised"], f"approval cards: want {a['raised']}, got {len(raised)}")
            for st in a.get("statuses") or []:
                want(self.cards(st), f"no approval card ended {st!r}")
            if "pending_at_end" in a:
                want(len(self.pending()) == a["pending_at_end"], f"pending cards at end: {len(self.pending())}")
        for m in e.get("messages") or []:
            m = dict(m)
            chat = self.chat_of(m.pop("chat"))
            if "ui_text" in m:
                m["text"] = i18n.t(m.pop("ui_text"))
            if "bot" in m:
                m["bot_id"] = self.bots[m.pop("bot")]["id"]
            want(find(chat, **m), f"no message {m} in chat")
        for m in e.get("no_messages") or []:
            m = dict(m)
            chat = self.chat_of(m.pop("chat"))
            want(not find(chat, **m), f"unexpected message {m}")
        if "max_steps" in e:
            n = sum(t.steps for t in tasks)
            want(n <= e["max_steps"], f"worker steps {n} > {e['max_steps']}")
        seen = self.llm_text()
        for text in e.get("not_in_llm") or []:
            want(text not in seen, f"{text!r} reached the model")
        for text in e.get("not_in_db") or []:
            hit = memory.conn.execute("select count(*) from messages where ts >= ? and (content like ? or meta like ?)",
                                      (self.t0, f"%{text}%", f"%{text}%")).fetchone()[0]
            hit += memory.conn.execute("select count(*) from task_steps where ts >= ? and (body like ? or detail like ? or title like ?)",
                                       (self.t0, f"%{text}%", f"%{text}%", f"%{text}%")).fetchone()[0]
            want(not hit, f"{text!r} stored in the DB ({hit} rows)")
        for text in e.get("in_llm") or []:
            want(text in seen, f"{text!r} never reached the model")
        if mem := e.get("memory"):
            b = self.bots[mem.get("bot") or next(iter(self.bots))]
            listed = memories.list_for(b["id"])
            items = [x for v in listed.values() if isinstance(v, list) for x in v]
            want(any(mem["contains"] in x.get("text", "") for x in items), f"memory {mem['contains']!r} not saved")
        if "routine_runs" in e:
            got = [r["status"] for r in routines.runs(self.routine["id"])]
            want(sorted(got) == sorted(e["routine_runs"]), f"routine runs: want {e['routine_runs']}, got {got}")
        if ops := e.get("computer_ops"):
            have = self.computer.ops if self.computer else []
            want(all(o in have for o in ops), f"computer ops: want {ops}, got {have}")
        for path, text in (e.get("computer_files") or {}).items():
            have = (self.computer.fs if self.computer else {}).get(path)
            want(have is not None and text in have, f"computer file {path}: {have!r}")
        if "lang_flag" in e:
            got = [bool(t.lang_flag) for t in tasks]
            want(got and all(x == e["lang_flag"] for x in got), f"lang_flag: want {e['lang_flag']}, got {got}")
        if "listener_hits" in e:
            want(self.listener_hits == e["listener_hits"], f"host listener hits: want {e['listener_hits']}, got {self.listener_hits}")
        u = self.usage()
        if "stream_errors" in e:
            want(u["errors"] == e["stream_errors"], f"failed model calls: want {e['stream_errors']}, got {u['errors']}")
        for name in e.get("tool_frames") or []:
            frames = [x for x in self.events.of("tool") if x.get("name") == name]
            states = [f.get("state") for f in frames]
            want("run" in states and "ok" in states,
                 f"no run/ok frame for tool {name!r} (frames: {[(f.get('name'), f.get('state')) for f in frames]})")
        if e.get("turn_usage"):
            chats = [b["chat_id"] for b in self.bots.values()] + ([self.group["id"]] if self.group else [])
            rows = memory.conn.execute(
                f"select meta from messages where role='assistant' and ts >= ? "
                f"and chat_id in ({','.join('?' * len(chats))}) order by id desc limit 10",
                [self.t0, *chats]).fetchall()
            usage = [(json.loads(r[0] or "{}") or {}).get("usage") for r in rows]
            want(any(u and (u.get("out") or 0) > 0 for u in usage),
                 f"no reply carries this turn's usage (got {usage})")
        if "max_llm_calls" in e:
            want(len(self.llm.requests) <= e["max_llm_calls"], f"model calls {len(self.llm.requests)} > {e['max_llm_calls']}")
        want(not net.blocked, f"tried real network: {net.blocked}")
        return {"steps": sum(t.steps for t in tasks), "llm_calls": len(self.llm.requests), "tasks": len(tasks),
                "tools": executed, **u}

    async def close(self):
        for fn in reversed(self.cleanups):
            try:
                fn()
            except Exception:
                pass
        for it in self.pending():
            approvals.resolve(it["id"], False, "eval cleanup")
        for t in self.tasks():
            if t.status == "running" and t.handle:
                t.handle.cancel()
        await settle()


async def run(scn: dict, **fx) -> tuple[list[str], dict]:
    """Chạy một kịch bản; trả về (danh sách lỗi, số đo)."""
    r = Run(scn, **fx)
    t0 = time.monotonic()
    with NetGuard() as net:
        try:
            await r.setup()
            await r.drive()
            metrics = r.check(net)
        finally:
            await r.close()
    metrics["latency_ms"] = round((time.monotonic() - t0) * 1000)
    return r.failures, metrics
