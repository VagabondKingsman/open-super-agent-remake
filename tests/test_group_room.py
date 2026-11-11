"""群里“谁在做什么”：@everyone 交给协调者、一轮有按钱和按秒的闸、工作清单看得见每个成员的任务、
成员旁边写着它会什么。线上 11/11 18:59 那条 @Mọi người 让 4 个 Bot 各发一条，就是这里要挡住的形状。"""
import pytest

from osa import bots, groups, memory, router, skills
from osa.config import CFG
from osa.worker import Task


@pytest.fixture
def fake(monkeypatch):
    """把 router.runtime 换成假的：每个假 Router 带一份 _turn_usage，可按剧本说话、交接。"""
    from types import SimpleNamespace
    log, plan = [], {}

    class Fake:
        def __init__(self, bid):
            self.bot_id, self._turn_usage = bid, {"cost": 0.0}

        async def respond(self, cid, turn=None):
            log.append((self.bot_id, turn))
            if act := plan.get(self.bot_id):
                await act(cid)

    monkeypatch.setattr(router, "runtime", lambda bid: Fake(bid))
    return SimpleNamespace(log=log, plan=plan, said=lambda: [b for b, _ in log])


async def test_everyone_goes_to_the_coordinator_only(make_bot, fake):
    lead, other = make_bot("Lead"), make_bot("Other")
    g = bots.create_group([lead["id"], other["id"]], lead=lead["id"])
    await groups.on_user(bots.chat(g["id"]), "@everyone xem giúp việc này")
    assert fake.said() == [lead["id"]]          # 只有协调者答，不是全群一起答
    assert fake.log[0][1]["origin"] == "user"
    assert groups.everyone_mentioned("@所有人") and groups.everyone_mentioned("@Everyone")
    assert not groups.everyone_mentioned("@Other")


async def test_the_coordinator_hands_out_the_rest_of_an_everyone(make_bot, fake):
    lead, a, b = make_bot("Coord"), make_bot("Writer"), make_bot("Runner")
    g = bots.create_group([lead["id"], a["id"], b["id"]], lead=lead["id"])

    async def hand_to_b(cid):
        await groups.handoff(cid, lead["id"], b["id"], "viết phần b")

    fake.plan[lead["id"]] = hand_to_b
    await groups.on_user(bots.chat(g["id"]), "@所有人 xem giúp")
    assert fake.said() == [lead["id"], b["id"]]        # 协调者先答，然后只轮到它交出去的那个
    assert fake.log[1][1] == {"depth": 0}


async def test_a_round_stops_when_it_costs_too_much(make_bot, fake, monkeypatch):
    monkeypatch.setitem(CFG["limits"], "group_round_usd", 0.02)
    a, b = make_bot("CostA"), make_bot("CostB")
    g = bots.create_group([a["id"], b["id"]], lead=a["id"])

    async def pricey(cid):
        self_id = fake.log[-1][0]
        await groups.handoff(cid, self_id, (b if self_id == a["id"] else a)["id"], "nữa")

    fake.plan[a["id"]] = pricey
    fake.plan[b["id"]] = pricey
    # 每一次开口都花 0.01：两轮之后就到了 0.02 的闸
    real = router.runtime

    def with_cost(bid):
        r = real(bid)
        orig = r.respond

        async def respond(cid, turn=None):
            r._turn_usage = {"cost": 0.01}
            await orig(cid, turn)

        r.respond = respond
        return r

    router.runtime = with_cost
    await groups.on_user(bots.chat(g["id"]), "chào cả nhà")
    assert len(fake.log) == 2, fake.log      # 第三次开口前停下
    assert any("已经用了" in (m["content"] or "") for m in memory.page(g["id"]))


def test_the_round_ceiling_reads_the_limits(monkeypatch):
    monkeypatch.setitem(CFG["limits"], "group_round_usd", 0.5)
    monkeypatch.setitem(CFG["limits"], "group_round_s", 0)
    g = groups.Group(1)
    assert not g._over(0.49, 0) and g._over(0.5, 0)
    monkeypatch.setitem(CFG["limits"], "group_round_usd", 0)
    assert not g._over(99.0, 0)              # 0 = 不限


def test_each_member_shows_what_it_can_do(make_bot):
    a, b = make_bot("Skilled"), make_bot("Plain")
    g = bots.create_group([a["id"], b["id"]], lead=a["id"])
    skills.save(a["id"], "viet-bai", "Viết bài tiếng Việt. Đủ dài.", "viết bài")
    block = router.Router(a["id"])._group_block(bots.chat(g["id"]))
    assert "viet-bai" in block                   # 我会什么，和我一起写在名单里
    assert "[skills:" not in block.split("- Plain: ")[1]


def test_the_ledger_shows_every_members_work_in_the_room(make_bot):
    a, b = make_bot("Lead2"), make_bot("Work2")
    g = bots.create_group([a["id"], b["id"]], lead=a["id"])
    r = router.Router(a["id"])
    r.chat = bots.chat(g["id"])
    t = Task(id=9311, goal="khảo sát metadata tool", bot_id=b["id"], chat_id=g["id"])
    router.TASKS[9311] = t
    try:
        ledger = r._group_ledger()
        assert "#9311" in ledger and "Work2" in ledger and "khảo sát metadata tool" in ledger
        assert "running" in ledger
    finally:
        router.TASKS.pop(9311, None)
    assert r._group_ledger() == ""           # 群里没有在跑的任务：不加这句
    r.chat = bots.chat(a["chat_id"])         # 私聊里没有“群里”这一说
    assert r._group_ledger() == ""
