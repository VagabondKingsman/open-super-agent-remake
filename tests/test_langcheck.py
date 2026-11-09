"""Wrong-language reply check (osa/langcheck.py) and the reply-language hint with MCP tools present."""
import sys
from pathlib import Path

import pytest
from conftest import find, until
from fakellm import Call
from osa import bots, i18n, langcheck, mcp_hub, server

ZH = "今天杭州天气晴朗，气温二十一度，适合出门散步，也可以去西湖边走走，傍晚记得带一件外套。"   # > 20 han


@pytest.mark.parametrize("ui", ["vi", "en"])
def test_flags_a_chinese_reply_in_non_chinese_ui(ui):
    flag = langcheck.check(ZH, "What's the weather like in Hangzhou?", ui)
    assert flag and flag["ui"] == ui and flag["han"] >= langcheck.MIN_HAN


def test_zh_ui_is_never_checked():
    assert langcheck.check(ZH, "weather?", "zh") is None


def test_chinese_request_allows_chinese_reply():
    assert langcheck.check(ZH, "杭州今天天气怎么样？", "vi") is None
    assert langcheck.check(ZH, "Please translate this short word into Vietnamese for me, thanks: 你好吗", "vi") is not None


def test_short_and_mixed_replies_are_left_alone():
    assert langcheck.check("你好！", "hi", "vi") is None
    assert langcheck.check("Hôm nay trời nắng, nhiệt độ 21 độ. " + ZH[:12], "hi", "vi") is None
    vi = "Hôm nay Hàng Châu trời nắng đẹp, nhiệt độ khoảng 21 độ, rất hợp để đi dạo quanh Tây Hồ."
    assert langcheck.check(vi, "hi", "vi") is None and langcheck.check(vi, "hi", "en") is None


def test_code_urls_quotes_and_markers_are_ignored():
    code = "Đây là mã:\n```python\nprint('" + ZH + "')\n```\nXong rồi."
    assert langcheck.check(code, "hi", "vi") is None
    assert langcheck.check("Xem https://example.com/" + ZH + " nhé", "hi", "vi") is None
    assert langcheck.check("Bạn viết: “" + ZH + "” nghĩa là hôm nay trời đẹp.", "hi", "vi") is None
    assert langcheck.check("Bạn viết:\n> " + ZH + "\nnghĩa là hôm nay trời đẹp, cứ đi dạo thôi.", "hi", "vi") is None
    assert langcheck.check("`" + ZH + "` là câu mẫu.", "hi", "vi") is None
    assert langcheck.check("[附件] " * 30 + "đã nhận", "hi", "vi") is None


def test_defaults_to_current_ui_language(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    assert langcheck.check(ZH, "hi")
    monkeypatch.setattr(i18n, "_lang", "zh")
    assert langcheck.check(ZH, "hi") is None


def test_record_logs_once(monkeypatch, caplog):
    monkeypatch.setattr(i18n, "_lang", "vi")
    with caplog.at_level("WARNING", logger="osa.langcheck"):
        assert langcheck.record(ZH, "hi", "chat 7")
        assert langcheck.record("Xin chào", "hi", "chat 7") is None
    assert len(caplog.records) == 1 and "chat 7" in caplog.records[0].getMessage()


@pytest.fixture
def bot(make_bot):
    made = []

    def make(name: str = "") -> dict:
        made.append(make_bot(name))
        return made[-1]
    yield make
    for b in made:
        bots.delete(b["id"])


async def test_router_reply_is_flagged_not_rewritten(monkeypatch, llm, events, bot):
    monkeypatch.setattr(i18n, "_lang", "vi")
    b = bot("Langy")
    llm.script("router:Langy", ZH)
    await server.safe_handle(bots.chat(b["chat_id"]), "What's the weather like in Hangzhou?")
    [m] = await until(lambda: find(b["chat_id"], role="assistant", text=ZH), what="reply")
    assert m["content"] == ZH and m["meta"]["lang_flag"]["ui"] == "vi"


async def test_router_reply_not_flagged_when_user_writes_chinese(monkeypatch, llm, events, bot):
    monkeypatch.setattr(i18n, "_lang", "vi")
    b = bot("Langz")
    llm.script("router:Langz", ZH)
    await server.safe_handle(bots.chat(b["chat_id"]), "杭州今天天气怎么样？")
    [m] = await until(lambda: find(b["chat_id"], role="assistant", text=ZH), what="reply")
    assert "lang_flag" not in m["meta"]


async def test_task_result_is_flagged_with_a_task_note(monkeypatch, llm, events, bot):
    from osa import tasklog
    monkeypatch.setattr(i18n, "_lang", "en")
    b = bot("Tasky")
    llm.script("router:Tasky", Call("dispatch", {"goal": "Check the weather in Hangzhou"}), "On it")
    llm.script("worker", ZH)
    await server.safe_handle(bots.chat(b["chat_id"]), "Check the weather in Hangzhou")
    [res] = await until(lambda: find(b["chat_id"], kind="result"), what="task result")
    assert res["meta"]["lang_flag"]["ui"] == "en"
    notes = [s["title"] for s in tasklog.steps(res["meta"]["task_id"]) if s["kind"] == "note"]
    assert any("en" in n and "Chinese" in n for n in notes)


async def test_observe_task_rows_carry_the_flag(monkeypatch, llm, events, bot):
    from osa import observe
    monkeypatch.setattr(i18n, "_lang", "en")
    zh, en = bot("Obsz"), bot("Obse")
    llm.script("router:Obsz", Call("dispatch", {"goal": "Summarise the news"}), "On it")
    llm.script("router:Obse", Call("dispatch", {"goal": "Summarise the news"}), "On it")
    llm.script("worker", ZH)
    await server.safe_handle(bots.chat(zh["chat_id"]), "Summarise the news")
    [res] = await until(lambda: find(zh["chat_id"], kind="result"), what="flagged result")
    llm.script("worker", "Here is the summary in English, as asked.")
    await server.safe_handle(bots.chat(en["chat_id"]), "Summarise the news")
    await until(lambda: find(en["chat_id"], kind="result"), what="plain result")
    [row] = observe.stats("today", 0, zh["id"])["tasks"]
    assert row["id"] == res["meta"]["task_id"] and row["lang_flag"]["ui"] == "en"
    [plain] = observe.stats("today", 0, en["id"])["tasks"]
    assert plain["lang_flag"] is None


SERVER = Path(__file__).parent / "fixtures" / "mcp_ui_server.py"


@pytest.fixture
async def mcp_app():
    mcp_hub.save("uidemo", {"command": sys.executable, "args": [str(SERVER)]})
    await mcp_hub.connect("uidemo", timeout=60)
    assert mcp_hub.session_of("uidemo")
    yield "uidemo"
    await mcp_hub.disconnect("uidemo")
    mcp_hub.remove("uidemo")


@pytest.mark.parametrize("language", ["vi", "en"])
async def test_reply_language_hint_is_sent_with_mcp_tools(mcp_app, monkeypatch, llm, events, bot, language):
    """MCP tool descriptions come from the server and are passed through as they are. The reply-language
    directive still reaches the model in both the router prompt and the worker prompt."""
    monkeypatch.setattr(i18n, "_lang", language)
    b = bot("Mcpy")
    llm.script("router:Mcpy", Call("dispatch", {"goal": "weather in Hangzhou"}), "ok")
    llm.script("worker", Call("uidemo__show_weather", {"city": "Hangzhou"}), "Sunny, 21 degrees")
    await server.safe_handle(bots.chat(b["chat_id"]), "weather in Hangzhou")
    await until(lambda: find(b["chat_id"], kind="result"), what="task result")
    worker_body = llm.bodies("worker")[-1]
    assert any(t["function"]["name"] == "uidemo__show_weather" for t in worker_body["tools"])
    assert i18n.ANSWER_LANG[language] in worker_body["messages"][0]["content"]
    assert i18n.ANSWER_LANG[language] in llm.bodies("router", "Mcpy")[0]["messages"][0]["content"]
