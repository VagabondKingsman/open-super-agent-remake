"""推送到手机：Bot 能把通知推到你的手机上（Bark、Server酱、PushPlus、ntfy、Telegram、Gotify、企业微信、飞书、钉钉），后台任务做完也能推。

设置里 channel 选一种，再填它下面那一组（别的组不用管）。token、key、webhook 地址建议存进保险库，写成 "vault:名字"：
- bark（iPhone 上的 Bark App）：device_key 是 App 里那串 key；自己搭的服务器改 server。
- serverchan（Server酱，sct.ftqq.com）：sendkey。Server酱³ 的 sctp 开头的 key 也行。
- pushplus（pushplus.plus，推到微信）：token。
- ntfy（ntfy.sh 或自己搭的）：topic，要登录的再填 token。topic 别人猜到就能看，起个长一点的名字。
- telegram：bot_token（找 @BotFather 建 Bot）和 chat_id（你和 Bot 的对话 id）。
- gotify（自己搭的）：server 和 app_token。
- wecom（企业微信群机器人）、feishu（飞书群机器人）、dingtalk（钉钉群机器人）：webhook 地址。钉钉开了“加签”的不支持，用“自定义关键词”。
- wecom_app（企业微信自建应用，推到个人微信 / 企业微信）：corp_id、agent_id、secret，to_user 默认 @all。
  新建的应用要在企业微信后台把这台服务器的 IP 加进“可信 IP”，不然发不出去。
on_task_done：off 不推（默认）、failed 只推失败的、all 每个后台任务（包括定时任务）做完都推；任务里已经推过一次的不再重复推。

别的插件能用它提供的 notify 服务：META 里写 "inject": ["notify"]，然后 await ctx.services["notify"].send("文字", title="标题", url="链接")，
发不出去会抛 RuntimeError。
"""
import asyncio
import re
import time
import httpx
from osa import i18n
from osa.registry import ROUTER, WORKER, Tool

META = {"title": "推送到手机", "version": "1.0", "author": "open-super-agent", "provide": ["notify"],
        "config": {
            "channel": "",
            "on_task_done": "off",
            "bark": {"server": "https://api.day.app", "device_key": ""},
            "serverchan": {"sendkey": ""},
            "pushplus": {"token": ""},
            "ntfy": {"server": "https://ntfy.sh", "topic": "", "token": ""},
            "telegram": {"bot_token": "", "chat_id": ""},
            "gotify": {"server": "", "app_token": ""},
            "wecom": {"webhook": ""},
            "wecom_app": {"corp_id": "", "agent_id": "", "secret": "", "to_user": "@all"},
            "feishu": {"webhook": ""},
            "dingtalk": {"webhook": ""},
        }}
CHANNELS = {"bark": "Bark", "serverchan": "ServerChan", "pushplus": "PushPlus", "ntfy": "ntfy", "telegram": "Telegram",
            "gotify": "Gotify", "wecom": "WeCom group bot", "wecom_app": "WeCom app", "feishu": "Feishu group bot",
            "dingtalk": "DingTalk group bot"}
REQUIRED = {"bark": ["device_key"], "serverchan": ["sendkey"], "pushplus": ["token"], "ntfy": ["topic"],
            "telegram": ["bot_token", "chat_id"], "gotify": ["server", "app_token"], "wecom": ["webhook"],
            "wecom_app": ["corp_id", "agent_id", "secret"], "feishu": ["webhook"], "dingtalk": ["webhook"]}
URLS = {"bark": "server", "ntfy": "server", "gotify": "server", "wecom": "webhook", "feishu": "webhook", "dingtalk": "webhook"}
DEFAULT_SERVER = {"bark": "https://api.day.app", "ntfy": "https://ntfy.sh"}
# 正文最多多少字：企业微信一条最多 2048 字节，Bark 走苹果推送最多 4KB，Telegram 4096 字
LIMIT = {"wecom": 600, "wecom_app": 600, "bark": 1000, "telegram": 3500}
MAX_TEXT = 3000
WECOM_API = "https://qyapi.weixin.qq.com/cgi-bin/"

SCHEMA = {"type": "function", "function": {
    "name": "push_to_phone",
    "description": "Push a notification to the user's own phone (through the Bark / ServerChan / ntfy / Telegram etc. channel set up "
                   "in the plugin settings). Use it when the user says \"remind me\", \"tell me when it's done\" or \"send it to my phone\", "
                   "or when a background task (including a scheduled one) has something the user must know right away. "
                   "It only reaches the user themself and cannot message anyone else.",
    "parameters": {"type": "object", "properties": {
        "text": {"type": "string", "description": "Notification body: say briefly what happened"},
        "title": {"type": "string", "description": "Optional title, about ten words"},
        "url": {"type": "string", "description": "Optional link to open when the notification is tapped, starting with http or https"}},
        "required": ["text"]}}}


def _cut(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n - 1] + "…"


def link(url: str) -> str:
    return i18n.t("[打开链接]({url})", url=url)


def _plain(title: str, text: str, url: str) -> str:
    return "\n".join(x for x in (title, text, url) if x)


def check(channel: str, conf: dict) -> dict:
    """检查某个渠道的设置，返回整理好的一份（补上默认服务器、去掉结尾的 /）；不对就抛 ValueError，原因显示在设置页上。"""
    if channel not in CHANNELS:
        raise ValueError(i18n.t("先在设置里选 channel：{channels}，再填它下面那一组", channels=" / ".join(CHANNELS)))
    conf = {k: (v.strip() if isinstance(v, str) else v) for k, v in (conf or {}).items()}
    if channel in DEFAULT_SERVER and not conf.get("server"):
        conf["server"] = DEFAULT_SERVER[channel]
    for k in REQUIRED[channel]:
        if conf.get(k) in (None, ""):
            raise ValueError(i18n.t("channel 选的是 {channel}：先填 {channel}.{key}（写的是 vault:名字 的话，看看保险库里有没有这一项）",
                                    channel=channel, key=k))
    if (k := URLS.get(channel)) and not str(conf[k]).startswith(("https://", "http://")):
        raise ValueError(i18n.t("{channel}.{key} 要是 http 或 https 开头的地址", channel=channel, key=k))
    if k:
        conf[k] = str(conf[k]).rstrip("/") if k == "server" else str(conf[k])
    if channel == "ntfy" and not re.fullmatch(r"[-_A-Za-z0-9]{1,64}", str(conf["topic"])):
        raise ValueError(i18n.t("ntfy.topic 只能用字母、数字、- 和 _，最多 64 个字"))
    if channel == "telegram" and not re.fullmatch(r"-?\d+|@\w+", str(conf["chat_id"])):
        raise ValueError(i18n.t("telegram.chat_id 是一串数字（群是负数），或者 @频道名"))
    if channel == "wecom_app" and not str(conf["agent_id"]).isdigit():
        raise ValueError(i18n.t("wecom_app.agent_id 是应用详情页上的 AgentId（一串数字）"))
    return conf


def build(channel: str, conf: dict, text: str, title: str = "", url: str = "", token: str = "") -> dict:
    """要发的请求：{"url", "json", "headers"}，都是 POST。只拼不发，测试直接看它。token 是企业微信应用的 access_token。"""
    text = _cut(text, LIMIT.get(channel, MAX_TEXT))
    plain = _plain(title, text, url)
    if channel == "bark":
        body = {"device_key": conf["device_key"], "body": text, "group": "osa"}
        return {"url": conf["server"] + "/push", "json": body | ({"title": title} if title else {}) | ({"url": url} if url else {})}
    if channel == "serverchan":
        key = conf["sendkey"]
        m = re.match(r"sctp(\d+)t", key)   # Server酱³ 的 key 里带着用户 id，地址不一样
        api = f"https://{m[1]}.push.ft07.com/send/{key}.send" if m else f"https://sctapi.ftqq.com/{key}.send"
        return {"url": api, "json": {"title": _cut(title or text.split("\n")[0], 32),
                                     "desp": text + (f"\n\n{link(url)}" if url else "")}}
    if channel == "pushplus":
        return {"url": "https://www.pushplus.plus/send", "json": {
            "token": conf["token"], "title": title or _cut(text.split("\n")[0], 50),
            "content": text + (f"\n\n{link(url)}" if url else ""), "template": "markdown"}}
    if channel == "ntfy":   # 用 JSON 发到根地址：标题里有中文也不用管请求头的编码
        body = {"topic": conf["topic"], "message": text} | ({"title": title} if title else {}) | ({"click": url} if url else {})
        return {"url": conf["server"], "json": body,
                "headers": {"Authorization": f"Bearer {conf['token']}"} if conf.get("token") else {}}
    if channel == "telegram":   # 不用 parse_mode：正文里的 * _ 不用转义
        return {"url": f"https://api.telegram.org/bot{conf['bot_token']}/sendMessage",
                "json": {"chat_id": conf["chat_id"], "text": plain, "disable_web_page_preview": True}}
    if channel == "gotify":
        body = {"message": text, "priority": 5} | ({"title": title} if title else {})
        if url:
            body["extras"] = {"client::notification": {"click": {"url": url}}}
        return {"url": conf["server"] + "/message", "json": body, "headers": {"X-Gotify-Key": conf["app_token"]}}
    if channel == "wecom_app":
        return {"url": f"{WECOM_API}message/send?access_token={token}", "json": {
            "touser": conf.get("to_user") or "@all", "msgtype": "text", "agentid": int(conf["agent_id"]), "text": {"content": plain}}}
    if channel == "feishu":
        return {"url": conf["webhook"], "json": {"msg_type": "text", "content": {"text": plain}}}
    if channel in ("wecom", "dingtalk"):
        return {"url": conf["webhook"], "json": {"msgtype": "text", "text": {"content": plain}}}
    raise ValueError(f"Unknown channel {channel}")


def failure(channel: str, status: int, data) -> str:
    """对方的回复 -> 没发成功的原因，成功返回空。好几家出错也回 HTTP 200，要看 JSON 里的 code。"""
    data = data if isinstance(data, dict) else {}
    msg = data.get("message") or data.get("msg") or data.get("errmsg") or data.get("description") or data.get("error") or ""
    if status >= 400:
        return f"HTTP {status}" + (f": {msg}" if msg else "")
    ok = {"bark": lambda d: d.get("code") == 200, "serverchan": lambda d: d.get("code") == 0,
          "pushplus": lambda d: d.get("code") == 200, "telegram": lambda d: d.get("ok") is True,
          "wecom": lambda d: d.get("errcode") == 0, "wecom_app": lambda d: d.get("errcode") == 0,
          "dingtalk": lambda d: d.get("errcode") == 0,
          "feishu": lambda d: d.get("code", d.get("StatusCode")) == 0}.get(channel)
    if ok and not ok(data):
        return str(msg or data)[:300] or "no success reported"
    return ""


class Notifier:
    """notify 服务：await notifier.send(文字, title="", url="")，发不出去抛 RuntimeError。"""

    def __init__(self, channel: str, conf: dict):
        self.channel = channel
        self.name = CHANNELS[channel]
        self._conf = conf
        self._token, self._token_until = "", 0.0   # 企业微信应用的 access_token，两小时有效

    async def _wecom_token(self, client) -> str:
        if self._token and time.time() < self._token_until:
            return self._token
        r = await client.get(WECOM_API + "gettoken", params={"corpid": self._conf["corp_id"], "corpsecret": self._conf["secret"]})
        try:
            d = r.json()
        except ValueError:
            d = {"errmsg": f"HTTP {r.status_code}"}
        if d.get("errcode") != 0 or not d.get("access_token"):
            raise RuntimeError(f"WeCom did not return an access_token: {d.get('errmsg') or d}")
        self._token, self._token_until = d["access_token"], time.time() + int(d.get("expires_in", 7200)) - 300
        return self._token

    async def send(self, text: str, title: str = "", url: str = ""):
        text, title, url = str(text or "").strip(), str(title or "").strip()[:100], str(url or "").strip()
        if not text:
            raise RuntimeError("The notification text is empty")
        if url and not url.startswith(("https://", "http://")):
            raise RuntimeError("url must start with http or https")
        try:
            async with asyncio.timeout(10), httpx.AsyncClient(timeout=8) as client:   # 一次推一条，不常用，不留着连接
                token = await self._wecom_token(client) if self.channel == "wecom_app" else ""
                req = build(self.channel, self._conf, text, title, url, token)
                r = await client.post(req["url"], json=req["json"], headers=req.get("headers") or {})
        except TimeoutError:
            raise RuntimeError(f"{self.name} did not answer within 10 seconds") from None
        except httpx.HTTPError as e:
            raise RuntimeError(f"Could not reach {self.name} ({type(e).__name__})") from None
        try:
            data = r.json()
        except ValueError:
            data = None
        if why := failure(self.channel, r.status_code, data):
            if self.channel == "wecom_app" and isinstance(data, dict) and data.get("errcode") in (40014, 42001):
                self._token = ""   # token 失效了，下次重新拿
            raise RuntimeError(f"{self.name} rejected it: {why}")


def task_message(task: dict, bot: dict, result: str) -> tuple[str, str]:
    ok = task.get("status") == "done"
    name = bot.get("name", "Bot")
    title = i18n.t("✅ {bot} 的任务完成了", bot=name) if ok else i18n.t("❌ {bot} 的任务没完成", bot=name)
    result = (result or "").strip()
    goal = _cut(task.get("goal") or i18n.t("任务 #{id}", id=task.get("id")), 80)
    return title, goal + ("\n\n" + _cut(result, 800) if result else "")


def apply(ctx):
    channel = ctx.config.get("channel") or ""
    mode = ctx.config.get("on_task_done") or "off"
    if mode not in ("off", "failed", "all"):
        raise ValueError(i18n.t("on_task_done 只能是 off（不推）/ failed（只推失败的）/ all（都推）"))
    raw = ctx.config.get(channel) if channel in CHANNELS else {}
    conf = check(channel, {k: ctx.secret(v) for k, v in (raw if isinstance(raw, dict) else {}).items()})
    notifier = Notifier(channel, conf)
    ctx.provide("notify", notifier, f"push a notification to the user's phone ({notifier.name})")
    pushed: set = set()   # 自己调过 push_to_phone 的任务：做完时不再推一次

    async def run(call):
        try:
            await notifier.send(call.args.get("text"), call.args.get("title") or "", call.args.get("url") or "")
        except RuntimeError as e:
            return f"Not pushed: {e}"
        if call.task is not None:
            if len(pushed) > 1000:
                pushed.clear()
            pushed.add(getattr(call.task, "id", None))
        return f"Pushed ({notifier.name})."

    ctx.tool(Tool("push_to_phone", SCHEMA, run, where=frozenset({ROUTER, WORKER}),
                  describe=f"Push a notification to the user's phone ({notifier.name})",
                  progress=lambda a: i18n.t("推送到手机：{text}", text=str(a.get("title") or a.get("text") or "")[:40])))

    async def on_done(task: dict, bot: dict, result: str, **_):
        if task.get("id") in pushed:
            pushed.discard(task.get("id"))
            return
        if mode == "failed" and task.get("status") == "done":
            return
        title, text = task_message(task, bot, result)
        try:
            await notifier.send(text, title)
        except RuntimeError as e:
            ctx.log.warning("推送任务 #%s 失败：%s", task.get("id"), e)

    if mode != "off":
        ctx.on("task_done", on_done)
