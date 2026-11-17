"""Tác vụ lỗi thì không được trình bày kết quả (402/timeout/…): tin kết quả phải mang luật,
và câu trả lời ngay sau đó mà bày bảng PASS/exit code thì bị đính chính."""
import pytest

from conftest import find, until
from fakellm import Call, StreamReply
from osa import bots, i18n, memory, router, server
from osa.worker import Task


def test_result_body_adds_rule_only_for_failed_tasks(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    done = Task(id=1, bot_id=1, chat_id=1, goal="x")
    done.status, done.result = "done", "ok"
    assert "output" not in router.result_body(done)
    bad = Task(id=2, bot_id=1, chat_id=1, goal="x")
    bad.status, bad.result = "failed", "Tác vụ thất bại: Hết hạn mức (402 -)"
    body = router.result_body(bad)
    assert body.startswith("Tác vụ thất bại")
    assert "không có output" in body           # luật tiếng Việt
    empty = Task(id=3, bot_id=1, chat_id=1, goal="x")
    empty.status, empty.result = "failed", ""
    assert router.result_body(empty) == ""     # không có gì để dán luật vào


@pytest.mark.parametrize("text,want", [
    ("| Bước | Kết quả |\n| 1 | PASS |", True),
    ("check_exit=0 và ui.py texts OK", True),
    ("✅ 环境自检通过", True),
    ("Kết quả: FAIL", True),
    ("Mình chưa chạy được bước này.", False),
    ("", False),
])
def test_claims_results(text, want):
    assert router.claims_results(text) is want


def _chat(bot):
    return bots.chat(bot["chat_id"])


async def _dispatch_failing(llm, bot):
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "kiểm tra gì đó"}), "đã giao")
    llm.script("worker", StreamReply(content="", reasoning="trống", finish="length"),
               StreamReply(content="", reasoning="vẫn trống", finish="length"))
    await server.safe_handle(_chat(bot), "chạy bước 1")
    return await until(lambda: find(bot["chat_id"], kind="result"), what="kết quả task")


async def test_failed_result_carries_the_rule(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("FailRule")
    result = await _dispatch_failing(llm, bot)
    assert result[0]["meta"]["status"] == "failed"
    assert "không có output" in result[0]["content"]


async def test_reply_claiming_results_after_failure_is_corrected(llm, events, make_bot, monkeypatch):
    """Đúng ca đã gặp: worker chết 402, bot vẫn bày bảng PASS — phải có câu đính chính."""
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("FakePass")
    await _dispatch_failing(llm, bot)
    llm.script(f"router:{bot['name']}", "| Bước | Kết quả |\n| 1 | PASS |\nexit=0")
    await server.safe_handle(_chat(bot), "tóm tắt kết quả đi")
    await until(lambda: len(find(bot["chat_id"], role="assistant")) >= 2, what="câu trả lời")
    msg = find(bot["chat_id"], role="assistant")[-1]
    assert "Đính chính" in msg["content"]
    assert msg["meta"].get("unsupported_results", {}).get("task_id")


async def test_reply_without_claims_is_left_alone(llm, events, make_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    bot = make_bot("Honest")
    await _dispatch_failing(llm, bot)
    llm.script(f"router:{bot['name']}", "Bước này lỗi vì hết hạn mức, mình chưa có kết quả.")
    await server.safe_handle(_chat(bot), "sao rồi")
    await until(lambda: len(find(bot["chat_id"], role="assistant")) >= 2, what="câu trả lời")
    msg = find(bot["chat_id"], role="assistant")[-1]
    assert "Đính chính" not in msg["content"]
    assert not msg["meta"].get("unsupported_results")
