"""OSA_COMPUTER_MOUNTS 在 Instabox 后端上的替身（OPEN-INSTABOX-REPO）。

Docker 后端用 `-v 宿主:容器` 真挂载；Instabox 是另一台机器，没有这条路，于是 Bot 在那边读不到
宿主上的仓库。这里把宿主目录打包、写进 VM、在那里解开，路径和 Docker 挂载一致。

按内容 sha 跳过没变的目录（on the VM 记一份清单），所以每次 start 不会把仓库重推一遍。
只读挂载（默认）在解包后 chmod -R a-w；目标目录归 root 就不是只读了，够用。
"""
import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path

from .base import ComputerError
from .local import mount_pairs

LIST = "/data/.osa-mounts.json"        # VM 里的清单：容器路径 -> sha，用来跳过没变的东西
SKIP = ("--exclude=.git", "--exclude=node_modules", "--exclude=__pycache__", "--exclude=.venv")


def _sha(path: str) -> str:
    """目录内容的指纹：路径 + mtime + 大小，不比字节，够快。"""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv"))
        for f in sorted(files):
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            h.update(f"{os.path.relpath(p, path)}:{int(st.st_mtime)}:{st.st_size}\n".encode())
    return h.hexdigest()[:16]


def _tar(path: str) -> bytes:
    """打包成 tar.gz（子进程，别把事件循环堵住）。"""
    out = subprocess.run(["tar", *SKIP, "-czf", "-", "-C", path, "."], capture_output=True)
    if out.returncode:
        raise ComputerError(f"tar {path} 失败：{out.stderr.decode()[:200]}")
    return out.stdout


async def deliver(c) -> list[str]:
    """把 OSA_COMPUTER_MOUNTS 里每个目录推到电脑上。返回这轮真推了的容器路径。"""
    pairs = mount_pairs()
    if not pairs:
        return []
    seen = {}
    try:
        raw = (await c.exec(f"cat {LIST} 2>/dev/null || true", timeout=20)).stdout
        seen = json.loads(raw) if raw.strip() else {}
    except Exception:  # noqa: BLE001 - 清单读不出来就当空的，重推一遍
        seen = {}
    pushed = []
    for host, dest, mode in pairs:
        sha = _sha(host)
        if seen.get(dest) == sha:
            continue
        data = await asyncio.to_thread(_tar, host)
        await c.write_bytes("/tmp/osa-push.tar.gz", data)
        script = (f"mkdir -p {dest} && tar -xzf /tmp/osa-push.tar.gz -C {dest} && rm -f /tmp/osa-push.tar.gz"
                  + (f" && chmod -R a-w {dest}" if mode == "ro" else ""))
        r = await c.exec(script, timeout=300)
        if r.exit_code:
            raise ComputerError(f"解开 {dest} 失败：{r.stderr[:200]}")
        seen[dest] = sha
        pushed.append(dest)
    if pushed:
        await c.write_bytes(LIST, json.dumps(seen).encode())
    return pushed
