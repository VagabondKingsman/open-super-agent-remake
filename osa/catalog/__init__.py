"""应用市场的目录。

每个应用一份 YAML 清单，文件名就是应用名：
- osa/catalog/apps/<名字>.yaml：随项目发布。想让应用上架，加一份清单提 PR 就行
- data/apps/<名字>.yaml：只在这台机器上用，和内置的同名时覆盖内置的。适合先在本机试

格式见 docs/apps.md。清单改了不用重启，下次打开应用页就会重新读。`python -m osa.catalog` 检查所有清单。

connect 是连接配置的模板：字符串里的 {字段名} 换成用户填的值。secret 字段先存进保险库，
配置里只留 {vault:名字}，记在 owned 里，删除应用时一起删掉。
"""

from ..i18n import s as _s
import inspect
import json
import logging
import re
from pathlib import Path
import yaml
from ..config import ROOT
from . import checks

log = logging.getLogger(__name__)

BUILTIN = Path(__file__).parent / "apps"
LOCAL = ROOT / "data" / "apps"
# 和 mcp_hub.WORKSPACE 是同一个目录。不从那边导入：导入 mcp_hub 会打开数据库，检查清单用不着
WORKSPACE = ROOT / "data" / "workspace"

# 分类按这个顺序显示。要加新分类，改这里
CATEGORIES = {"notes": "笔记与文档", "mail": "邮件与日历", "files": "文件", "tasks": "任务与协作",
              "design": "设计", "dev": "开发", "web": "搜索与网页", "life": "生活"}
# 没有品牌图标时可以用的线条图标，图形在 web/src/appIcons.ts
GLYPHS = {"globe", "folder", "mail", "search", "train", "pin", "book", "doc", "feather", "plug",
          "chat", "hash", "package", "cloud", "palette", "table", "calendar", "check", "notebook"}

ID = re.compile(r"^[a-z][a-z0-9_-]{0,23}$")       # 文件名也是应用名，规则和 mcp_hub.NAME 一样
KEYS = {"title", "category", "order", "by", "icon", "desc", "about", "can", "example", "note", "how",
        "steps", "link", "link_label", "copy", "fields", "check", "deny", "confirm", "connect"}
FIELD_KEYS = {"key", "label", "placeholder", "default", "secret", "optional", "nospace", "pattern", "invalid"}
CONNECT_KEYS = {"type", "command", "args", "env", "url", "headers", "oauth"}
OAUTH_KEYS = {"client_id", "client_secret", "scope", "params"}
SLOT = re.compile(r"\{(\w+)\}")
COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
SVG_PATH = re.compile(r"^[MmZzLlHhVvCcSsQqTtAa0-9eE.,+\-\s]+$")

_cache: dict = {"sig": None, "items": {}, "errors": []}


# ---------- 读清单 ----------
def _files() -> dict[str, Path]:
    files = {}
    for d in (BUILTIN, LOCAL):
        if d.is_dir():
            for p in sorted(d.glob("*.yaml")):
                files[p.stem] = p       # 本机的同名清单覆盖内置的
    return files


def _show(p: Path) -> str:
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def load() -> tuple[dict[str, dict], list[str]]:
    """读所有清单，返回（应用名 -> 清单，有错的清单和原因）。文件都没变就用上次读的。"""
    files = _files()
    try:
        sig = tuple((str(p), p.stat().st_mtime_ns) for p in files.values())
    except OSError:                     # 读的时候正好有文件被删掉，下次再读
        sig = None
    if sig is None or sig != _cache["sig"]:
        items, errors = {}, []
        for name, p in files.items():
            try:
                items[name] = parse(name, yaml.safe_load(p.read_text("utf-8")))
            except yaml.MarkedYAMLError as e:
                mark = e.problem_mark or e.context_mark
                where = _s('audit_52ec21ea8f', v0=mark.line + 1) if mark else ""
                errors.append(_s('audit_09af940aea', v0=_show(p), v1=where, v2=e.problem or e.context))
            except (OSError, yaml.YAMLError, ValueError) as e:
                errors.append(f"{_show(p)}：{e}")
        rank = list(CATEGORIES)
        items = dict(sorted(items.items(), key=lambda kv: (rank.index(kv[1]["category"]), kv[1]["order"], kv[0])))
        for e in errors:
            log.warning(_s('audit_0349bedea2'), e)
        _cache.update(sig=sig, items=items, errors=errors)
    return _cache["items"], _cache["errors"]


def items() -> dict[str, dict]:
    return load()[0]


def parse(name: str, m) -> dict:
    """检查一份清单并补上默认值。有问题时 raise ValueError，一次列出所有问题。"""
    if not isinstance(m, dict):
        raise ValueError(_s('audit_d0fd26a99a'))
    bad: list[str] = []
    if not ID.match(name):
        bad.append(_s('audit_5b7716fd39'))
    bad += [_s('audit_fb2565cd26', v0=k) for k in m if k not in KEYS]

    def text(v, where: str, need=False):
        if v is None:
            if need:
                bad.append(_s('audit_5e6c7385e4', v0=where))
        elif not isinstance(v, str) or not v.strip():
            bad.append(_s('audit_63c67fe3e6', v0=where))

    def texts(v, where: str):
        if v is not None and (not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v)):
            bad.append(_s('audit_fc19620353', v0=where))

    for k in ("title", "by", "desc"):
        text(m.get(k), k, need=True)
    for k in ("about", "example", "note", "how", "link", "link_label"):
        text(m.get(k), k)
    for k in ("can", "steps", "deny"):
        texts(m.get(k), k)
    if m.get("category") not in CATEGORIES:
        bad.append(_s('audit_dd3bb89dfb', v0=', '.join(CATEGORIES)))
    if "order" in m and (type(m["order"]) is not int):
        bad.append(_s('audit_9325a8eb88'))
    cf = m.get("confirm", "auto")
    if cf not in ("auto", "all", "none") and not (isinstance(cf, list) and cf and all(isinstance(x, str) for x in cf)):
        bad.append(_s('audit_8436d082c8'))
    _check_icon(m.get("icon"), bad)
    cp = m.get("copy")
    if cp is not None and not (isinstance(cp, dict) and set(cp) == {"label", "text"}
                               and all(isinstance(v, str) and v.strip() for v in cp.values())):
        bad.append(_s('audit_a97105cf11'))
    fields = _check_fields(m.get("fields"), bad)
    keys = {f["key"] for f in fields}
    used = _check_connect(m.get("connect"), keys, bad)
    used |= _check_checks(m.get("check"), keys, bad)
    bad += [_s('audit_f8f62f9eca', v0=k) for k in sorted(keys - used)]

    o = m["connect"].get("oauth") if isinstance(m.get("connect"), dict) else None
    oauth = o is True or isinstance(o, dict)
    if bad:
        raise ValueError("；".join(bad))

    builtin = {"workspace": str(WORKSPACE)}
    return m | {
        "id": name, "order": m.get("order", 100), "confirm": m.get("confirm", "auto"),
        "kind": "oauth" if oauth else "token" if any(f.get("secret") for f in fields) else "none",
        "client": isinstance(o, dict) and "client_id" in o,     # 用户自己建的 OAuth 客户端：要告诉他回调地址
        "can": m.get("can") or [], "steps": m.get("steps") or [], "deny": m.get("deny") or [],
        "check": m.get("check") or {},
        "fields": [f | {"default": _fill(f["default"], builtin)} if "default" in f else f for f in fields],
    }


def _check_icon(ic, bad: list):
    if ic is None:
        return
    if not isinstance(ic, dict):
        bad.append(_s('audit_b0a0f585cd'))
        return
    bad += [_s('audit_b323721507', v0=k) for k in ic if k not in ("color", "svg", "glyph")]
    if not COLOR.match(str(ic.get("color") or "")):
        bad.append(_s('audit_e2405c6f5d'))
    if "svg" in ic and "glyph" in ic:
        bad.append(_s('audit_10f7374d8b'))
    if "svg" in ic and not (isinstance(ic["svg"], str) and SVG_PATH.match(ic["svg"])):
        bad.append(_s('audit_59d8aabf49'))
    if "glyph" in ic and ic["glyph"] not in GLYPHS:
        bad.append(_s('audit_70d2b187c9', v0=', '.join(sorted(GLYPHS))))


def _check_fields(fields, bad: list) -> list[dict]:
    if fields is None:
        return []
    if not isinstance(fields, list):
        bad.append(_s('audit_3e793a0450'))
        return []
    out, seen = [], set()
    for i, f in enumerate(fields, 1):
        where = _s('audit_3510286aae', v0=i)
        if not isinstance(f, dict):
            bad.append(_s('audit_d5cb9be0c5', v0=where))
            continue
        bad += [_s('audit_ccada1a457', v0=where, v1=k) for k in f if k not in FIELD_KEYS]
        k = f.get("key")
        if not isinstance(k, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", k):
            bad.append(_s('audit_455339dd71', v0=where))
            continue
        if k in seen:
            bad.append(_s('audit_562dc804ac', v0=where, v1=k))
        seen.add(k)
        if not isinstance(f.get("label"), str) or not f["label"].strip():
            bad.append(_s('audit_0976c3eed1', v0=where))
        for b in ("secret", "optional", "nospace"):
            if b in f and not isinstance(f[b], bool):
                bad.append(_s('audit_33cfad96d2', v0=where, v1=b))
        for s in ("placeholder", "default", "pattern", "invalid"):
            if s in f and not isinstance(f[s], str):
                bad.append(_s('audit_b0c8a151f2', v0=where, v1=s))
        if isinstance(f.get("pattern"), str):
            try:
                re.compile(f["pattern"])
            except re.error as e:
                bad.append(_s('audit_feda1b3d32', v0=where, v1=e))
        out.append(f)
    return out


def _slots(v) -> set[str]:
    return set(SLOT.findall(json.dumps(v, ensure_ascii=False)))


def _check_connect(c, keys: set, bad: list) -> set[str]:
    if not isinstance(c, dict):
        bad.append(_s('audit_04db7a0f8a'))
        return set()
    bad += [_s('audit_72e0e88292', v0=k) for k in c if k not in CONNECT_KEYS]

    def strmap(k):
        v = c.get(k)
        if v is not None and (not isinstance(v, dict) or not all(isinstance(x, str) for x in v.values())):
            bad.append(_s('audit_0045879fed', v0=k))

    t = c.get("type")
    if t == "stdio":
        if not isinstance(c.get("command"), str) or not c["command"].strip():
            bad.append(_s('audit_fc621b0d67'))
        if "args" in c and (not isinstance(c["args"], list) or not all(isinstance(x, str) for x in c["args"])):
            bad.append(_s('audit_26e87b2d28'))
        strmap("env")
        bad += [_s('audit_38ee899dd1', v0=k) for k in ("url", "headers", "oauth") if k in c]
    elif t in ("http", "sse"):
        # 整个地址也可以让用户填（飞书、企业微信的地址里带着授权）：写成 '{字段}'，字段里用 pattern 检查
        if not isinstance(c.get("url"), str) or not re.match(r"^(https?://|\{\w+\}$)", c["url"]):
            bad.append(_s('audit_d480651ec2', v0=t))
        strmap("headers")
        _check_oauth(c.get("oauth"), bad)
        bad += [_s('audit_cede355e1b', v0=k) for k in ("command", "args", "env") if k in c]
    else:
        bad.append(_s('audit_c04a9a6de5'))
    used = _slots(c)
    bad += [_s('audit_03896c7505', v0=s) for s in sorted(used - keys)]
    return used


def _check_oauth(o, bad: list):
    """oauth: true 用动态注册；写成一组键时可以带自己建的客户端（client_id、client_secret）、
    要申请的权限（scope，不写就按对方公布的全要）和授权页的额外参数（params）。"""
    if o is None or isinstance(o, bool):
        return
    if not isinstance(o, dict):
        bad.append(_s('audit_0d44f904f5'))
        return
    bad += [_s('audit_6b31d11d21', v0=k) for k in o if k not in OAUTH_KEYS]
    for k in ("client_id", "client_secret", "scope"):
        if k in o and (not isinstance(o[k], str) or not o[k].strip()):
            bad.append(_s('audit_7bb0e45006', v0=k))
    if "client_secret" in o and "client_id" not in o:
        bad.append(_s('audit_b181c624a5'))
    p = o.get("params")
    if p is not None and (not isinstance(p, dict) or not all(isinstance(x, str) for x in p.values())):
        bad.append(_s('audit_a17cb3fc9b'))


def _check_checks(ck, keys: set, bad: list) -> set[str]:
    if ck is None:
        return set()
    if not isinstance(ck, dict):
        bad.append(_s('audit_c5b3fdb689'))
        return set()
    used = set()
    for name, params in ck.items():
        fn = checks.CHECKS.get(name)
        if not fn:
            bad.append(_s('audit_d16d6f387a', v0=name, v1=', '.join(checks.CHECKS)))
            continue
        if not isinstance(params, dict):
            bad.append(_s('audit_f4e6686897', v0=name))
            continue
        ps = inspect.signature(fn).parameters
        bad += [_s('audit_bcc0ce8c5c', v0=name, v1=p) for p, v in ps.items() if v.default is v.empty and p not in params]
        bad += [_s('audit_5a3b40d17f', v0=name, v1=p) for p in params if p not in ps]
        used |= _slots(params)
    bad += [_s('audit_d9cebbbf49', v0=s) for s in sorted(used - keys)]
    return used




def _overlay_pack() -> dict:
    """Locale overlay for catalog titles/descriptions. YAML stays zh source."""
    import json
    from .. import i18n
    from pathlib import Path
    loc = i18n.get_locale()
    for candidate in (loc, "en"):
        path = Path(__file__).resolve().parent.parent / "locales" / candidate / "catalog.json"
        if path.exists():
            return json.loads(path.read_text())
    return {"categories": {}, "apps": {}}


def _apply_overlay(item: dict) -> dict:
    pack = _overlay_pack().get("apps", {}).get(item.get("id") or "", {})
    if not pack:
        return item
    out = dict(item)
    for k in ("title", "desc", "about", "example", "how", "note", "link_label", "by"):
        if pack.get(k):
            out[k] = pack[k]
    for k in ("can", "steps"):
        if pack.get(k):
            out[k] = pack[k]
    if pack.get("fields") and out.get("fields"):
        fields = []
        for f in out["fields"]:
            ff = dict(f)
            ov = pack["fields"].get(f.get("key"), {})
            for kk in ("label", "placeholder", "invalid"):
                if ov.get(kk):
                    ff[kk] = ov[kk]
            fields.append(ff)
        out["fields"] = fields
    if pack.get("copy") and out.get("copy"):
        out["copy"] = {**out["copy"], **pack["copy"]}
    return out

# ---------- 给前端和其他模块用 ----------
def public() -> list[dict]:
    out = []
    for it in items().values():
        o = {k: v for k, v in it.items() if k not in ("connect", "check", "order")}
        o["fields"] = [{k: v for k, v in f.items() if k not in ("pattern", "nospace")} for f in it["fields"]]
        o.setdefault("example", "")
        o.setdefault("about", "")
        o["remote"] = it["connect"]["type"] != "stdio"
        out.append(_apply_overlay(o))
    return out


def categories() -> list[list[str]]:
    """有应用的分类，按显示顺序：[[键, 名字], …]。"""
    used = {i["category"] for i in items().values()}
    names = _overlay_pack().get("categories") or CATEGORIES
    return [[k, names.get(k, CATEGORIES[k])] for k in CATEGORIES if k in used]


def title(name: str) -> str:
    from .. import mcp_hub
    a = mcp_hub.get(name) or {}
    i = items().get(a.get("catalog") or name)
    if not i:
        return "@" + name
    return _apply_overlay(i | {"id": i.get("id") or (a.get("catalog") or name)}).get("title") or i["title"]


def _fill(v, subst: dict):
    if isinstance(v, str):
        return SLOT.sub(lambda m: subst.get(m[1], m[0]), v)
    if isinstance(v, list):
        return [_fill(x, subst) for x in v]
    if isinstance(v, dict):
        return {k: _fill(x, subst) for k, x in v.items()}
    return v


def _values(it: dict, values: dict) -> dict:
    """检查用户填的内容，返回整理好的值（去掉首尾空格；nospace 的字段去掉所有空格）。"""
    vals = {}
    for f in it.get("fields", []):
        v = str(values.get(f["key"]) or f.get("default") or "").strip()
        if f.get("nospace"):
            v = re.sub(r"\s+", "", v)
        if not v and not f.get("optional"):
            raise ValueError(_s('audit_099a18004c', v0=f['label']))
        if v and f.get("pattern") and not re.search(f["pattern"], v):
            raise ValueError(f.get("invalid") or _s('audit_e9c32951b2', v0=f['label']))
        vals[f["key"]] = v
    return vals


async def check(item_id: str, values: dict):
    """添加前先按清单里的 check 试一下填的东西对不对，错了直接告诉用户，不用等应用连接失败。"""
    it = items().get(item_id) or {}
    if not it.get("check"):
        return
    vals = _values(it, values)
    for name, params in it["check"].items():
        await checks.CHECKS[name](**_fill(params, vals))


def build(item_id: str, values: dict) -> dict:
    """按清单里的模板生成应用配置。用户填的密钥存进保险库。"""
    from .. import vault
    it = items().get(item_id)
    if not it:
        raise ValueError(_s('audit_ee7f23896b'))
    vals = _values(it, values)
    subst, owned = {}, []
    for f in it["fields"]:
        v = vals[f["key"]]
        if f.get("secret") and v:
            ref = f"{item_id}_{f['key']}".upper().replace("-", "_")
            vault.put(ref, v)
            owned.append(ref)
            v = "{vault:" + ref + "}"
        subst[f["key"]] = v
    cfg = _fill(it["connect"], subst)
    return cfg | {"catalog": item_id, "deny": it["deny"], "confirm": it["confirm"], "owned": owned}
