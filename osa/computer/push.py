"""OSA_COMPUTER_MOUNTS 在 Instabox 后端上的替身（OPEN-INSTABOX-REPO）。

Docker 后端用 `-v 宿主:容器` 真挂载；Instabox 是另一台机器，没有这条路，于是 Bot 在那边读不到
宿主上的仓库，`.agents/` 得手抄过去。

这里按**文件**对齐：宿主上每个文件记 `mtime:size`，和目标机上的清单比，只传变了的、删掉多了的。
整个仓库一次 22 MB，而一次 exec 的 stdin 只装得下 1 MiB —— 一次一包会 400，所以早先的 tar 方案
其实没成过；按文件走之后每次只传改动那几行。只读挂载（默认）在收尾 `chmod -R a-w`。
"""
import asyncio
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

from .. import i18n
from .local import mount_pairs

LIST = "/data/.osa-mounts.json"        # 目标机上的清单：目录 -> {相对路径: "mtime:size"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache", "evals-out", "osa-data"}


def _files(root: str) -> dict[str, str]:
    """宿主目录下所有文件的相对路径 -> 指纹。"""
    out = {}
    base = Path(root)
    for dirpath, dirs, files in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir != ".":
            rel = Path(rel_dir).parts
            dirs[:] = [d for d in dirs if not (d.startswith(".") and d != ".agents") or d in ("", )]
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        else:
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            dirs[:] = dirs + [".agents"] if (base / ".agents").is_dir() else dirs
        for f in files:
            p = os.path.join(dirpath, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            out[os.path.relpath(p, root)] = _print(p, st)
    return out


def _print(p: str, st) -> str:
    """指纹。小文件按内容（同一秒里改同样长的内容是常事），大文件按 mtime+大小，不读整份。"""
    if st.st_size <= 2 << 20:
        with open(p, "rb") as fh:
            return hashlib.sha1(fh.read()).hexdigest()[:16]
    return f"{int(st.st_mtime)}:{st.st_size}"


def _sha(files: dict[str, str]) -> str:
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(f"{rel}:{files[rel]}\n".encode())
    return h.hexdigest()[:16]


SEED_DIR = "/data/home"          # VM 上以 user 身份跑，HOME=/data/home


def _token() -> str:
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not tok:
        try:
            tok = Path.home().joinpath(".nodecode/gh-token").read_text().strip()
        except OSError:
            tok = ""
    return tok


def _seed_files(token: str) -> dict[str, tuple[str, int]]:
    """给 VM 上的 git/gh 一份能用的凭据（路径 -> (内容, 权限)）。"""
    who = os.environ.get("OSA_GIT_IDENTITY") or "OSA Bot <osa@localhost>"
    name, _, mail = who.partition("<")
    name, mail = name.strip() or "OSA Bot", mail.rstrip("> ").strip() or "osa@localhost"
    cred = f"https://x-access-token:{token}@github.com\n"
    gitcfg = ("[credential \"https://github.com\"]\n"
              "\thelper = store --file " + SEED_DIR + "/.git-credentials\n"
              f"[user]\n\tname = {name}\n\temail = {mail}\n[init]\n\tdefaultBranch = main\n")
    hosts = ("github.com:\n"
             f"    oauth_token: {token}\n    git_protocol: https\n")
    return {
        f"{SEED_DIR}/.git-credentials": (cred, 0o600),
        f"{SEED_DIR}/.gitconfig": (gitcfg, 0o644),
        f"{SEED_DIR}/.config/gh/hosts.yml": (hosts, 0o600),
    }


async def seed(c) -> list[str]:
    """把宿主上的 GH 凭据写进电脑，Bot 才能在那边 clone/push 自己的改动。"""
    token = _token()
    if not token:
        return []
    files = _seed_files(token)
    stamp = hashlib.sha256(("".join(sorted(k + v[0] for k, v in files.items()))).encode()).hexdigest()[:16]
    try:
        raw = (await c.exec(f"cat {LIST} 2>/dev/null || true", timeout=20)).stdout
        seen: dict = json.loads(raw) if raw.strip() else {}
    except Exception:  # noqa: BLE001
        seen = {}
    if seen.get("@seed") == stamp:
        return []
    for path, (body, mode) in files.items():
        await c.write_bytes(path, body.encode())
        await c.exec(f"chmod {mode:o} {path}", timeout=20)
    seen["@seed"] = stamp
    await c.write_bytes(LIST, json.dumps(seen).encode())
    return ["git credentials"]


PART = 480 << 10              # 一段 tar.gz 的大小：一次 exec 的 stdin 装 1 MiB，base64 后仍留余量
PARTS = "/tmp/osa-push.tgz"


def _tar_bytes(host: str, rels: list[str]) -> bytes:
    """只把要传的那些文件打成一段 tar.gz。"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for rel in rels:
            full = os.path.join(host, rel)
            if os.path.isfile(full):
                tf.add(full, arcname=rel)
    return buf.getvalue()


async def _extract(c, host: str, rels: list[str], dest: str):
    """分批把文件送到目标机再一次性解开 —— 一个文件一个 exec 的话，仓库几千个文件要二十分钟。"""
    data = await asyncio.to_thread(_tar_bytes, host, rels)
    if not data:
        return
    parts = [data[i:i + PART] for i in range(0, len(data), PART)] or [data]
    names = [f"{PARTS}.{i:05d}" for i in range(len(parts))]
    for name, chunk in zip(names, parts):
        await c.write_bytes(name, chunk)
    # 先 mkdir + chmod u+w：只读挂载整棵树是 a-w 的，tar 直接写会被拒（Cannot open: File exists）
    r = await c.exec(f"mkdir -p {dest} && chmod u+w -R {dest} 2>/dev/null; "
                     f"cat {' '.join(names)} | tar -xzf - -C {dest} && rm -f {PARTS}.*", timeout=300)
    if r.exit_code:
        raise ValueError(i18n.t("解开 {dest} 失败：{error}", dest=dest, error=r.stderr[:200]))


async def deliver(c) -> list[str]:
    """让目标机的每个挂载点与宿主一致。返回这轮真动过的容器路径。"""
    pairs = mount_pairs()
    if not pairs:
        return []
    try:
        raw = (await c.exec(f"cat {LIST} 2>/dev/null || true", timeout=20)).stdout
        seen: dict = json.loads(raw) if raw.strip() else {}
    except Exception:  # noqa: BLE001 - 清单读不出来就当没有，重来一遍
        seen = {}
    touched = []
    for host, dest, mode in pairs:
        files = await asyncio.to_thread(_files, host)
        old = seen.get(dest) or {}
        if old == files:
            continue
        changed = sorted(k for k in files if old.get(k) != files[k])
        await _extract(c, host, changed, dest)
        gone = sorted(set(old) - set(files))
        for i in range(0, len(gone), 500):
            await c.exec("rm -f " + " ".join(f"{dest}/{r}" for r in gone[i:i + 500]), timeout=60)
        r = await c.exec(f"chmod {'a-w' if mode == 'ro' else 'u+w'} -R {dest}", timeout=180)
        if r.exit_code:
            raise ValueError(i18n.t("挂载 {dest} 权限没设好：{error}", dest=dest, error=r.stderr[:200]))
        seen[dest] = files
        touched.append(dest)
    if touched:
        await c.write_bytes(LIST, json.dumps(seen).encode())
    return touched
