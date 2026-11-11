"""群聊里谁说话：@ 谁轮到谁、交接插队、等任务结果时先跳过、一轮最多说几次、任务做完交给谁。

这里只测分配，不测模型：router.runtime 换成假的，记下轮到谁、带的是什么来由。
"""
from types import SimpleNamespace

import pytest
from conftest import find

from osa import bots, groups, i18n, router


@pytest.fixture
def rounds(monkeypatch):
    """把 router.runtime 换成假的：记下 (谁, 来由)，按剧本做事。"""
    log, plan = [], {}

    class FakeRouter:
        def __init__(self, bot_id):
            self.bot_id = bot_id

        async def respond(self, chat_id, turn=None):
            log.append((self.bot_id, turn))
            if act := plan.get(self.bot_id):
                await act(chat_id)

    monkeypatch.setattr(router, "runtime", lambda bot_id: FakeRouter(bot_id))
    return SimpleNamespace(log=log, plan=plan, said=lambda: [b for b, _ in log])


# ---------- 谁被 @ 到 ----------
def test_mentions_follow_the_order_of_the_at_signs(make_bot):
    nova, two, kim = make_bot("Nova"), make_bot("Nova Two"), make_bot("Kim")
    ids = [nova["id"], two["id"], kim["id"]]
    assert groups.mentions("@Kim chào @Nova", ids) == [kim["id"], nova["id"]]
    assert groups.mentions("@nova viết gì đó", ids) == [nova["id"]]        # 名字不分大小写
    assert groups.mentions("@Nova Two đây", ids) == [two["id"]]            # 长名字优先，不被 @Nova 抢走
    assert groups.mentions("@Nova2 đây", ids) == []                        # @Nova2 不是 @Nova
    assert groups.mentions("@everyone", ids) == ids
    assert groups.mentions("@所有人", ids) == ids
    assert groups.mentions("không nhắc ai", ids) == []


def test_only_a_message_from_the_user_makes_the_turn_theirs():
    turn = {"depth": 2, "via": "telegram"}
    assert groups.respond_turn("mention", turn) == {"depth": 2, "origin": "user"}
    assert groups.respond_turn("lead", turn) == {"depth": 2, "origin": "user"}
    assert groups.respond_turn("handoff", turn) == {"depth": 2}
    assert groups.respond_turn("dm", turn) is turn        # 私信引起的这一轮原样转交
    assert turn == {"depth": 2, "via": "telegram"}         # 不改传进来的 turn


# ---------- 一轮里轮着说 ----------
async def test_the_lead_answers_when_nobody_is_mentioned(make_bot, rounds):
    lead, other = make_bot("Lead"), make_bot("Other")
    g = bots.create_group([lead["id"], other["id"]], lead=lead["id"])
    await groups.on_user(bots.chat(g["id"]), "chào cả nhà")
    assert rounds.log == [(lead["id"], {"depth": 0, "origin": "user"})]
    rounds.log.clear()
    await groups.on_user(bots.chat(g["id"]), "@Other xem giúp việc này")
    assert rounds.log == [(other["id"], {"depth": 0, "origin": "user"})]


async def test_a_handoff_takes_the_floor_before_the_rest_of_the_queue(make_bot, rounds):
    planner, writer, checker = make_bot("Planner"), make_bot("Writer"), make_bot("Checker")
    g = bots.create_group([planner["id"], writer["id"], checker["id"]])
    rounds.plan[planner["id"]] = lambda chat_id: groups.handoff(chat_id, planner["id"], writer["id"], "viết tổng kết")

    await groups.get(g["id"]).run([(planner["id"], "lead"), (checker["id"], "mention")])

    assert rounds.said() == [planner["id"], writer["id"], checker["id"]]   # 交接的插到队首
    assert rounds.log[0][1]["origin"] == "user" and "origin" not in rounds.log[1][1]
    assert rounds.log[2][1]["origin"] == "user"      # 队列里原来的 @ 还是用户那一轮
    [h] = find(g["id"], kind="handoff")
    assert h["meta"]["to"] == writer["id"] and "viết tổng kết" in h["content"]


async def test_handing_to_the_same_bot_twice_speaks_once(make_bot, rounds):
    a, b = make_bot("Boss"), make_bot("Helper")
    g = bots.create_group([a["id"], b["id"]])

    async def twice(chat_id):
        await groups.handoff(chat_id, a["id"], b["id"], "việc một")
        await groups.handoff(chat_id, a["id"], b["id"], "việc hai")

    rounds.plan[a["id"]] = twice
    await groups.get(g["id"]).run([(a["id"], "lead")])
    assert rounds.said() == [a["id"], b["id"]]
    assert len(find(g["id"], kind="handoff")) == 2      # 两条交接记录，但只轮到他一次


async def test_a_bot_waiting_for_a_task_result_is_skipped_until_it_arrives(make_bot, rounds):
    a, b = make_bot("Asker"), make_bot("Busy")
    g = bots.create_group([a["id"], b["id"]])
    groups.expect(g["id"], b["id"])          # B 有任务在跑，做完会交给它
    try:
        await groups.get(g["id"]).run([(b["id"], "mention")])
        assert rounds.said() == []
    finally:
        groups.unexpect(g["id"], b["id"])
    await groups.get(g["id"]).run([(b["id"], "mention")])
    assert rounds.said() == [b["id"]]


async def test_a_round_of_bots_that_keep_talking_stops_at_the_limit(make_bot, rounds):
    a, b = make_bot("Looper"), make_bot("Echo")
    g = bots.create_group([a["id"], b["id"]])
    rounds.plan[a["id"]] = lambda chat_id: groups.handoff(chat_id, a["id"], b["id"], "tiếp đi")
    rounds.plan[b["id"]] = lambda chat_id: groups.handoff(chat_id, b["id"], a["id"], "tiếp đi")

    await groups.get(g["id"]).run([(a["id"], "lead")])

    assert len(rounds.said()) == groups.MAX_TURNS
    assert find(g["id"], text=i18n.t("Bot 们这一轮已经说了 {n} 次，先停一下，等你发话。", n=groups.MAX_TURNS))
    assert groups.get(g["id"]).handoffs == []          # 停下来以后不留尾巴给下一轮


async def test_a_bot_that_breaks_does_not_silence_the_others(make_bot, rounds, monkeypatch):
    a, b = make_bot("Broken"), make_bot("Steady")
    g = bots.create_group([a["id"], b["id"]])
    heard = []

    async def sink(event):
        heard.append(event)

    monkeypatch.setattr(groups, "notify", sink)

    async def boom(chat_id):
        raise RuntimeError("bùm")

    rounds.plan[a["id"]] = boom
    await groups.get(g["id"]).run([(a["id"], "mention"), (b["id"], "mention")])

    assert rounds.said() == [a["id"], b["id"]]
    [err] = [e for e in heard if e["type"] == "error"]
    assert "Broken" in err["message"] and err["chat_id"] == g["id"]


async def test_a_deleted_member_and_a_foreign_bot_are_skipped(make_bot, rounds):
    a, b, outsider = make_bot("Inside"), make_bot("Colleague"), make_bot("Outsider")
    g = bots.create_group([a["id"], b["id"]])
    await groups.get(g["id"]).run([(outsider["id"], "mention"), (a["id"], "mention")])
    assert rounds.said() == [a["id"]]


# ---------- 任务做完交接 ----------
def _task(chat_id: int, bot_id: int, to: int, *, status="done", depth=1, tid=4242, note="viết tổng kết"):
    return SimpleNamespace(chat_id=chat_id, bot_id=bot_id, status=status, depth=depth, id=tid,
                           handoff={"to": to, "note": note})


async def test_a_finished_task_hands_its_result_to_the_next_bot(make_bot, rounds):
    finder, writer = make_bot("Finder"), make_bot("Writer")
    g = bots.create_group([finder["id"], writer["id"]])
    groups.expect(g["id"], writer["id"])

    await groups.after_task(_task(g["id"], finder["id"], writer["id"]))

    assert rounds.log == [(writer["id"], {"depth": 2})]      # 接下来说话的那一轮比任务深一层
    [h] = find(g["id"], kind="handoff")
    assert h["meta"]["task_id"] == 4242 and "viết tổng kết" in h["content"]
    assert groups.get(g["id"]).expected.get(writer["id"], 0) == 0


async def test_a_task_that_failed_only_says_so(make_bot, rounds):
    finder, writer = make_bot("Finder"), make_bot("Writer")
    g = bots.create_group([finder["id"], writer["id"]])
    groups.expect(g["id"], writer["id"])

    await groups.after_task(_task(g["id"], finder["id"], writer["id"], status="failed", tid=4243))

    assert rounds.said() == []
    assert find(g["id"], text=i18n.t("任务 #{id} 没做完，没有交给 {name}", id=4243, name="Writer"))


async def test_a_chain_of_handed_tasks_stops_before_it_never_ends(make_bot, rounds):
    finder, writer = make_bot("Finder"), make_bot("Writer")
    g = bots.create_group([finder["id"], writer["id"]])
    groups.expect(g["id"], writer["id"])

    await groups.after_task(_task(g["id"], finder["id"], writer["id"], depth=groups.MAX_TURNS - 1))

    assert rounds.said() == []
    assert find(g["id"], text=i18n.t("Bot 们这一轮已经说了 {n} 次，先停一下，等你发话。", n=groups.MAX_TURNS))


async def test_a_reply_from_a_private_message_is_heard_in_the_group(make_bot, rounds):
    a, b = make_bot("Asker"), make_bot("Friend")
    g = bots.create_group([a["id"], b["id"]])
    turn = {"depth": 1, "origin": "user"}
    await groups.wake(g["id"], b["id"], turn)
    assert rounds.log == [(b["id"], turn)]
