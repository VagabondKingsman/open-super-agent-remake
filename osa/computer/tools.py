"""Worker 的电脑工具。所有 Bot 共用一台电脑，几个任务同时用时各自一个浏览器窗口，满了排队；
computer_* 截的是自己窗口里的页面、按页面坐标点击，动作之后自动附上新截图，模型马上能看到结果。"""
import contextvars
import base64
from .. import i18n
from . import ComputerError, get

AUTO_SHOT = {"computer_click", "computer_type", "computer_key", "computer_scroll"}


BROWSER = {"browser_open", "browser_snapshot", "browser_click", "browser_type", "browser_key",
           "browser_scroll", "browser_back", "browser_read", "browser_upload"}
# 要用浏览器窗口的工具：第一次用时占一个窗口（满了排队）；终端和读写文件不占
WINDOW = BROWSER | {"computer_screenshot", "computer_click", "computer_type", "computer_key", "computer_scroll", "ask_human"}


def page_text(d: dict) -> str:
    """把浏览器返回的页面信息排成给模型和任务过程看的文字。句子走 i18n，随界面语言变。"""
    if "elements" not in d:   # browser_read
        more = i18n.t("\n…（共 {total} 字，用 offset={offset} 继续读）",
                      total=d["total"], offset=d["offset"] + len(d["text"])) \
            if d["offset"] + len(d["text"]) < d["total"] else ""
        return f"{d['title']} | {d['url']}\n{d['text']}{more}"
    els = "\n".join(d["elements"]) or i18n.t("（没有可操作元素）")
    if d.get("dialog"):
        els = i18n.t("（页面上有弹窗，下面只列弹窗里的元素；是登录、扫码或验证码就调用 ask_human）") + "\n" + els
    return i18n.t("当前页面：{title} | {url}（滚动 {scroll}）\n可操作元素：\n{els}\n\n正文开头：{text}",
                  title=d["title"], url=d["url"], scroll=d["scroll"], els=els, text=d["text"][:1200])


def _fn(name, desc, props: dict, required: list[str] | None = None):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required if required is not None else list(props)}}}


S, I, B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
SCHEMAS = [
    _fn("browser_open", "Open a URL in the computer's browser (current tab). Returns numbered actionable elements and the start of the page text.", {"url": S}),
    _fn("browser_snapshot", "Read the current browser page: actionable elements numbered [n], the start of the text, and the scroll position. Use it when the page changed or you are unsure.", {}),
    _fn("browser_click", "Click a page element. ref is the number from browser_snapshot.", {"ref": I}),
    _fn("browser_type", "Type into a field after clearing it. ref is the field number. submit=true presses Enter after typing.",
        {"ref": I, "text": S, "submit": B}, ["ref", "text"]),
    _fn("browser_key", "Press one key on the page: Enter, Tab, Escape, Backspace, ArrowDown, ArrowUp, PageDown, and similar.", {"key": S}),
    _fn("browser_scroll", "Scroll the page by one screen.", {"direction": {"type": "string", "enum": ["up", "down"]}}, ["direction"]),
    _fn("browser_back", "Go back in the browser.", {}),
    _fn("browser_read", "Read the full text of the current page. Each call returns at most 12000 characters; pass offset to continue.", {"offset": I}, []),
    _fn("browser_upload", "Upload files from the computer into the page. ref is the number of an upload or file input. paths are absolute file paths.",
        {"ref": I, "paths": {"type": "array", "items": S}}),
    _fn("computer_screenshot", "Screenshot the current page in the browser and return the image. Use it to see layout, images, charts, captchas, or whether an action worked. Use browser_snapshot for text and elements.", {}),
    _fn("computer_click", "Fallback: click screenshot coordinates (x, y). Use only when browser_click cannot, such as a canvas or an element with no number. Coordinates match computer_screenshot.",
        {"x": I, "y": I, "button": {"type": "string", "enum": ["left", "right", "middle"]}, "double": B}, ["x", "y"]),
    _fn("computer_type", "Fallback: type at the current focus on the page. Use browser_type for web fields.", {"text": S}),
    _fn("computer_key", "Press a key or chord on the page, for example Enter, Tab, ctrl+a, shift+Tab, or Escape. The browser's own shortcuts, such as a new tab, do not work.", {"keys": S}),
    _fn("computer_scroll", "Fallback: scroll the mouse wheel at the middle of the page. Use browser_scroll for web pages.",
        {"direction": {"type": "string", "enum": ["up", "down", "left", "right"]}, "amount": I}, ["direction"]),
    _fn("computer_shell", "Run a bash command in the computer terminal. The working directory is /data/workspace and files persist. Use it to download, process data, or run scripts.",
        {"cmd": S, "timeout": I}, ["cmd"]),
    _fn("computer_read_file", "Read a text file on the computer.", {"path": S}),
    _fn("computer_write_file", "Write a text file on the computer. This overwrites.", {"path": S, "content": S}),
    _fn("ask_human", "Call this when only a person can finish the step: login, captcha, QR code, payment check, or a choice the user must make. The user takes over the computer and hands it back, then you continue. Say clearly what they should do.", {"reason": S}),
    _fn("ask_approval", "Call this before a consequential action such as submitting a form, paying, sending a message or email, deleting data, or publishing. Say what you will do and the effect. Continue only after the user agrees.", {"action": S}),
]
NAMES = {s["function"]["name"] for s in SCHEMAS}

SYSTEM_HINT = """You have a computer (Linux, a Chromium browser, and a terminal, shared with the other bots). Your task has its own browser window.
Other tasks work in other windows at the same time. Logins and files are shared. Use the browser_* and computer_* tools:
- Prefer browser_* for web pages. They drive the browser directly and do not need you to guess coordinates from a picture.
  browser_open, then find a number in the element list, then browser_click or browser_type (submit=true presses Enter). The result includes a fresh element list.
  Use browser_read for the full text. Element numbers refresh on every result; use the latest ones. Use browser_upload to send a file to the page.
- Use computer_screenshot when you need to see how the page looks (charts, images, layout, captchas, or whether an action worked). It captures the page in your window.
  When browser_* cannot do it (a canvas, an element with no number, a key chord), use computer_click, computer_type, or computer_key with screenshot coordinates.
  Those actions attach a new screenshot.
- For a plain lookup, prefer web_search or fetch_url. They are faster. Use the browser when you need a login, interaction, or the real page.
- Use computer_shell to download files, process data, or run scripts.
- On a captcha (slider puzzle, click-the-text, image challenge, a security-check page), a QR login, a password login, an SMS code, or any human-check:
  call ask_human immediately. Do not try to drag or solve it. Those checks exist to stop automation; trying fails and can get the account or IP blocked.
  The ask_human reason must say what the user should do, for example drag the slider to finish the puzzle.
- Call ask_human for any other step only a person can do. Call ask_approval before a consequential action such as submit, pay, or send."""


# 当前 Worker 占用电脑用的标识（Heavy 模式下同一任务的几个 Worker 各不相同）
CLAIM: contextvars.ContextVar[str] = contextvars.ContextVar("osa_claim", default="")


async def release():
    key = CLAIM.get()
    if key:
        await get().release(key)


def _label(task, key: str) -> str:
    if isinstance(task.id, str):
        return task.id
    part = key.rpartition(":")[2]
    return i18n.t("任务 #{id}", id=task.id) + \
        (" · " + i18n.t("研究员 {n}", n=int(part[1:]) + 1) if part[:1] == "h" and part[1:].isdigit() else "")


def _progress_label(name: str, args: dict) -> str:
    """任务卡片和任务过程里显示的这一步在做什么。"""
    fixed = {"browser_snapshot": i18n.N_("查看页面"), "browser_back": i18n.N_("后退"), "browser_read": i18n.N_("读取页面"),
             "computer_screenshot": i18n.N_("截图")}
    if name in fixed:
        return i18n.t(fixed[name])
    if name == "browser_open":
        return i18n.t("打开 {url}", url=args.get("url", ""))
    if name == "browser_click":
        return i18n.t("点击 [{ref}]", ref=args.get("ref"))
    if name in ("browser_type", "computer_type"):
        return i18n.t("输入 “{text}”", text=str(args.get("text", ""))[:30])
    if name in ("browser_key", "computer_key"):
        return i18n.t("按键 {key}", key=args.get("key") if name == "browser_key" else args.get("keys"))
    if name in ("browser_scroll", "computer_scroll"):
        return i18n.t("滚动 {direction}", direction=args.get("direction"))
    if name == "browser_upload":
        return i18n.t("上传文件到 [{ref}]", ref=args.get("ref"))
    if name == "computer_click":
        return i18n.t("点击 ({x}, {y})", x=args.get("x"), y=args.get("y"))
    if name == "computer_shell":
        return i18n.t("终端：{cmd}", cmd=str(args.get("cmd", ""))[:60])
    if name == "computer_read_file":
        return i18n.t("读取 {path}", path=args.get("path"))
    if name == "computer_write_file":
        return i18n.t("写入 {path}", path=args.get("path"))
    if name == "ask_human":
        return i18n.t("请你帮忙：{reason}", reason=str(args.get("reason", ""))[:60])
    if name == "ask_approval":
        return i18n.t("请求确认：{action}", action=str(args.get("action", ""))[:60])
    return name


async def call(task, name: str, args: dict, notify_progress, key: str = "") -> tuple[str, bytes | None]:
    """执行一个电脑工具，返回 (给模型的文字, 可选截图)。key 是谁在用：任务的 CLAIM，对话里直接操作的是 chat-<Bot id>。"""
    from .. import approvals
    c = get()
    key = key or CLAIM.get() or str(task.id)
    if name in WINDOW and not key.startswith("chat-"):
        await c.claim(key, _label(task, key), notify_progress,
                      {"task_id": task.id if isinstance(task.id, int) else None, "bot_id": task.bot_id})
    await notify_progress(_progress_label(name, args))
    try:
        if name == "browser_upload":
            paths = args.get("paths") or []
            if isinstance(paths, str):
                paths = [paths]
            if not paths:
                return i18n.t("没有给要上传的文件路径"), None
            await c.browser("upload", key=key, ref=args.get("ref"), files=[str(x) for x in paths][:10])
            return page_text(await c.browser("snapshot", key=key)), None
        if name in BROWSER:
            op = name.removeprefix("browser_")
            if op == "open" and not str(args.get("url", "")).startswith(("http://", "https://")):
                return i18n.t("只能打开 http / https 网址"), None
            kw = {k: v for k, v in args.items() if v is not None}
            return page_text(await c.browser(op, key=key, **kw)), None
        if name == "computer_screenshot":
            return i18n.t("这是浏览器里当前页面的截图。"), await c.page_shot(key)
        if name == "computer_click":
            button = args.get("button") or "left"
            if button not in ("left", "right", "middle"):
                return i18n.t("button 只能是 left / right / middle"), None
            await c.browser("click_xy", key=key, x=int(args["x"]), y=int(args["y"]), button=button, double=bool(args.get("double")))
            text = i18n.t("已点击。")
        elif name == "computer_type":
            if not args.get("text"):
                return i18n.t("没有要输入的文字"), None
            await c.browser("type", key=key, text=str(args["text"]))
            text = i18n.t("已输入。")
        elif name == "computer_key":
            await c.browser("press", key=key, keys=str(args.get("keys") or ""))
            text = i18n.t("已按键。")
        elif name == "computer_scroll":
            await c.browser("wheel", key=key, direction=args.get("direction") or "down", amount=args.get("amount") or 3)
            text = i18n.t("已滚动。")
        elif name == "computer_shell":
            return (await c.shell(args["cmd"], int(args.get("timeout") or 120))).text(), None
        elif name == "computer_read_file":
            data = await c.read_bytes(args["path"], 1 << 20)
            return data.decode(errors="replace")[:20000], None
        elif name == "computer_write_file":
            await c.write_bytes(args["path"], args["content"].encode())
            return i18n.t("已写入 {path}（{n} 字）", path=args["path"], n=len(args["content"])), None
        elif name == "ask_human":
            await c.start()
            if c.controller == "bot":   # 把这个任务的窗口放到最前面，用户一接手就看到；用户正在帮别的任务时不打扰，等他点这张卡片的“接手”
                try:
                    await c.front(key)
                except ComputerError:
                    pass
            c.asking[task.id] = key   # 从卡片上接手时，把这个（不是同一任务的别的研究员）的窗口放到前面
            try:
                ok, note = await approvals.request(task, "ask_human", {"需要你做的事": args["reason"]}, kind="help")
            finally:
                if c.asking.get(task.id) == key:
                    c.asking.pop(task.id, None)
            done = i18n.t("用户已处理完并交还电脑。{note}", note=note) if ok else i18n.t("用户没有处理：{note}", note=note)
            return done.strip(), None
        elif name == "ask_approval":
            ok, note = await approvals.request(task, "ask_approval", {"操作": args["action"]})
            done = i18n.t("用户同意了。{note}", note=note) if ok else i18n.t("用户拒绝了，不要执行这个操作。{note}", note=note)
            return done.strip(), None
        else:
            return i18n.t("未知的电脑工具"), None
    except ComputerError as e:
        return i18n.t("电脑操作失败：{error}", error=e), None
    shot = await c.page_shot(key) if name in AUTO_SHOT else None
    return text, shot


def image_message(png: bytes, caption: str = "the current page", coords: bool = True) -> dict:
    w, h = int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")   # PNG 头里的宽高
    tail = "click coordinates use this size" if coords else "for looking only; do not click coordinates on this image"
    return {"role": "user", "content": [
        {"type": "text", "text": f"(system image: {caption}, {w}x{h}, {tail})"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}}]}


def prune_images(msgs: list[dict], keep: int = 2):
    """只保留最近 keep 张截图，更早的换成文字，避免上下文越来越长。"""
    seen = 0
    for m in reversed(msgs):
        if isinstance(m.get("content"), list) and any(p.get("type") == "image_url" for p in m["content"]):
            seen += 1
            if seen > keep:
                m["content"] = "(an earlier screenshot was omitted)"
