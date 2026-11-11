"""Instabox 后端：所有 Bot 共用一台 Firecracker 微虚拟机（agent-browser 模板，自带 Xfce 桌面和 Chromium）。

接口依据 https://api.instabox.sh/v1/openapi.json 和 Instabox 文档编写。
需要 Instabox 的 API key（scope 至少 machines:write）：界面里填的（加密存在保险库里）优先，没填用环境变量 INSTABOX_API_KEY。
"""
import asyncio
import os
import uuid
import httpx
import websockets
from .. import i18n, vault
from ..memory import conn
from .base import Computer, ComputerError, ExecResult, check_enabled

API = os.environ.get("INSTABOX_API_URL", "https://api.instabox.sh")
STATE = {"running": "running", "suspended": "paused", "stopped": "stopped", "creating": "starting",
         "starting": "starting", "resuming": "starting", "suspending": "paused", "stopping": "stopped",
         "error": "error", "deleting": "error", "deleted": "none"}


KEY = "INSTABOX_API_KEY"   # 保险库里和环境变量里都叫这个


def key_source() -> str:
    """API key 从哪来：saved（界面里填的）/ env（环境变量）/ 空（没有）。"""
    if vault.get(KEY):
        return "saved"
    return "env" if os.environ.get(KEY) else ""


def _headers(extra: dict | None = None) -> dict:
    key = vault.get(KEY) or os.environ.get(KEY)
    if not key:
        raise ComputerError(i18n.t("还没填 Instabox 的 API Key"))
    return {"X-API-Key": key, **(extra or {})}


async def save_key(key: str):
    """界面里填 API key：先试一下能不能列出机器，能用才存。换了 key 可能是另一个账号，忘掉之前记下的机器；
    那个账号里有以前给这里建的机器就直接接着用。key 为空：删掉界面里填的（回到环境变量）。"""
    key = key.strip()
    ours = None
    if key:
        try:
            async with httpx.AsyncClient(base_url=API, timeout=15) as h:
                r = await h.get("/v1/machines", headers={"X-API-Key": key})
        except httpx.HTTPError as e:
            raise ComputerError(i18n.t("连不上 Instabox：{error}", error=str(e) or type(e).__name__)) from None
        if r.status_code in (401, 403):
            raise ComputerError(i18n.t("Instabox 不认这个 API Key（{code}），检查一下有没有复制完整、权限里有没有 machines:write", code=r.status_code))
        if r.status_code >= 400:
            raise ComputerError(f"Instabox {r.status_code} {r.text[:200]}")
        try:
            ours = next((m["id"] for m in r.json().get("machines", []) if m.get("state") not in ("deleting", "deleted")
                         and (m.get("metadata") or {}).get("app") == "open-super-agent"), None)
        except (ValueError, AttributeError, KeyError):
            pass
    if key == (vault.get(KEY) or ""):
        return
    if key:
        vault.put(KEY, key)
    else:
        vault.delete(KEY)
    conn.execute("delete from computers where backend='instabox'")
    if ours:
        conn.execute("insert or replace into computers(bot_id, backend, ref) values(0, 'instabox', ?)", (ours,))
    conn.commit()


class InstaboxComputer(Computer):
    backend = "instabox"

    def __init__(self, bot_id: int, template: str = "agent-browser", idle_seconds: int = 900,
                 fixed_machine: str | None = None):
        super().__init__(bot_id)
        self.fixed_machine = fixed_machine   # config 里指定已有机器（免费版只能有一台）
        self.template = template
        self.idle_seconds = idle_seconds
        self._starting = asyncio.Lock()
        self._switch = asyncio.Lock()        # 换机器一次只做一次（几个动作同时发现机器没了）
        self.http = httpx.AsyncClient(base_url=API, timeout=httpx.Timeout(60, read=660))

    # 机器 id 存在数据库里，以后一直用同一台机器
    @property
    def machine_id(self) -> str | None:
        if self.fixed_machine:
            return self.fixed_machine
        r = conn.execute("select ref from computers where bot_id=? and backend='instabox'", (self.bot_id,)).fetchone()
        return r[0] if r else None

    def _save_id(self, mid: str):
        conn.execute("insert or replace into computers(bot_id, backend, ref) values(?, 'instabox', ?)", (self.bot_id, mid))
        conn.commit()

    def _forget(self):
        conn.execute("delete from computers where bot_id=? and backend='instabox'", (self.bot_id,))
        conn.commit()

    async def _get_machine(self, mid: str) -> dict | None:
        """那台机器的样子；已经没了（账号那边删掉、回收）返回 None。"""
        try:
            return await self._req("GET", f"/v1/machines/{mid}")
        except ComputerError as e:
            if "machine_not_found" in str(e) or " 404 " in str(e):
                return None
            raise

    async def _set_role(self, mid: str, role: str):
        """在机器的 metadata 里记下它是哪一台（primary：现在用的；backup：备着）。Instabox 不认这个接口也不影响用。"""
        try:
            await self._req("PATCH", f"/v1/machines/{mid}", json={"metadata": {"app": "open-super-agent", "role": role}})
        except Exception:
            pass

    async def failover(self, why: str = "") -> str:
        """现在这台机器没了：换一台自己的机器用，一台都没有就返回 ""（start 里新建）。
        有现成的机器时只多两次请求（列一下、记住），所以切换在几秒内完成。"""
        if self.fixed_machine:
            raise ComputerError(i18n.t("config.yaml 指定的电脑（{mid}）不在了，换不了：清空 computer.instabox_machine 或改成另一台", mid=self.fixed_machine))
        async with self._switch:
            cur = self.machine_id
            if cur and await self._get_machine(cur) is not None:
                return cur          # 别人已经换好了
            alive = [m for m in await self.list_machines()   # state 是界面上的说法（见 STATE）：paused 是挂起的
                     if m["ours"] and m["id"] != cur and m["state"] in ("running", "paused", "stopped")]
            if not alive:
                self._forget()
                return ""
            order = {"running": 0, "paused": 1, "stopped": 2}   # 已经开着的先用，挂起的次之
            pick = sorted(alive, key=lambda m: order[m["state"]])[0]["id"]
            self._save_id(pick)
            await self._set_role(pick, "primary")
            return pick

    async def list_machines(self) -> list[dict]:
        """账号下所有机器，给界面选“用已有的电脑”。"""
        out, cursor = [], None
        for _ in range(10):
            d = await self._req("GET", "/v1/machines" + (f"?cursor={cursor}" if cursor else ""))
            out += d.get("machines", [])
            if not (cursor := d.get("nextCursor")):
                break
        cur = self.machine_id
        return [{"id": m["id"], "name": m.get("name") or "", "state": STATE.get(m.get("state"), "error"),
                 "template": m.get("template") or "", "created": m.get("createdAt"),
                 "role": (m.get("metadata") or {}).get("role") or "",
                 "ours": (m.get("metadata") or {}).get("app") == "open-super-agent", "current": m["id"] == cur}
                for m in out if m.get("state") not in ("deleting", "deleted")]

    def use_machine(self, mid: str):
        if self.fixed_machine:
            raise ComputerError(i18n.t("config.yaml 的 computer.instabox_machine 已经指定了机器，要换请先清空那一项"))
        self._save_id(mid)

    async def _req(self, method: str, path: str, json: dict | None = None, idem: bool = False, timeout: float | None = None):
        h = _headers({"Idempotency-Key": str(uuid.uuid4())} if idem else None)
        r = await self.http.request(method, path, json=json, headers=h, timeout=timeout or httpx.USE_CLIENT_DEFAULT)
        if r.status_code >= 400:
            try:
                e = r.json().get("error", {})
                msg = f"{e.get('code')}: {e.get('message')}"
            except Exception:
                msg = r.text[:300]
            raise ComputerError(f"Instabox {r.status_code} {msg}")
        return r.json() if r.content else {}

    async def _wait_op(self, op: dict) -> dict:
        while op.get("state") not in ("succeeded", "failed"):
            op = await self._req("GET", f"/v1/operations/{op['id']}?wait=25s", timeout=40)
        if op["state"] == "failed":
            raise ComputerError(i18n.t("Instabox 操作失败：{error}", error=op.get("error")))
        return op

    async def status(self) -> dict:
        mid = self.machine_id
        if not mid:
            return {"state": "none", "detail": i18n.t("还没有创建")}
        try:
            m = await self._get_machine(mid)
        except ComputerError as e:
            return {"state": "error", "detail": str(e)}
        if m is None:
            return {"state": "gone", "detail": i18n.t("那台机器已经没了"), "machine_id": mid}
        return {"state": STATE.get(m.get("state"), "error"), "detail": m.get("state", ""), "machine_id": mid}

    async def start(self):
        check_enabled()
        async with self._starting:
            st = await self.status()
            mid = self.machine_id
            if mid and st["state"] == "gone":   # 机器没了：换一台自己的（或者下面新建一台）
                mid = await self.failover()
                st = await self.status() if mid else {"state": "none", "detail": ""}
            if st["state"] == "none" or not mid:
                try:
                    op = await self._req("POST", "/v1/machines", idem=True, json={
                    "name": "osa-computer", "templateId": self.template,
                    "autoSuspendAfterSeconds": self.idle_seconds, "metadata": {"app": "open-super-agent", "role": "primary"}})
                except ComputerError as e:
                    if " 429 " in str(e):
                        raise ComputerError(i18n.t("Instabox 账号的机器数量到上限了（免费版只能有一台）。"
                                                   "可以在电脑面板里选“用已有的电脑”，或者去 Instabox 删掉一台。")) from e
                    raise
                op = await self._wait_op(op)
                self._save_id(op["machineId"])
                mid = op["machineId"]
            elif st["detail"] == "suspended":
                await self._wait_op(await self._req("POST", f"/v1/machines/{mid}/resume", idem=True))
            elif st["detail"] == "stopped":
                await self._wait_op(await self._req("POST", f"/v1/machines/{mid}/start", idem=True))
            elif st["state"] == "running":
                await self._req("POST", f"/v1/machines/{mid}/wake", json={})   # 记一次活动，防止被闲置暂停
            d = await self._req("POST", f"/v1/machines/{mid}/desktop", timeout=100,
                                json={"action": "start", "width": self.width, "height": self.height})
            if not d.get("installed"):   # 首次使用要先装桌面，约半分钟
                if not d.get("installing"):
                    await self._req("POST", f"/v1/machines/{mid}/desktop", json={"action": "install"})
                for _ in range(120):
                    await asyncio.sleep(3)
                    d = await self._req("POST", f"/v1/machines/{mid}/desktop", json={"action": "status"})
                    if d.get("failed"):
                        raise ComputerError(i18n.t("桌面安装失败：{error}", error=str(d.get("log", ""))[:300]))
                    if d.get("installed"):
                        break
                await self._req("POST", f"/v1/machines/{mid}/desktop", timeout=100,
                                json={"action": "start", "width": self.width, "height": self.height})
            # 和本地后端保持一致的工作目录；桌面已在运行时分辨率可能不是配置值，以实际为准
            r = await self.exec("mkdir -p /data/workspace; DISPLAY=:1 xdpyinfo 2>/dev/null | awk '/dimensions:/{print $2}'", timeout=20)
            try:
                self.width, self.height = map(int, r.stdout.strip().split("x"))
            except ValueError:
                pass

    async def pause(self):
        mid = self.machine_id
        if mid and (await self.status())["state"] == "running":
            await self._wait_op(await self._req("POST", f"/v1/machines/{mid}/suspend", idem=True))

    async def _wake_retry(self, fn):
        """机器空闲后会自己挂起：遇到 409 machine_not_running 就叫醒它，再做一次。
        shell()/browser() 本来就会 start()，但 exec/read_file 走的是这里，之前原样把 409 抛给了模型。"""
        try:
            return await fn()
        except ComputerError as e:
            if "machine_not_found" in str(e):   # 机器没了：换一台，再试一次
                if not await self.failover():
                    raise
                await self.start()
                return await fn()
            if "machine_not_running" not in str(e):
                raise
            await self.start()
            return await fn()

    async def exec(self, cmd: str, timeout: int = 120, stdin: str | None = None) -> ExecResult:
        return await self._wake_retry(lambda: self._exec_once(cmd, timeout, stdin))

    async def _exec_once(self, cmd: str, timeout: int = 120, stdin: str | None = None) -> ExecResult:
        mid = self.machine_id
        if not mid:
            raise ComputerError(i18n.t("电脑还没创建"))
        body = {"cmd": cmd, "timeoutSeconds": max(1, min(600, timeout)), "cwd": "/data/workspace"}
        if stdin is not None:
            body["stdin"] = stdin
        r = await self._req("POST", f"/v1/machines/{mid}/exec", json=body, timeout=timeout + 30)
        return ExecResult(r.get("exitCode", -1), r.get("stdout", ""), r.get("stderr", ""), bool(r.get("timedOut")))

    async def read_bytes(self, path: str, limit: int = 32 << 20) -> bytes:
        return await self._wake_retry(lambda: self._read_once(path, limit))

    async def _read_once(self, path: str, limit: int) -> bytes:
        mid = self.machine_id
        r = await self.http.get(f"/v1/machines/{mid}/files/content", params={"path": path}, headers=_headers())
        if r.status_code == 404:
            raise ComputerError(i18n.t("文件不存在：{path}", path=path))
        if r.status_code >= 400:
            return await super().read_bytes(path, limit)
        if len(r.content) > limit:
            raise ComputerError(i18n.t("文件太大"))
        return r.content

    def takeover(self):
        super().takeover()
        if self.machine_id:   # 同时告诉 Instabox，它自带的电脑操作工具也会停手
            asyncio.create_task(self._req("POST", f"/v1/machines/{self.machine_id}/desktop", json={"action": "takeover"}))

    def handback(self):
        super().handback()
        if self.machine_id:
            asyncio.create_task(self._req("POST", f"/v1/machines/{self.machine_id}/desktop", json={"action": "handback"}))

    async def open_vnc(self):
        url = API.replace("https://", "wss://").replace("http://", "ws://") + f"/v1/machines/{self.machine_id}/vnc"
        # ping：云端那头的连接悄悄断了（NAT 超时、机器重启）也能发现——不发 ping 就一直等，画面冻在那里
        ws = await websockets.connect(url, additional_headers=_headers(), max_size=None,
                                      ping_interval=20, ping_timeout=20, close_timeout=5)

        async def recv() -> bytes:
            m = await ws.recv()
            return m if isinstance(m, bytes) else m.encode()

        return recv, ws.send, ws.close
