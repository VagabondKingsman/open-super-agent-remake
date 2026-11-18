"""A tool step that goes silent must cost that step, not the task.

Nova, 2026-11-18: a computer_shell step ran 926 s with no progress signal, the
watchdog read that as "no progress" and cancelled the whole task. Two changes
are tested here: a per-step ceiling that fires only on silence, and a progress
report that counts as a sign of life.
"""
import asyncio
import inspect
import time

from osa import clock, worker


def _task():
    return worker.Task(id=1, goal="probe")


def test_a_silent_tool_is_abandoned_and_a_talking_one_is_waited_out():
    async def body():
        # silent: nothing refreshes last_progress, so the ceiling fires
        silent_task = _task()
        silent_task.last_progress = clock.now() - 5

        async def silent():
            await asyncio.sleep(5)

        started = time.monotonic()
        try:
            await worker._run_with_ceiling(silent_task, silent(), 0.2)
        except asyncio.TimeoutError:
            pass
        else:
            raise AssertionError("a silent tool was not abandoned")
        assert time.monotonic() - started < 3, "the ceiling did not fire promptly"

        # talking: the tool keeps refreshing last_progress, so it is waited out
        talking_task = _task()

        async def talking():
            for _ in range(8):
                talking_task.last_progress = clock.now()
                await asyncio.sleep(0.05)
            return "finished"

        assert await worker._run_with_ceiling(talking_task, talking(), 0.2) == "finished"

    asyncio.run(body())


def test_zero_means_no_ceiling():
    async def body():
        task = _task()
        task.last_progress = clock.now() - 100

        async def slow():
            await asyncio.sleep(0.2)
            return "ok"

        assert await worker._run_with_ceiling(task, slow(), 0) == "ok"

    asyncio.run(body())


def test_the_ceiling_reads_config(monkeypatch):
    monkeypatch.setitem(worker.CFG["limits"], "tool_timeout_s", 42)
    assert worker.tool_timeout_s() == 42
    monkeypatch.setitem(worker.CFG["limits"], "tool_timeout_s", 0)
    assert worker.tool_timeout_s() == 0


def test_a_progress_report_counts_as_life():
    """The whole point: a tool that is talking must keep the task alive."""
    assert "task.last_progress = clock.now()" in inspect.getsource(worker._run_calls)


def test_a_running_task_names_its_tool():
    task = _task()
    task.tool_name, task.tool_started = "computer_shell", clock.now()
    public = task.public()
    assert public["tool"] == "computer_shell"
    assert public["tool_s"] >= 0
