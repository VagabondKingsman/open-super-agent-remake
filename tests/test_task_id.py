"""OPEN-TASK-ID: 任务号不借消息 id，删 Bot / 清对话之后新任务不顶掉还在跑的老任务。"""
from osa import router
from osa.worker import Task


def test_task_ids_are_their_own_sequence():
    router.TASKS.clear()
    router._task_seq = 0
    assert router.task_id(1610) == 1
    assert router.task_id(1610) == 2          # 同一个消息 id 也不撞
    assert router.task_id(7) == 3


def test_a_live_task_is_never_overwritten(monkeypatch):
    router.TASKS.clear()
    router._task_seq = 0
    first = router.task_id()
    router.TASKS[first] = Task(id=first, goal="cũ")
    second = router.task_id()
    assert second != first and router.TASKS[first].goal == "cũ"


def test_the_number_skips_anything_already_there():
    router.TASKS.clear()
    router._task_seq = 0
    router.TASKS[1] = Task(id=1, goal="đã có")
    assert router.task_id() == 2
