"""OPEN-INSTABOX-REPO: 宿主目录推到 Instabox 的那一半 —— 解析、打包、按 sha 跳过、只读。"""
import json
import os
import subprocess
from types import SimpleNamespace

import pytest

from osa.computer import push
from osa.computer.base import ExecResult


class FakeVM:
    """只记下写进去的文件和跑过的命令。"""
    def __init__(self, listing: str = ""):
        self.files, self.cmds, self.listing = {}, [], listing

    async def exec(self, cmd, timeout=120, stdin=None):
        self.cmds.append(cmd)
        if cmd.startswith("cat /data/.osa-mounts.json"):
            return ExecResult(0, self.listing, "")
        return ExecResult(0, "", "")

    async def write_bytes(self, path, data):
        self.files[path] = data


@pytest.fixture
def tree(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("print(1)")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref")
    monkeypatch.setenv("OSA_COMPUTER_MOUNTS", f"{tmp_path}:/data/repo")
    return tmp_path


async def test_a_mount_is_packed_and_unpacked_at_the_same_path(tree):
    vm = FakeVM()
    assert await push.deliver(vm) == ["/data/repo"]
    assert "/tmp/osa-push.tar.gz" in vm.files and vm.files["/tmp/osa-push.tar.gz"][:2] == b"\x1f\x8b"
    assert any("tar -xzf /tmp/osa-push.tar.gz -C /data/repo" in c for c in vm.cmds)
    assert any("chmod -R a-w /data/repo" in c for c in vm.cmds)          # 默认只读
    assert json.loads(vm.files["/data/.osa-mounts.json"])["/data/repo"]  # 记下了清单


async def test_an_unchanged_directory_is_skipped(tree):
    first = FakeVM()
    await push.deliver(first)
    sha = json.loads(first.files["/data/.osa-mounts.json"])["/data/repo"]
    second = FakeVM(listing=json.dumps({"/data/repo": sha}))
    assert await push.deliver(second) == [] and not second.files


async def test_a_changed_file_pushes_again(tree):
    first = FakeVM()
    await push.deliver(first)
    before = json.loads(first.files["/data/.osa-mounts.json"])
    (tree / "a.py").write_text("print(2)")
    os.utime(tree / "a.py", (1, 1))          # mtime 必须变：同一秒内改内容也只是 sha 变
    second = FakeVM(listing=json.dumps(before))
    assert await push.deliver(second) == ["/data/repo"]


async def test_rw_mount_is_not_made_read_only(tree, monkeypatch):
    monkeypatch.setenv("OSA_COMPUTER_MOUNTS", f"{tree}:/data/repo:rw")
    vm = FakeVM()
    await push.deliver(vm)
    assert not any("chmod -R a-w" in c for c in vm.cmds)


async def test_no_mounts_means_no_work(monkeypatch):
    monkeypatch.delenv("OSA_COMPUTER_MOUNTS", raising=False)
    vm = FakeVM()
    assert await push.deliver(vm) == [] and vm.cmds == []


def test_git_is_kept_out_of_the_tarball(tree):
    assert "--exclude=.git" in push.SKIP and "--exclude=node_modules" in push.SKIP
    names = subprocess.run(["tar", *push.SKIP, "-tzf", "-", "-C", str(tree), "."],
                           input=push._tar(str(tree)), capture_output=True).stdout.decode()
    assert "./a.py" in names and ".git/HEAD" not in names
