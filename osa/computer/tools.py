"""Worker 的电脑工具。所有 Bot 共用一台电脑，几个任务同时用时各自一个浏览器窗口，满了排队；
computer_* 截的是自己窗口里的页面、按页面坐标点击，动作之后自动附上新截图，模型马上能看到结果。
本机电脑（host.py）的工具说明和提示词不一样：文件只在工作文件夹里，终端默认没有；
上传文件、写文件、提交、终端命令按确认规则先问用户（_confirm，规则见 approvals.decide）。
本机（或借来的 Mac）给了屏幕权限时还有 desktop_* 工具：看整个屏幕、用真实的鼠标键盘操作别的 App（_desktop，见 host.py）。"""
import asyncio
import contextvars
import base64
import re
import time
from .. import i18n
from . import ComputerError, get, macdesk
from .base import HOSTS

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
    # 元素行里的记号在页面脚本里是英文（脚本不能 import 这里）：到这里才换成界面语言
    for en, zh in (("checked", "（已选中）"), ("offscreen", "（屏幕外）")):
        word = i18n.t(zh)
        els = els.replace(f" ({en})", word if word.startswith("（") else f" {word}")
    if d.get("dialog"):
        els = i18n.t("（页面上有弹窗，下面只列弹窗里的元素；是登录、扫码或验证码就调用 ask_human）") + "\n" + els
    scroll = d.get("scroll")
    if d.get("vh"):   # 视口高度：判断“下面还有没有东西”要用
        scroll = i18n.t("{scroll}，视口高 {vh}", scroll=scroll, vh=d["vh"])
    return i18n.t("当前页面：{title} | {url}（滚动 {scroll}）\n可操作元素：\n{els}\n\n正文开头：{text}",
                  title=d["title"], url=d["url"], scroll=scroll, els=els, text=d["text"][:1200])


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
    _fn("computer_screenshot", "Take a picture of the current page in the browser and return the image. Use it to see what the page looks like (images, charts, layout, captchas, whether an action worked); "
        "for page content and elements use browser_snapshot. With save=true the screenshot is saved in the computer's working folder (screenshots subfolder) and the path is returned; "
        "to send a page screenshot to the user, send that file with send_file. "
        "With screen=true it captures the whole screen instead (every window, the desktop and panels) for looking only: "
        "click coordinates still follow the page screenshot, not this image.", {"save": B, "screen": B}, []),
    _fn("computer_click", "[Fallback] Click the page at screenshot coordinates (x, y). Use only when browser_click cannot do it (canvas, elements without a number); "
        "coordinates follow the computer_screenshot image.",
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
DESK_SCHEMAS = [
    _fn("desktop_screenshot", "Take a picture of the whole screen of the user's Mac (main display) and return the image, plus the frontmost app, the windows on screen and the mouse position. "
        "Use it first to look at the screen when operating apps other than the browser; coordinates for desktop_click and the other tools follow this screenshot. "
        "With save=true the screenshot is saved in the working folder (screenshots subfolder) and the file path is returned; to send the screenshot to the user, send that file with send_file.",
        {"save": B}, []),
    _fn("desktop_click", "Click the screen at desktop_screenshot coordinates (the real mouse; the clicked window is brought to the front)",
        {"x": I, "y": I, "button": {"type": "string", "enum": ["left", "right", "middle"]}, "double": B}, ["x", "y"]),
    _fn("desktop_drag", "Hold the left mouse button and drag from (x, y) to (to_x, to_y): drag files, sliders, box selections", {"x": I, "y": I, "to_x": I, "to_y": I}),
    _fn("desktop_type", "Type text where the screen currently has focus (entered by pasting, so any language works and the input method does not interfere; it does not press enter). Click the place to type into first", {"text": S}),
    _fn("desktop_key", "Press a key or key combination, e.g. enter, esc, tab, backspace, cmd+a, cmd+c, cmd+v, cmd+tab, cmd+space (focus search), "
        "cmd+w (close window), cmd+q (quit app), cmd+shift+g (go to folder in Finder), up, down. "
        "To press several keys in order separate them with spaces and they are all pressed in one call, e.g. \"1 2 3 * 4 5 enter\", \"down down enter\"", {"keys": S}),
    _fn("desktop_scroll", "Move the mouse to (x, y) on the screenshot, then scroll",
        {"x": I, "y": I, "direction": {"type": "string", "enum": ["up", "down", "left", "right"]}, "amount": I}, ["x", "y", "direction"]),
    _fn("desktop_open_app", "Open an app or bring it to the front (e.g. WeChat, Finder, Notes, Calendar, Safari, System Settings); name is the app's name", {"name": S}),
]
DESKTOP = {s["function"]["name"] for s in DESK_SCHEMAS}
NAMES = {s["function"]["name"] for s in SCHEMAS} | DESKTOP

_HOST_FILES = {
    "computer_read_file": "Read a text file in the working folder (the path may be relative to the working folder)",
    "computer_write_file": "Write a text file in the working folder (overwrites; the path may be relative to the working folder)",
    "browser_upload": "Upload files from the working folder into the page: ref is the number of the \"upload / choose file\" button or file input, paths are the file paths",
}


def desk_schemas(c=None) -> list[dict]:
    """操作整个屏幕的工具：只有本机（或借来的 Mac）是 Mac、给了两个权限才给。"""
    c = c or get()
    return DESK_SCHEMAS if c.backend in HOSTS and c.desktop_enabled() else []


def schemas(c=None) -> list[dict]:
    """给 Worker 的电脑工具。本机电脑：文件工具说明换成工作文件夹，终端没打开就不给 computer_shell，
    能操作整个屏幕时再加上 desktop_*。"""
    c = c or get()
    if c.backend not in HOSTS:
        return SCHEMAS
    out = []
    for s in SCHEMAS:
        f = s["function"]
        if f["name"] == "computer_shell":
            if not c.shell_enabled():
                continue
            s = _fn("computer_shell", f"Run a shell command on the user's computer (the working directory is the working folder {c.workspace}). Every command needs user confirmation.",
                    {"cmd": S, "timeout": I}, ["cmd"])
        elif f["name"] in _HOST_FILES:
            s = {"type": "function", "function": {**f, "description": _HOST_FILES[f["name"]]}}
        elif f["name"] == "computer_screenshot":   # 本机电脑看整个屏幕走 desktop_screenshot（要权限），这里不给 screen
            s = _fn("computer_screenshot", f["description"].split(" With screen=true")[0], {"save": B}, [])
        out.append(s)
    return out + desk_schemas(c)


def _intro(c) -> str:
    if c.backend not in HOSTS:
        return f"""You have a computer (Linux + Chromium browser + terminal, shared with the other Bots). Your task has its own browser window
(and its own browser profile: cookies and logins belong to this task, other tasks do not see them). Other tasks work in their own windows
at the same time without interfering; files are shared by all. Operate it with the browser_* / computer_* tools:
It is a different machine from the one OSA runs on: the host's paths (/home/..., /tmp/...) do not exist here - work inside {c.workspace}.
"""
    shell = ("- Terminal: computer_shell runs commands on the user's computer (the working directory is the working folder). Every command needs user confirmation (except command prefixes the user has \"always allowed\"; commands with ; && | $( or redirection are asked every time); use it only when necessary."
             if c.shell_enabled() else "- No terminal (the user has not turned it on). Download files with the browser; read and write files with computer_read_file / computer_write_file.")
    desk = DESK_HINT if c.desktop_enabled() else ""
    return f"""You have a computer: a Chrome browser on the user's computer set up specially for Bots (separate from the user's own everyday Chrome, shared by all Bots;
you can directly use any site the user has logged into there). Your task has its own browser window; other tasks work in their own windows at the same time without interfering. Operate it with the browser_* / computer_* tools:
- Files can only live in the working folder {c.workspace}: computer_read_file / computer_write_file can only read and write files inside it (relative paths are fine),
  files the browser downloads are in its downloads subfolder, and browser_upload can only upload files from inside it.
{shell}
- When uploading files, writing files, or clicking buttons like "send / publish / submit / pay", the system automatically pops up a confirmation card for the user, so you do not need to call ask_approval for these;
  if the user refuses, do not try again; do it another way or explain in your result.{desk}"""


DESK_HINT = """
- The whole computer: the user also allows you to operate other apps on this Mac (desktop_* tools, using the user's real screen, mouse and keyboard).
  For the web still prefer browser_* (the Bot's own Chrome: fast and it does not tie up the mouse); use desktop_* only for things outside the web (chat apps like WeChat, files in Finder, Notes, Calendar,
  System Settings, the user's own browser...): first desktop_screenshot to look at the screen → desktop_open_app to open or switch apps →
  desktop_click at screenshot coordinates → desktop_type to enter text → desktop_key for shortcuts. A fresh screenshot is attached automatically after every action.
  The first use pops up a card asking the user to agree. The mouse and keyboard can serve only one task at a time and other tasks wait, so finish as soon as you are done.
  When the user moves the mouse or presses a key you are paused; after the user hands control back, desktop_screenshot again before continuing.
  Clicking buttons like "send / pay" on screen, or pressing enter in a multi-line input, automatically pops up a confirmation card; for other consequential actions (deleting files, changing system settings,
  running commands in a terminal) use ask_approval first. Do not operate Open Super Agent's own window. When the screen is locked, use ask_human to ask the user to unlock it.
  To give the user a screenshot: desktop_screenshot(save=true) to save it in the working folder, then send_file; do not use the system screenshot shortcuts or a "screenshot" app."""


def system_hint(c=None) -> str:
    c = c or get()
    shell = "" if c.backend in HOSTS else ("\n- Use computer_shell to download files, process data and run scripts. "
                                          "The first command of a task is shown to the user for confirmation; after that the task runs them directly.")
    return _intro(c) + _BODY.replace("{shell}", shell)


def capability(c=None) -> str:
    """Router 的能力清单里那一句：电脑是什么、能做什么。"""
    c = c or get()
    if c.backend in HOSTS:
        return ("Every background task can use a Chrome browser on the user's computer set up specially for Bots (separate from the user's own Chrome, shared by all Bots); "
                "it can open web pages, click, type, act after logging in, and upload and download files (files live in the working folder)"
                + (", and run terminal commands (each needs user confirmation)" if c.shell_enabled() else "") + ". Several tasks can use it at once, each in its own browser window, "
                "sharing login state; tasks only queue when too many use it at once. The browser window is on the user's screen and the picture is also visible in the right panel. "
                "A confirmation card pops up automatically when uploading files, writing files, or clicking buttons like \"send / publish / pay\". "
                + ("Tasks can also look at the whole screen and operate other apps on this Mac with the real mouse and keyboard (WeChat, Finder, Notes, "
                   "System Settings, etc.; desktop_* tools); each task asks the user the first time it uses them; the mouse and keyboard serve only one task at a time. "
                   "Use desktop_* yourself only for one or two steps (open an app, glance at the screen); for pressing a series of buttons, filling things in or going back and forth in an app, "
                   "dispatch a task (the number of tool calls you have in this turn is limited)." if c.desktop_enabled() else ""))
    return ("Every background task can use a computer shared by all Bots (Linux desktop + Chromium browser + terminal); "
            "it can open web pages, click, type, act after logging in, upload and download files, and run scripts. Several tasks can use it at once, each in its own browser window, "
            "each task with its own browser profile (its own cookies and logins), sharing files; tasks only queue when too many use it at once. "
            "The user can watch the screen live in the right panel. "
            f"It is a different machine from the host: give paths inside {c.workspace}, never host paths.")


_BODY = """
- To operate web pages prefer the browser_* tools (they control the browser directly: fast and precise, no estimating coordinates from images):
  browser_open to open → find the number in the returned element list → browser_click / browser_type (submit=true presses enter) → the result contains the new element list.
  For the full content use browser_read. Element numbers are refreshed on every return; use the latest ones. To upload a file to a page use browser_upload.
- When you need to see what the page looks like (charts, images, layout, captchas, confirming an action worked) use computer_screenshot (it shoots the page in your window);
  for what browser_* cannot handle (canvas pages, elements without a number, key combinations) use computer_click / computer_type / computer_key at screenshot coordinates;
  a fresh screenshot is attached automatically after these actions.
- For plain research prefer web_search / fetch_url, which are faster and cheaper; use the browser only when you need to log in, interact, or see the page's actual look.{shell}
- When you see a captcha (slider puzzle, click-the-characters, image verification, an "abnormal environment" / "security check" page), QR-code login, password login, SMS verification,
  or a human check: call ask_human **immediately** and never try to drag or solve it yourself; these exist to block automation, so trying only fails
  and may get the account or IP flagged. In ask_human's reason say clearly what the user must do (e.g. "drag the slider to complete the puzzle check").
- Call ask_human for any other step only a human can do; call ask_approval before consequential actions such as submitting, paying, or sending."""


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
    if name == "desktop_screenshot":
        return i18n.t("看屏幕")
    if name == "desktop_click":
        return i18n.t("点击屏幕 ({x}, {y})", x=args.get("x"), y=args.get("y"))
    if name == "desktop_drag":
        return i18n.t("在屏幕上拖动")
    if name == "desktop_type":
        return i18n.t("输入 “{text}”", text=str(args.get("text", ""))[:30])
    if name == "desktop_key":
        return i18n.t("按键 {key}", key=args.get("keys"))
    if name == "desktop_scroll":
        return i18n.t("滚动 {direction}", direction=args.get("direction"))
    if name == "desktop_open_app":
        return i18n.t("打开 {app}", app=args.get("name", ""))
    if name == "ask_human":
        return i18n.t("请你帮忙：{reason}", reason=str(args.get("reason", ""))[:60])
    if name == "ask_approval":
        return i18n.t("请求确认：{action}", action=str(args.get("action", ""))[:60])
    return name


ENTER = {"enter", "return"}


async def _confirm(task, c, name: str, args: dict, key: str) -> str | None:
    """按确认规则先问用户：上传文件、写文件、终端命令，以及“提交”（点发送 / 发布 / 付款这类按钮、在发消息的输入框里回车，
    动作之前让浏览器看一眼要点的元素，见 cdp_helper.INSPECT_JS）。返回 None 表示可以做，否则是给模型的话。"""
    from .. import approvals
    if name == "browser_upload":
        tool, shown = name, {"要上传的文件": args.get("paths"), "上传到": f"[{args.get('ref')}]"}
    elif name == "computer_write_file":
        tool, shown = name, {"文件": args.get("path"), "内容开头": str(args.get("content") or "")[:500]}
    elif name == "computer_shell":
        tool, shown = name, {"命令": args.get("cmd")}
    else:
        mode = "click" if name in ("browser_click", "computer_click") else None
        if name == "browser_type" and args.get("submit") or name == "browser_key" and str(args.get("key") or "").lower() in ENTER \
                or name == "computer_key" and str(args.get("keys") or "").replace(" ", "").lower().rpartition("+")[2] in ENTER:
            mode = "enter"
        if not mode or not approvals.decide("browser_submit", c.backend)[0]:
            return None
        try:
            info = await c.browser("inspect", key=key, mode=mode, ref=args.get("ref"), x=args.get("x"), y=args.get("y"))
        except ComputerError:
            return None   # 看不了就照常做：元素找不到的话，动作本身会报错
        if not info.get("submit"):
            return None
        tool, shown = "browser_submit", {"操作": info.get("what"), "页面": f"{info.get('title') or ''} | {info.get('url') or ''}"}
    if not approvals.decide(tool, c.backend, args if tool != "browser_submit" else shown,
                            background=bool(getattr(task, "background", False)), task_id=task.id)[0]:
        return None
    ok, note = await approvals.request(task, tool, shown)   # 终端：卡片上能“总是允许这个命令前缀”（approvals.resolve）
    if ok and tool == "computer_shell":
        approvals.shell_confirmed(task.id)   # 这个任务里后面的终端命令直接跑（B1）
    return None if ok else f"The user refused this action; it was not performed. {note}".strip()


async def call(task, name: str, args: dict, notify_progress, key: str = "") -> tuple[str, bytes | None]:
    """执行一个电脑工具，返回 (给模型的文字, 可选截图)。key 是谁在用：任务的 CLAIM，对话里直接操作的是 chat-<Bot id>。
    执行期间把进程说明挂在电脑上：等用户交还、等机器开起来的时候，任务卡片上看得见在等什么（见 base.wait_for_control）。"""
    c = get()
    prev, c.progress = getattr(c, "progress", None), notify_progress
    try:
        return await _call(task, c, name, args, notify_progress, key)
    finally:
        c.progress = prev


async def _call(task, c, name: str, args: dict, notify_progress, key: str = "") -> tuple[str, bytes | None]:
    from .. import approvals
    key = key or CLAIM.get() or str(task.id)
    if name in DESKTOP:
        await notify_progress(_progress_label(name, args))
        try:
            return await _desktop(task, c, name, args, key, notify_progress)
        except ComputerError as e:
            return f"Computer action failed: {e}", None
        except (TypeError, ValueError, KeyError) as e:
            return f"Bad arguments: {e}", None
    if name in WINDOW and not key.startswith("chat-"):
        await c.claim(key, _label(task, key), notify_progress,
                      {"task_id": task.id if isinstance(task.id, int) else None, "bot_id": task.bot_id})
    await notify_progress(_progress_label(name, args))
    try:
        if name == "browser_upload" and isinstance(args.get("paths"), str):
            args = {**args, "paths": [args["paths"]]}
        if name == "browser_upload":   # 先查文件在不在（本机电脑：在不在工作文件夹里），再问用户
            paths = c.upload_paths([str(x) for x in args.get("paths") or []][:10])
            if not paths:
                return "No file path to upload was given", None
        if refused := await _confirm(task, c, name, args, key):
            return refused, None
        if name == "browser_upload":
            await c.browser("upload", key=key, ref=args.get("ref"), files=[str(x) for x in paths][:10])
            return page_text(await c.browser("snapshot", key=key)), None
        if name in BROWSER:
            op = name.removeprefix("browser_")
            if op == "open" and not str(args.get("url", "")).startswith(("http://", "https://")):
                return i18n.t("只能打开 http / https 网址"), None
            kw = {k: v for k, v in args.items() if v is not None}
            if "key" in kw:   # browser_key 的按键名：key 这个名字 c.browser 自己要用（谁在操作）
                kw["name"] = kw.pop("key")
            return page_text(await c.browser(op, key=key, **kw)), None
        if name == "computer_screenshot":
            whole = bool(args.get("screen")) and c.backend not in HOSTS   # B4：Worker 也能看整个屏幕（和 look_at_screen 一样）
            if whole:
                png, title = await c.look()
                png = shot(png, "the whole screen", coords=False)
                what = f"This is a screenshot of the whole screen (active window: {title or 'unknown'}); it is for looking only"
            else:
                png = await c.page_shot(key)
                what = "This is a screenshot of the current page in the browser"
            if not args.get("save"):
                return what + ".", png
            path = f"screenshots/{'screen' if whole else 'page'} {time.strftime('%Y-%m-%d %H.%M.%S')}.png"
            await c.write_bytes(path if c.backend in HOSTS else f"{c.workspace}/{path}", png)
            return f"{what}, saved to {c.workspace}/{path} (use send_file to send it to the user).", png
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
            # 把这个任务的窗口放到最前面，用户一接手就看到；用户正在帮别的任务时不打扰，等他点这张卡片的“接手”。
            # 本机电脑不抢：你可能正在用别的程序，点卡片上的“接手电脑”时才放到前面
            if c.controller == "bot" and c.backend not in HOSTS:
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
            ok, note = await approvals.request(task, "ask_approval", {"操作": args["action"]}, once=True)   # 每一步都是它自己判断要问的
            return (f"The user approved. {note}".strip() if ok else f"The user refused; do not perform this action. {note}".strip()), None
        else:
            return i18n.t("未知的电脑工具"), None
    except ComputerError as e:
        return i18n.t("电脑操作失败：{error}", error=e), None
    snap = await c.page_shot(key) if name in AUTO_SHOT else None
    return text, snap


class Shot(bytes):
    """带说明的截图（整个屏幕的截图和浏览器页面的截图，给模型的说明不一样）。coords：能不能按它的坐标点击。"""
    caption = "screenshot of the current page"
    coords = True


def shot(png: bytes, caption: str, coords: bool = True) -> Shot:
    s = Shot(png)
    s.caption = caption
    s.coords = coords
    return s


# 屏幕上点了就发出去、花钱的按钮（比浏览器里那份少了“删除、确认、回复”：App 里到处都是，比如计算器的退格键就叫“删除”）
DESK_SUBMIT = re.compile(r"发送|发布|发表|提交|支付|付款|购买|下单|结算|转账"
                         r"|\b(send|post|publish|submit|pay|buy|order|checkout|transfer|tweet)\b", re.I)
SETTLE = {"desktop_open_app": 1.5}   # 动作之后等一会儿再截图，界面才变过来


def _desk_text(d: dict) -> str:
    f = d["front"]
    wins = "; ".join(f"{w['app']}" + (f" — {w['title']}" if w["title"] else "") for w in d["windows"]) or "none"
    return (f"Screenshot {d['width']}×{d['height']} (click coordinates use this size), mouse at ({d['cursor'][0]}, {d['cursor'][1]}). "
            f"Frontmost: {f['app'] or 'unknown'}" + (f" — {f['title']}" if f["title"] else "") + f". Windows on screen (front to back): {wins}")


async def _desktop(task, c, name: str, args: dict, key: str, notify_progress) -> tuple[str, bytes | None]:
    """整个屏幕的工具：占住屏幕（一次一个任务）→ 这个任务第一次用先问用户 → 点“发送”类按钮、在输入框里回车先问 → 做 → 截图。"""
    from .. import approvals
    if c.backend not in HOSTS or not c.desktop_enabled():
        return "This computer cannot operate the whole screen right now (it is not a Mac, or Open Super Agent has not been given the Accessibility and Screen Recording permissions); only the browser (browser_*) can be used.", None
    ok_key = key if key.startswith("chat-") else f"task:{task.id}"   # 同意按任务记：Heavy 的几个研究员只问一次
    no = ("The user did not allow you to operate the whole screen this time (they declined on the card). "
          "Use browser_* for whatever the browser can do; for what it cannot, say so in your result, and do not try desktop_* again in this task.")
    if time.time() - c.desk_denied.get(ok_key, 0) < 600:
        return no, None
    await c.desk_claim(key, _label(task, key), notify_progress)
    if not c.desk_allowed(ok_key):
        if approvals.decide("desktop", c.backend, {"任务": task.goal[:300]})[0]:
            ok, note = await approvals.request(task, "desktop", {"任务": task.goal[:300]})
            if not ok:
                c.desk_denied[ok_key] = time.time()
                await c.desk_release(key)
                return f"{no}{note}", None
        c.desk_ok[ok_key] = time.time()
    if name == "desktop_screenshot":
        d = await c.desk("screenshot", key)
        saved = ""
        if args.get("save"):
            path = f"screenshots/screen {time.strftime('%Y-%m-%d %H.%M.%S')}.png"
            await c.write_bytes(path, d["png"])
            saved = f"Screenshot saved in the working folder: {c.workspace}/{path} (use send_file to send it to the user). "
        return saved + _desk_text(d), shot(d["png"], "screenshot of the whole screen")
    what = ""   # 不为空：这一步像是发出去（点“发送”、在输入框里回车），先问用户
    if name == "desktop_click":
        x, y = int(args["x"]), int(args["y"])
        button = args.get("button") or "left"
        if button not in ("left", "right", "middle"):
            return "button must be left / right / middle", None
        el = await c.desk("inspect", key, x=x, y=y)
        label = el.get("label") or ""
        if button == "left" and len(label) <= 40 and DESK_SUBMIT.search(label):
            what = i18n.t("在「{app}」里点击「{label}」", app=el.get('app') or '?', label=label)
        op, kw = "click", {"x": x, "y": y, "button": button, "double": bool(args.get("double"))}
        done = f"Clicked ({x}, {y})" + (f" \"{label}\"" if label else "") + ". "
    elif name == "desktop_drag":
        op, kw, done = "drag", {k: int(args[k]) for k in ("x", "y", "to_x", "to_y")}, "Dragged. "
    elif name == "desktop_type":
        if not args.get("text"):
            return "No text to type", None
        op, kw, done = "type", {"text": str(args["text"])[:20000]}, "Typed. "
    elif name == "desktop_key":
        keys = str(args.get("keys") or "")
        if any(macdesk.parse_keys(k)[1] in ("enter", "return") for k in keys.split()):
            f = await c.desk("focused", key)
            if f.get("role") == "AXTextArea":   # 多行输入框（聊天软件、终端）里按回车，多半是发出去、执行
                what = i18n.t("在「{app}」的输入框里按 {keys}", app=f.get('app') or '?', keys=keys)
        op, kw, done = "key", {"keys": keys}, f"Pressed {keys}. "
    elif name == "desktop_scroll":
        op, kw = "scroll", {"x": int(args["x"]), "y": int(args["y"]), "direction": args.get("direction") or "down",
                            "amount": args.get("amount") or 3}
        done = "Scrolled. "
    elif name == "desktop_open_app":
        app = str(args.get("name") or "").strip()
        if not app:
            return "No app name was given", None
        op, kw, done = "open_app", {"name": app}, f"Opened {app}. "
    else:
        return "Unknown computer tool", None
    if what and approvals.decide("desktop_submit", c.backend, {"操作": what})[0]:
        ok, note = await approvals.request(task, "desktop_submit", {"操作": what})
        if not ok:
            return f"The user refused this action; it was not performed. {note}".strip(), None
    await c.desk(op, key, **kw)
    await asyncio.sleep(SETTLE.get(name, 0.6))
    d = await c.desk("screenshot", key)
    return done + _desk_text(d), shot(d["png"], "screenshot of the whole screen")


def image_message(png: bytes, caption: str | None = None, coords: bool | None = None) -> dict:
    caption = caption or getattr(png, "caption", "screenshot of the current page")
    coords = getattr(png, "coords", True) if coords is None else coords
    w, h = int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")   # PNG 头里的宽高
    tail = "click coordinates use this size" if coords else "for looking only; do not click coordinates on this image"
    return {"role": "user", "content": [
        {"type": "text", "text": f"(system image: {caption}, {w}x{h}, {tail})"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}}]}


def prune_images(msgs: list[dict], keep: int = 2, batch: int = 4) -> int:
    """只保留最近 keep 张截图，更早的换成文字，避免上下文越来越长。

    C18：要换就多攒几张一起换（到 keep + batch 张才动手）。每来一张新截图就换掉一张的话，前面已经发出去
    的消息每步都变，模型服务的缓存每一步都落空、整段重读；多留几张只多花几张图的 token。"""
    pics = [m for m in msgs
            if isinstance(m.get("content"), list) and any(p.get("type") == "image_url" for p in m["content"])]
    if len(pics) <= keep + batch:
        return 0
    for m in pics[:-keep] if keep else pics:
        m["content"] = "(an earlier screenshot was omitted)"
    return len(pics) - keep
