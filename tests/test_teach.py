"""演示一遍：录到的操作排成步骤、模型整理的技能草稿、录制时独占电脑、结束以后交还。"""
import time

import pytest
from conftest import until
from fakellm import Reply

from osa import computer, i18n, teach


class FakeComputer:
    """冒充电脑：记下录制的开始和结束，别的照做。"""

    backend = "local"

    def __init__(self, events=None):
        self.users, self.exclusive = {}, None
        self.events = events or []
        self.done = []
        self.taken = False
        self.rec = None

    def busy(self):
        return "Bot đang dùng"

    async def start(self):
        self.done.append("start")

    async def claim_exclusive(self, key, label):
        self.exclusive, self.label = key, label
        self.done.append(("claim", key))

    async def release(self, key):
        self.exclusive = None
        self.done.append(("release", key))

    async def browser(self, op, *, as_human=False, **args):
        self.done.append((op, args.get("file")))
        if op == "rec_start":
            self.rec = args.get("file")
            return {"ok": True}
        return {"events": self.events}

    def takeover(self):
        self.taken = True

    def handback(self):
        self.taken = False
        self.done.append("handback")

    async def show(self):
        self.done.append("show")


@pytest.fixture
def puter(monkeypatch):
    def make(events=None):
        c = FakeComputer(events)
        monkeypatch.setattr(computer, "get", lambda *a, **k: c)
        return c
    return make


@pytest.fixture(autouse=True)
def no_recording():
    yield
    if teach._timer:
        teach._timer.cancel()
    teach.state, teach._timer, teach.notify = None, None, None


# ---------- 录到的操作排成文字 ----------
def test_a_demo_becomes_one_line_per_step():
    t0 = 1000.0
    events = [
        {"type": "navigate", "t": t0, "url": "https://shop.vn/", "title": "Shop", "start": True},
        {"type": "click", "t": t0 + 3, "kind": "按钮", "name": "Tìm vé", "url": "https://shop.vn/"},
        {"type": "input", "t": t0 + 5, "field": "Điểm đi", "value": "Hà Nội", "url": "https://shop.vn/"},
        {"type": "input", "t": t0 + 6, "field": "Điểm đi", "value": "Hà Nội", "submit": True,
         "url": "https://shop.vn/"},
        {"type": "navigate", "t": t0 + 7, "url": "https://shop.vn/ketqua", "title": "Kết quả"},
        {"type": "navigate", "t": t0 + 8, "url": "https://shop.vn/ketqua"},   # 连着打开同一个网址：只留一次
    ]
    lines = teach.describe(events, t0)
    assert len(lines) == 4
    assert lines[0] == "00:00 " + i18n.t("开始时在 {url}", url="https://shop.vn/") + i18n.t("（{title}）", title="Shop")
    assert lines[1] == "00:03 " + i18n.t("点击 {kind}「{name}」", kind="按钮", name="Tìm vé")
    # 同一个输入框记了两次（回车前、回车时）：只留最后一次，带上“然后按回车”
    assert lines[2] == "00:06 " + i18n.t("在「{field}」输入「{value}」", field="Điểm đi", value="Hà Nội") \
        + i18n.t("，然后按回车")
    assert lines[3].startswith("00:07 ") and "ketqua" in lines[3]


def test_a_password_and_a_way_to_another_site_are_marked():
    t0 = 2000.0
    events = [
        {"type": "navigate", "t": t0, "url": "https://bank.vn/login", "start": True},
        {"type": "input", "t": t0 + 1, "field": "Mật khẩu", "value": "******", "secret": True,
         "url": "https://bank.vn/login"},
        {"type": "select", "t": t0 + 2, "field": "Chi nhánh", "value": "Hà Nội", "url": "https://bank.vn/login"},
        {"type": "check", "t": t0 + 3, "field": "Nhớ tài khoản", "checked": True, "url": "https://bank.vn/login"},
        {"type": "key", "t": t0 + 4, "key": "Enter", "url": "https://bank.vn/login"},
        {"type": "click", "t": t0 + 5, "kind": "链接", "name": "Trợ giúp", "url": "https://help.bank.vn/faq"},
    ]
    lines = teach.describe(events, t0)
    assert lines[1].endswith(i18n.t("（密码类，没有记录内容）"))
    assert lines[2] == "00:02 " + i18n.t("在「{field}」选择「{value}」", field="Chi nhánh", value="Hà Nội")
    assert lines[3] == "00:03 " + i18n.t("勾选「{field}」", field="Nhớ tài khoản")
    assert lines[4] == "00:04 " + i18n.t("按 {key}", key="Enter")
    assert lines[5].endswith(i18n.t("（在 {site}）", site="help.bank.vn"))   # 跳到另一个网站时注明


def test_a_very_long_demo_keeps_the_last_three_hundred_steps():
    t0 = 3000.0
    events = [{"type": "click", "t": t0 + i, "kind": "按钮", "name": f"nút {i}"} for i in range(400)]
    lines = teach.describe(events, t0)
    assert len(lines) == 300 and "nút 100" in lines[0] and "nút 399" in lines[-1]


def test_recorded_events_nobody_understands_are_left_out():
    assert teach.describe([{"type": "scroll", "t": 1}, {"type": "focus", "t": 2}], 1) == []


# ---------- 模型整理的草稿 ----------
def test_json_wrapped_in_a_code_block_or_prose_is_read():
    assert teach._parse('```json\n{"name": "a", "body": "b"}\n```') == {"name": "a", "body": "b"}
    assert teach._parse('好的，草稿是 {"name": "a", "body": "b"} 就这样') == {"name": "a", "body": "b"}
    assert teach._parse("完全不是 JSON") == {}
    assert teach._parse('["name", "a"]') == {}          # 不是对象


async def test_the_model_turns_the_trace_into_a_skill(llm):
    llm.script("other", Reply('{"name":"dat-ve-tau","description":"Khi cần đặt vé tàu","body":"1. Mở shop.vn"}'))
    d = await teach.draft_skill(["00:00 开始时在 https://shop.vn/"])
    assert d == {"name": "dat-ve-tau", "description": "Khi cần đặt vé tàu", "body": "1. Mở shop.vn"}
    sent = llm.bodies("other")[-1]
    assert "https://shop.vn/" in sent["messages"][-1]["content"]


async def test_a_draft_without_a_method_is_asked_once_more(llm):
    llm.script("other", Reply('{"name":"x"}'), Reply('{"name":"x","description":"d","body":"Bước 1"}'))
    d = await teach.draft_skill(["00:00 bước"])
    assert d["body"] == "Bước 1"
    assert len(llm.bodies("other")) == 2


async def test_a_model_that_says_nothing_still_gives_the_recorded_steps(llm):
    llm.script("other", Reply("không biết"), Reply("cũng không"))
    steps = ["00:00 开始时在 https://shop.vn/", "00:03 点击 按钮「Mua」"]
    d = await teach.draft_skill(steps, note="mua vé")
    assert d["name"].startswith(i18n.t("演示{time}", time="")[:2])
    assert d["description"] == "mua vé"
    assert d["body"] == i18n.t("按下面录到的步骤做：") + "\n" + "\n".join(steps)


# ---------- 录制的时候独占电脑 ----------
async def test_starting_a_demo_takes_the_computer(make_bot, puter):
    b = make_bot("Teacher")
    c = puter()
    pub = await teach.start(b["id"], "  đặt vé tàu  ")
    assert pub["bot_id"] == b["id"] and pub["note"] == "đặt vé tàu" and pub["max_s"] == teach.MAX_S
    assert c.exclusive == teach.KEY and c.taken
    assert ("rec_start", c.rec) in c.done and c.done[0] == "start"
    assert teach.public() == pub
    with pytest.raises(ValueError) as e:
        await teach.start(b["id"])
    assert str(e.value) == i18n.t("已经在录制了，先结束上一段")


async def test_a_busy_computer_waits_its_turn(make_bot, puter):
    c = puter()
    c.exclusive = "task-7"
    with pytest.raises(ValueError) as e:
        await teach.start(make_bot("Teacher")["id"])
    assert "Bot đang dùng" in str(e.value)
    assert c.exclusive == "task-7" and teach.public() is None


async def test_a_recorder_that_will_not_start_gives_the_computer_back(make_bot, puter):
    c = puter()

    async def broken(op, **kw):
        raise RuntimeError("không mở được")

    c.browser = broken
    with pytest.raises(RuntimeError):
        await teach.start(make_bot("Teacher")["id"])
    assert c.exclusive is None and teach.public() is None


# ---------- 结束 ----------
async def test_stopping_the_demo_hands_the_computer_back_and_writes_a_draft(make_bot, puter, llm):
    b = make_bot("Teacher")
    c = puter([{"type": "navigate", "url": "https://shop.vn/", "start": True},
               {"type": "click", "kind": "按钮", "name": "Mua"}])
    llm.script("other", Reply('{"name":"mua-ve","description":"Khi mua vé","body":"Mở shop.vn rồi bấm Mua"}'))
    await teach.start(b["id"])

    result = await teach.stop()

    assert result["bot_id"] == b["id"] and result["draft"]["name"] == "mua-ve"
    assert len(result["steps"]) == 2 and "Mua" in result["steps"][1]
    assert c.exclusive is None and c.taken is False and "handback" in c.done
    assert teach.public() is None
    with pytest.raises(ValueError) as e:
        await teach.stop()
    assert str(e.value) == i18n.t("现在没有在录制")


async def test_a_demo_with_nothing_recorded_is_not_a_skill(make_bot, puter, llm):
    c = puter([])
    await teach.start(make_bot("Teacher")["id"])
    with pytest.raises(ValueError) as e:
        await teach.stop()
    assert str(e.value).startswith(i18n.t("没录到浏览器里的操作。录制只记网页上的点击、输入和打开的网址")[:10])
    assert c.exclusive is None and teach.public() is None
    assert llm.bodies("other") == []          # 没有步骤就不去问模型


async def test_cancelling_a_demo_just_stops_it(make_bot, puter, llm):
    c = puter([{"type": "click", "kind": "按钮", "name": "Mua"}])
    await teach.start(make_bot("Teacher")["id"])
    await teach.cancel()
    assert c.exclusive is None and teach.public() is None
    assert llm.bodies("other") == []          # 取消不生成草稿


async def test_a_demo_left_running_stops_itself_and_reports_the_draft(make_bot, puter, llm, monkeypatch):
    monkeypatch.setattr(teach, "MAX_S", 0.05)
    heard = []

    async def sink(event):
        heard.append(event)

    async def state(pc):
        return {"users": []}

    monkeypatch.setattr(teach, "notify", sink)
    monkeypatch.setattr(computer, "public_state", state)
    c = puter([{"type": "navigate", "url": "https://shop.vn/", "start": True}])
    llm.script("other", Reply('{"name":"x","body":"b"}'))

    await teach.start(make_bot("Teacher")["id"])
    await until(lambda: teach.public() is None, 5, "录制到时自己结束")

    [done] = [e for e in heard if e.get("type") == "teach" and e.get("auto")]
    assert done["draft"]["name"] == "x" and done["auto"] is True
    assert done["bot_id"] and done["teach"] is None          # 录制已经结束，前端收到的状态是空的
    assert c.exclusive is None and "handback" in c.done
