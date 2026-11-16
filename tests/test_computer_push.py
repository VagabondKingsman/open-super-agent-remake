"""OPEN-INSTABOX-REPO: 宿主目录推到 Instabox 的那一半 —— 解析、只传改动、删掉多的、只读、分块。"""
import io
import json
import os
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
        if self.max_bytes and len(data) > self.max_bytes:
            raise RuntimeError("stdin is longer than 1048576 bytes")
        self.files[path] = data

    def tar_members(self) -> set[str]:
        """拼回写到 /tmp/osa-push.tgz.* 的那些段，列出里面真有的文件。"""
        import tarfile
        parts = [v for k, v in sorted(self.files.items()) if k.startswith(push.PARTS)]
        if not parts:
            return set()
        with tarfile.open(fileobj=__import__("io").BytesIO(b"".join(parts)), mode="r:gz") as tf:
            return {m.name for m in tf.getmembers() if m.isfile()}


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
    assert vm.tar_members() == {"a.py", "sub/b.txt", ".agents/BOARD.md"}
    assert any("tar -xzf - -C /data/repo" in c for c in vm.cmds)
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
    assert second.tar_members() == {"a.py"}                    # 没变的那个不重传


async def test_a_deleted_file_is_removed_on_the_far_side(tree):
    vm = FakeVM()
    await push.deliver(vm)
    manifest = vm.files["/data/.osa-mounts.json"].decode()
    (tree / "sub" / "b.txt").unlink()
    second = FakeVM(listing=manifest)
    await push.deliver(second)
    assert any("rm -f /data/repo/sub/b.txt" in c for c in second.cmds)


async def test_writable_before_extracting_so_read_only_trees_can_be_overwritten(tree):
    """只读挂载整棵树是 a-w 的：解包前必须先 chmod u+w，否则 tar 写不进已存在的文件。"""
    first = FakeVM()
    await push.deliver(first)
    (tree / "a.py").write_text("print(2)")
    second = FakeVM(listing=first.files["/data/.osa-mounts.json"].decode())
    await push.deliver(second)
    order = [i for i, c in enumerate(second.cmds) if "chmod u+w -R /data/repo" in c or "tar -xzf" in c]
    assert "chmod u+w" in second.cmds[order[0]] and "tar -xzf" in second.cmds[order[-1]]


async def test_rw_mount_is_left_writable(tree, monkeypatch):
    monkeypatch.setenv("OSA_COMPUTER_MOUNTS", f"{tree}:/data/repo:rw")
    vm = FakeVM()
    await push.deliver(vm)
    assert any("chmod u+w -R /data/repo" in c for c in vm.cmds)


async def test_no_mounts_means_no_work(monkeypatch):
    monkeypatch.delenv("OSA_COMPUTER_MOUNTS", raising=False)
    vm = FakeVM()
    assert await push.deliver(vm) == [] and vm.cmds == []


async def test_a_big_file_is_split_into_parts_under_the_limit(tree):
    """一次 exec 的 stdin 只装得下 1 MiB：大文件切成多段，不能让单次请求超限。"""
    (tree / "big.bin").write_bytes(os.urandom(3 << 20))      # 随机内容，压缩不掉
    vm = FakeVM(max_bytes=1 << 20)
    assert await push.deliver(vm) == ["/data/repo"]
    assert "big.bin" in vm.tar_members()
    assert len([k for k in vm.files if k.startswith(push.PARTS)]) > 1


async def test_whole_repo_does_not_cost_one_request_per_file(tree):
    """仓库几千个文件：每段 tar.gz 装一批，请求数远小于文件数。"""
    for i in range(300):
        (tree / "sub" / f"f{i}.txt").write_text("x" * 100)
    vm = FakeVM()
    await push.deliver(vm)
    assert len([c for c in vm.cmds if "tar -xzf" in c]) == 1
    assert len([k for k in vm.files if k.startswith(push.PARTS)]) < 40


async def test_credentials_are_written_for_the_vm(monkeypatch, tmp_path):
    monkeypatch.setenv("GH_TOKEN", "gho_test")
    monkeypatch.setattr(push.Path, "home", classmethod(lambda cls: tmp_path))
    vm = FakeVM()
    assert await push.seed(vm) == ["git credentials"]
    cred = vm.files[f"{push.SEED_DIR}/.git-credentials"].decode()
    assert "x-access-token:gho_test@github.com" in cred
    assert "store --file /data/home/.git-credentials" in vm.files[f"{push.SEED_DIR}/.gitconfig"].decode()
    assert "oauth_token: gho_test" in vm.files[f"{push.SEED_DIR}/.config/gh/hosts.yml"].decode()
    assert any("chmod 600 /data/home/.git-credentials" in c for c in vm.cmds)


async def test_credentials_are_not_rewritten_when_the_token_is_the_same(monkeypatch, tmp_path):
    monkeypatch.setenv("GH_TOKEN", "gho_test")
    monkeypatch.setattr(push.Path, "home", classmethod(lambda cls: tmp_path))
    first = FakeVM()
    await push.seed(first)
    assert await push.seed(FakeVM(listing=first.files["/data/.osa-mounts.json"].decode())) == []
    monkeypatch.setenv("GH_TOKEN", "gho_other")
    assert await push.seed(FakeVM(listing=first.files["/data/.osa-mounts.json"].decode())) == ["git credentials"]


async def test_no_token_means_no_seeding(monkeypatch, tmp_path):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(push.Path, "home", classmethod(lambda cls: tmp_path))
    vm = FakeVM()
    assert await push.seed(vm) == [] and vm.files == {}
