"""资料库：Bot 生成的页面（Pages），以及共用电脑里 /data/workspace 的文件。

页面存在数据库里，格式是 markdown 或 html。分享就是生成一个不可猜的链接 /s/<token>，取消分享后链接失效。
html 页面只通过带 CSP 的 /raw 地址在沙箱 iframe 里显示：脚本可以跑，但拿不到这个站点的任何数据，也连不上接口。
文件直接读写电脑里的目录，两个电脑后端都走 exec，所以要先开机。
"""

from .i18n import s as _s
import posixpath
import re
import secrets
import shlex
import time
from .memory import conn

conn.execute("""create table if not exists pages(
  id integer primary key, bot_id integer, title text, format text default 'markdown', content text,
  share_token text, pinned integer default 0, task_id integer, created real, updated real)""")
conn.execute("create unique index if not exists pages_token on pages(share_token)")
conn.execute("create table if not exists file_pins(path text primary key, ts real)")
conn.commit()

FORMATS = ("markdown", "html")
MAX_PAGE = 500_000
MAX_PAGES = 1000
WORKSPACE = "/data/workspace"
MAX_UPLOAD = 20 << 20
RAW_CSP = ("sandbox allow-scripts allow-popups; default-src 'none'; script-src 'unsafe-inline' https:; "
           "style-src 'unsafe-inline' https:; img-src https: data:; font-src https: data:; media-src https: data:; "
           "connect-src 'none'; frame-src 'none'; form-action 'none'")

_COLS = "id, bot_id, title, format, share_token, pinned, task_id, created, updated, length(content)"


# ---------- 页面 ----------
def _page(r, content: str | None = None) -> dict:
    i, bot_id, title, fmt, token, pinned, task_id, created, updated, size = r
    p = {"id": i, "bot_id": bot_id, "title": title, "format": fmt, "share_token": token, "pinned": bool(pinned),
         "task_id": task_id, "created": created, "updated": updated, "size": size or 0}
    if content is not None:
        p["content"] = content
    return p


def list_pages() -> list[dict]:
    return [_page(r) for r in conn.execute(f"select {_COLS} from pages order by pinned desc, updated desc")]


def get_page(pid: int, with_content: bool = True) -> dict | None:
    r = conn.execute(f"select {_COLS}, content from pages where id=?", (pid,)).fetchone()
    return _page(r[:-1], r[-1] if with_content else None) if r else None


def by_token(token: str) -> dict | None:
    if not token:
        return None
    r = conn.execute("select id from pages where share_token=?", (token,)).fetchone()
    return get_page(r[0]) if r else None


def save_page(bot_id: int | None, title: str, content: str, fmt: str = "markdown",
              pid: int | None = None, task_id: int | None = None) -> dict:
    """新建，或者给 pid 时更新内容。"""
    title = " ".join((title or "").split())[:120] or _s('audit_5a131f787f')
    fmt = fmt if fmt in FORMATS else "markdown"
    if not (content or "").strip():
        raise ValueError(_s('audit_c35f1f006d'))
    if len(content) > MAX_PAGE:
        raise ValueError(_s('audit_2a633e30c5', v0=MAX_PAGE // 1000))
    now = time.time()
    if pid is not None:
        if not get_page(pid, False):
            raise ValueError(_s('audit_896070b281', v0=pid))
        conn.execute("update pages set title=?, format=?, content=?, updated=? where id=?", (title, fmt, content, now, pid))
    else:
        if conn.execute("select count(*) from pages").fetchone()[0] >= MAX_PAGES:
            raise ValueError(_s('audit_a772e5de80', v0=MAX_PAGES))
        pid = conn.execute("insert into pages(bot_id, title, format, content, task_id, created, updated) "
                           "values(?,?,?,?,?,?,?)", (bot_id, title, fmt, content, task_id, now, now)).lastrowid
    conn.commit()
    return get_page(pid, False)


def update_page(pid: int, title: str | None = None, pinned: bool | None = None) -> dict:
    if not get_page(pid, False):
        raise ValueError(_s('audit_896070b281', v0=pid))
    if title is not None:
        conn.execute("update pages set title=?, updated=? where id=?",
                     (" ".join(title.split())[:120] or _s('audit_5a131f787f'), time.time(), pid))
    if pinned is not None:
        conn.execute("update pages set pinned=? where id=?", (int(pinned), pid))
    conn.commit()
    return get_page(pid, False)


def share(pid: int, on: bool) -> dict:
    """打开分享时生成新链接；关掉后旧链接立即失效。"""
    conn.execute("update pages set share_token=? where id=?", (secrets.token_urlsafe(16) if on else None, pid))
    conn.commit()
    return get_page(pid, False)


def delete_page(pid: int):
    conn.execute("delete from pages where id=?", (pid,))
    conn.commit()


def link(pid: int) -> str:
    """对话里引用页面用的地址，前端会在资料库里打开它。"""
    return f"/library/pages/{pid}"


SAVE_PAGE = {"type": "function", "function": {
    "name": "save_page",
    "description": _s('audit_c5b54a1584'),
    "parameters": {"type": "object", "properties": {
        "title": {"type": "string"},
        "content": {"type": "string", "description": _s('audit_c31bbaec66')},
        "format": {"type": "string", "enum": list(FORMATS)},
        "page_id": {"type": "integer", "description": _s('audit_b5e7a93523')}},
        "required": ["title", "content"]}}}


READ_PAGE = {"type": "function", "function": {
    "name": "read_page",
    "description": _s('audit_c145d983ac'),
    "parameters": {"type": "object", "properties": {"page_id": {"type": "integer"}}, "required": ["page_id"]}}}


def tool_read_page(args: dict, limit: int = 12000) -> str:
    from . import search
    p = get_page(args.get("page_id")) if isinstance(args.get("page_id"), int) else None
    if not p:
        return _s('audit_896070b281', v0=args.get('page_id'))
    text = search._plain(p["content"] or "", p["format"])
    if p["format"] == "html":
        text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()
    more = _s('audit_26fae562bf', v0=len(text) - limit) if len(text) > limit else ""
    return _s('audit_3f7076f9e6', v0=p['title'], v1=link(p['id']), v2=time.strftime('%Y-%m-%d', time.localtime(p['updated'])), v3=text[:limit], v4=more)


def tool_save_page(bot_id: int, args: dict, task_id: int | None = None) -> str:
    pid = args.get("page_id")
    if pid is not None and (not (old := get_page(pid, False)) or old["bot_id"] != bot_id):
        return _s('audit_404033d37b', v0=pid)
    try:
        p = save_page(bot_id, args.get("title", ""), args.get("content", ""), args.get("format") or "markdown",
                      args.get("page_id"), task_id)
    except (ValueError, TypeError) as e:
        return _s('audit_b480594004', v0=e)
    return _s('audit_9e6e9417f0', v0=p['id'], v1=p['title'], v2=link(p['id']))


# ---------- 文件 ----------
def norm(path: str | None) -> str:
    """把路径规范成 /data/workspace 下的绝对路径；跑出去就报错。"""
    p = (path or "").strip() or WORKSPACE
    if not p.startswith("/"):
        p = posixpath.join(WORKSPACE, p)
    p = posixpath.normpath(p)
    if p != WORKSPACE and not p.startswith(WORKSPACE + "/"):
        raise ValueError(_s('audit_93107ea8ff', v0=WORKSPACE))
    return p


def check_name(name: str) -> str:
    name = (name or "").strip()
    if not name or name in (".", "..") or "/" in name or "\0" in name or len(name) > 200:
        raise ValueError(_s('audit_8a643a21a4'))
    return name


async def list_dir(c, path: str) -> list[dict]:
    p = norm(path)
    q = shlex.quote(p)
    r = await c.exec(f"[ -d {q} ] || exit 3; find {q} -mindepth 1 -maxdepth 1 -printf '%y\\t%s\\t%T@\\t%f\\n' | head -n 1000", 30)
    if r.exit_code == 3:
        raise ValueError(_s('audit_90adcd5028'))
    if r.exit_code:
        raise ValueError((r.stderr or _s('audit_9ce69dc304')).strip()[:200])
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        kind, size, mtime, name = parts
        out.append({"name": name, "path": posixpath.join(p, name), "dir": kind == "d",
                    "size": int(size) if size.isdigit() else 0, "mtime": float(mtime or 0)})
    out.sort(key=lambda e: (not e["dir"], e["name"].lower()))
    return out


async def put_file(c, directory: str, name: str, data: bytes) -> dict:
    """把文件写进电脑里的目录。同名时自动加序号，不覆盖。"""
    d, name = norm(directory), check_name(name)
    if len(data) > MAX_UPLOAD:
        raise ValueError(_s('audit_1b52ebc0cc', v0=MAX_UPLOAD >> 20))
    try:
        existing = {e["name"] for e in await list_dir(c, d)}
    except ValueError:
        existing = set()   # 目录还不存在，写文件时会自动建
    stem, ext = posixpath.splitext(name)
    final, n = name, 1
    while final in existing:
        n += 1
        final = f"{stem} ({n}){ext}"
    path = posixpath.join(d, final)
    await c.write_bytes(path, data)
    return {"path": path, "name": final, "size": len(data)}


async def stat_many(c, paths: list[str]) -> dict[str, dict]:
    """置顶文件的现状（可能已经被删了）。"""
    if not paths:
        return {}
    qs = " ".join(shlex.quote(p) for p in paths)
    r = await c.exec(f"for f in {qs}; do [ -e \"$f\" ] && stat -c '%F\t%s\t%Y\t%n' \"$f\"; done; true", 30)
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            kind, size, mtime, name = parts
            out[name] = {"name": posixpath.basename(name), "path": name, "dir": kind == "directory",
                         "size": int(size) if size.isdigit() else 0, "mtime": float(mtime or 0)}
    return out


async def remove(c, path: str):
    p = norm(path)
    if p == WORKSPACE:
        raise ValueError(_s('audit_5a3c70545c'))
    r = await c.exec(f"rm -rf -- {shlex.quote(p)}", 60)
    if r.exit_code:
        raise ValueError((r.stderr or _s('audit_72250c5922')).strip()[:200])
    unpin(p)


def pins() -> list[str]:
    return [r[0] for r in conn.execute("select path from file_pins order by ts")]


def pin(path: str):
    conn.execute("insert or replace into file_pins values(?, ?)", (norm(path), time.time()))
    conn.commit()


def unpin(path: str):
    p = norm(path)
    conn.execute("delete from file_pins where path=? or path like ?", (p, p + "/%"))
    conn.commit()
