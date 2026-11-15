"""派活时答应了“回来贴结果”，做完要把 Bot 自己叫醒接上。来由是 own_task：里面没有 from，
以前的代码先取 woke["from"]，于是每一轮都被 KeyError('from') 挡住，醒了又什么都没说。"""
from osa import router


def test_an_own_task_wake_needs_no_sender(make_bot):
    bot = make_bot("Wake")
    rt = router.Router(bot["id"])
    rt.turn = {"woke": {"kind": "own_task", "task": 7, "text": "[任务 #7 结果]\nxong"}}
    block = rt._turn_block()
    assert "result has landed" in block and "Do not repeat" in block


def test_a_dm_wake_still_names_the_sender(make_bot):
    sender = make_bot("Sender")
    bot = make_bot("Waked")
    rt = router.Router(bot["id"])
    rt.turn = {"woke": {"kind": "dm", "from": sender["id"], "text": "chào"}}
    assert "Sender" in rt._turn_block()


def test_a_deleted_sender_does_not_blow_up(make_bot):
    bot = make_bot("Alone")
    rt = router.Router(bot["id"])
    rt.turn = {"woke": {"kind": "dm", "from": 999999, "text": "chào"}}
    assert "deleted bot" in rt._turn_block()
