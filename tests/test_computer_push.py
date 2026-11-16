"""OPEN-INSTABOX-REPO: 宿主目录推到 Instabox 的那一半 —— 解析、只传改动、删掉多的、只读、分块。"""
import json
from types import SimpleNamespace

import pytest

from osa.computer import push
from osa.computer.base import ExecResult


class FakeVM:
    """只记下写进去的文件和跑过的命令。写得下多大由 max_bytes 定（真实 exec 的 stdin 上限 1 MiB）。"""
    def __init__(self, listing: str = "", max_bytes: int = 0):
        self.files, self.cmds, self.listing, self.max_bytes = {}, [], listing, max_bytes

    async def exec(self, cmd, timeout=120, stdin=None):
        if self.max_bytes and stdin and len(stdin) > self.max_bytes:
            return ExecResult(1, "", "stdin is longer than 1048576 bytes")
        self.cmds.append(cmd)
        if cmd.startswith("cat /data/.osa-mounts.json"):
            return ExecResult(0, self.listing, "")
        return ExecResult(0, "", "")

    async def write_bytes(self, path, data):
        self.files[path] = data


@pytest.fixture
def tree(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("print(1)")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("hello")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref")
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "BOARD.md").write_text("việc mở")
    monkeypatch.setenv("OSA_COMPUTER_MOUNTS", f"{tmp_path}:/data/repo")
    return tmp_path


def _manifest(vm) -> dict:
    return json.loads(vm.files["/data/.osa-mounts.json"])["/data/repo"]


async def test_files_are_written_at_the_same_paths(tree):
    vm = FakeVM()
    assert await push.deliver(vm) == ["/data/repo"]
    assert vm.files["/data/repo/a.py"] == b"print(1)"
    assert vm.files["/data/repo/sub/b.txt"] == b"hello"
    assert vm.files["/data/repo/.agents/BOARD.md"] == "việc mở".encode()
    assert any("chmod a-w -R /data/repo" in c for c in vm.cmds)          # 默认只读
    assert ".git/HEAD" not in _manifest(vm)


async def test_git_and_caches_are_kept_out(tree):
    vm = FakeVM()
    await push.deliver(vm)
    assert not any("/.git/" in p for p in vm.files)
    assert ".git/HEAD" not in _manifest(vm)


async def test_nothing_changed_means_no_work(tree):
    first = FakeVM()
    await push.deliver(first)
    assert await push.deliver(FakeVM(listing=first.files["/data/.osa-mounts.json"].decode())) == []


async def test_a_changed_file_is_pushed_alone(tree):
    first = FakeVM()
    await push.deliver(first)
    (tree / "a.py").write_text("print(2)")
    second = FakeVM(listing=first.files["/data/.osa-mounts.json"].decode())
    await push.deliver(second)
    assert second.files["/data/repo/a.py"] == b"print(2)"
    assert "/data/repo/sub/b.txt" not in second.files          # 没变的那个不重传


async def test_a_deleted_file_is_removed_on_the_far_side(tree):
    vm = FakeVM()
    await push.deliver(vm)
    manifest = vm.files["/data/.osa-mounts.json"].decode()
    (tree / "sub" / "b.txt").unlink()
    second = FakeVM(listing=manifest)
    await push.deliver(second)
    assert any("rm -f /data/repo/sub/b.txt" in c for c in second.cmds)


async def test_rw_mount_is_left_writable(tree, monkeypatch):
    monkeypatch.setenv("OSA_COMPUTER_MOUNTS", f"{tree}:/data/repo:rw")
    vm = FakeVM()
    await push.deliver(vm)
    assert any("chmod u+w -R /data/repo" in c for c in vm.cmds)


async def test_no_mounts_means_no_work(monkeypatch):
    monkeypatch.delenv("OSA_COMPUTER_MOUNTS", raising=False)
    vm = FakeVM()
    assert await push.deliver(vm) == [] and vm.cmds == []


async def test_a_big_file_still_goes_through_a_one_megabyte_exec(tree):
    """一次 exec 的 stdin 只装得下 1 MiB：分块在 write_bytes 里，push 只负责按文件调它。"""
    (tree / "big.bin").write_bytes(b"x" * (2 << 20))
    vm = FakeVM(max_bytes=1 << 20)
    assert await push.deliver(vm) == ["/data/repo"]
    assert vm.files["/data/repo/big.bin"] == b"x" * (2 << 20)
