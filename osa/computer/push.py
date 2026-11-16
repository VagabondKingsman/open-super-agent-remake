"""OSA_COMPUTER_MOUNTS 在 Instabox 后端上的替身（OPEN-INSTABOX-REPO）。

Docker 后端用 `-v 宿主:容器` 真挂载；Instabox 是另一台机器，没有这条路，于是 Bot 在那边读不到
宿主上的仓库，`.agents/` 得手抄过去。

这里按**文件**对齐：宿主上每个文件记 `mtime:size`，和目标机上的清单比，只传变了的、删掉多了的。
整个仓库一次 22 MB，而一次 exec 的 stdin 只装得下 1 MiB —— 一次一包会 400，所以早先的 tar 方案
其实没成过；按文件走之后每次只传改动那几行。只读挂载（默认）在收尾 `chmod -R a-w`。
"""
import hashlib
import json
import os
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
        files = _files(host)
        old = seen.get(dest) or {}
        if old == files:
            continue
        for rel in sorted(k for k in files if old.get(k) != files[k]):
            with open(os.path.join(host, rel), "rb") as fh:
                data = fh.read()
            await c.write_bytes(os.path.join(dest, rel), data)
        gone = sorted(set(old) - set(files))
        if gone:
            script = "rm -f " + " ".join(f"{dest}/{r}" for r in gone)
            if len(script) > 90_000:      # 一次命令行装不下就分批
                for i in range(0, len(gone), 500):
                    batch = "rm -f " + " ".join(f"{dest}/{r}" for r in gone[i:i + 500])
                    await c.exec(batch, timeout=60)
            else:
                await c.exec(script, timeout=60)
        r = await c.exec(f"chmod {'a-w' if mode == 'ro' else 'u+w'} -R {dest}", timeout=120)
        if r.exit_code:
            raise ValueError(i18n.t("挂载 {dest} 权限没设好：{error}", dest=dest, error=r.stderr[:200]))
        seen[dest] = files
        touched.append(dest)
    if touched:
        await c.write_bytes(LIST, json.dumps(seen).encode())
    return touched
