"""OSA-010: Heavy 只派一次、草稿够数才审、失败不记完成、额度用尽停下。假模型，无密钥。"""
import email.utils
import time

import httpx
import pytest
from openai import APIStatusError, RateLimitError

from conftest import find, until
from fakellm import Call, HttpError
from osa import i18n, server, tasklog
from osa.config import CFG
from osa.providers import classify_limit
from osa import providers
from osa.worker import heavy_plan


def bots_chat(bot):
    from osa import bots
    return bots.chat(bot["chat_id"])


@pytest.fixture
def fresh_bot(make_bot):
    """每个场景用完就删，避免整套测试超过 50 个 Bot。"""
    from osa import bots
    ids = []

    def make(name: str):
        bot = make_bot(name)
        ids.append(bot["id"])
        return bot

    yield make
    for i in ids:
        bots.delete(i)


def _err(status: int, body: dict, headers: dict | None = None):
    req = httpx.Request("POST", "https://example.test/v1/chat/completions")
    resp = httpx.Response(status, json=body, headers=headers or {}, request=req)
    data = body.get("error", body)
    if status == 429:
        return RateLimitError(f"Error code: {status}", response=resp, body=data)
    return APIStatusError(f"Error code: {status}", response=resp, body=data)


def _quota(code: str, message: str, status: int = 429, headers: dict | None = None) -> HttpError:
    return HttpError(status, {"error": {"code": code, "message": message}}, headers or {})


async def _send(bot, text: str):
    await server.safe_handle(bots_chat(bot), text)


async def _results(bot, n: int = 1):
    return await until(lambda: len(find(bot["chat_id"], kind="result")) >= n and find(bot["chat_id"], kind="result"),
                       what=f"{n} 条任务结果")


def test_classify_quota_and_rate_limit():
    daily = classify_limit(_err(429, {"error": {"message": "org_token_rate_limit_day: Free core models share 1000000 tokens"}}))
    assert daily is not None and daily.kind == "quota" and daily.code == "org_token_rate_limit_day" and daily.retry_after is None

    for code in ("insufficient_quota", "free_limit_reached", "budget_exceeded"):
        hit = classify_limit(_err(429, {"error": {"code": code, "type": code, "message": "stop"}}))
        assert hit is not None and hit.kind == "quota" and hit.code == code

    payment = classify_limit(_err(402, {"error": {"code": "budget_exceeded", "message": "budget"}}))
    assert payment is not None and payment.kind == "quota" and payment.status == 402

    # 明确的普通限流即使正文里出现 quota 这个词，也按 Retry-After 重试，不当成额度用尽。
    rate = classify_limit(_err(
        429,
        {"error": {"code": "rate_limit_exceeded", "message": "per-minute quota of requests"}},
        {"retry-after": "4"},
    ))
    assert rate is not None and rate.kind == "rate" and rate.retry_after == 4

    millis = classify_limit(_err(429, {"error": {"code": "rate_limit_exceeded", "message": "slow"}}, {"retry-after-ms": "1500"}))
    assert millis is not None and millis.kind == "rate" and millis.retry_after == 1.5

    when = email.utils.formatdate(time.time() + 30, usegmt=True)
    dated = classify_limit(_err(429, {"error": {"message": "slow"}}, {"retry-after": when}))
    assert dated is not None and dated.kind == "rate" and dated.retry_after is not None
    assert 20 <= dated.retry_after <= 40

    assert classify_limit(_err(500, {"error": {"message": "boom"}})) is None


def test_heavy_plan_clamps_quorum(monkeypatch):
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["heavy"], "concurrency", 4)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 9)
    assert heavy_plan() == (3, 3, 3)
    monkeypatch.setitem(CFG["heavy"], "workers", 1)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    assert heavy_plan() == (1, 1, 1)


async def test_heavy_dispatch_is_idempotent_in_one_turn(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    bot = fresh_bot("Idem")
    llm.script("worker", "d0", "d1", "d2")
    llm.script("reviewer", "FINAL")
    llm.script(
        f"router:{bot['name']}",
        [Call("dispatch", {"goal": "g1", "mode": "heavy"}),
         Call("dispatch", {"goal": "g2", "mode": "heavy"}),
         Call("dispatch", {"goal": "g3", "mode": "heavy"})],
        "ack",
    )
    await _send(bot, "heavy")
    result = await _results(bot)
    assert len(find(bot["chat_id"], kind="dispatch")) == 1
    assert result[-1]["meta"]["status"] == "done"
    assert "FINAL" in result[-1]["content"]
    assert len(llm.bodies("worker")) == 3
    assert len(llm.bodies("reviewer")) == 1
    tools = [m["content"] for m in llm.bodies("router", bot["name"])[1]["messages"] if m["role"] == "tool"]
    assert sum("不再另派" in c for c in tools) == 2
    detail = tasklog.detail(result[-1]["meta"]["task_id"])
    assert detail["status"] == "done" and detail["mode"] == "heavy"


async def test_heavy_dispatch_idempotent_across_tool_rounds(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    bot = fresh_bot("Rounds")
    llm.script("worker", "d0", "d1", "d2")
    llm.script("reviewer", "ONCE")
    llm.script(
        f"router:{bot['name']}",
        Call("dispatch", {"goal": "first", "mode": "heavy"}),
        Call("dispatch", {"goal": "second", "mode": "heavy"}),
        "ack",
    )
    await _send(bot, "heavy")
    await _results(bot)
    assert len(find(bot["chat_id"], kind="dispatch")) == 1
    assert len(llm.bodies("worker")) == 3
    assert len(llm.bodies("reviewer")) == 1
    tools = [m["content"] for m in llm.bodies("router", bot["name"])[2]["messages"] if m["role"] == "tool"]
    assert any("不再另派" in c for c in tools)


async def test_later_turn_can_dispatch_heavy_again(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 1)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 1)
    bot = fresh_bot("Again")
    llm.script("worker", "one", "two")
    llm.script("reviewer", "R1", "R2")
    llm.script(
        f"router:{bot['name']}",
        Call("dispatch", {"goal": "first", "mode": "heavy"}),
        "ack",
        Call("dispatch", {"goal": "second", "mode": "heavy"}),
        "ack2",
    )
    await _send(bot, "first")
    await _results(bot, 1)
    await _send(bot, "second")
    await _results(bot, 2)
    assert len(find(bot["chat_id"], kind="dispatch")) == 2


async def test_single_dispatch_is_not_deduped(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    bot = fresh_bot("Singles")
    llm.script("worker", "one", "two")
    llm.script(
        f"router:{bot['name']}",
        [Call("dispatch", {"goal": "a", "mode": "single"}), Call("dispatch", {"goal": "b", "mode": "single"})],
        "ack",
    )
    await _send(bot, "two tasks")
    await _results(bot, 2)
    assert len(find(bot["chat_id"], kind="dispatch")) == 2
    assert len(llm.bodies("worker")) == 2


async def test_quorum_blocks_reviewer(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    monkeypatch.setitem(CFG["heavy"], "concurrency", 1)
    monkeypatch.setitem(CFG["limits"], "provider_transient_retries", 0)
    bot = fresh_bot("Quorum")
    llm.script("worker", "ONLY", HttpError(500, {"error": {"message": "boom"}}), HttpError(500, {"error": {"message": "boom"}}))
    llm.script("reviewer", "SHOULD_NOT_RUN")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "need drafts", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "failed"
    assert "草稿不够" in result[-1]["content"] and "1/3" in result[-1]["content"]
    assert llm.bodies("reviewer") == []
    assert tasklog.detail(result[-1]["meta"]["task_id"])["status"] == "failed"
    dispatch = find(bot["chat_id"], kind="dispatch")[-1]
    assert dispatch["meta"]["status"] == "failed"


async def test_partial_when_quorum_met_but_a_worker_failed(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    monkeypatch.setitem(CFG["heavy"], "concurrency", 1)
    monkeypatch.setitem(CFG["limits"], "provider_transient_retries", 0)
    bot = fresh_bot("Partial")
    llm.script("worker", "A", "B", HttpError(500, {"error": {"message": "boom"}}))
    llm.script("reviewer", "REVIEWED")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "partial", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "partial"
    assert "REVIEWED" in result[-1]["content"]
    assert len(llm.bodies("reviewer")) == 1
    detail = tasklog.detail(result[-1]["meta"]["task_id"])
    assert detail["status"] == "partial"
    assert find(bot["chat_id"], kind="dispatch")[-1]["meta"]["status"] == "partial"


async def test_quota_429_stops_pipeline_without_retry(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["heavy"], "concurrency", 1)
    monkeypatch.setitem(CFG["limits"], "provider_rate_retries", 2)
    slept = []

    async def spy(seconds):
        slept.append(seconds)

    monkeypatch.setattr(providers, "_pause", spy)
    bot = fresh_bot("Quota")
    llm.script("worker", _quota("org_token_rate_limit_day", "Free core models share 1000000 tokens per UTC day", headers={"retry-after": "30"}))
    llm.script("reviewer", "SHOULD_NOT_RUN")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "quota", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "failed"
    assert "没有交给审稿人" in result[-1]["content"]
    assert "org_token_rate_limit_day" in result[-1]["content"]
    assert llm.bodies("reviewer") == []
    assert len(llm.bodies("worker")) == 1
    assert slept == []
    assert tasklog.detail(result[-1]["meta"]["task_id"])["status"] == "failed"


async def test_402_after_two_drafts_does_not_call_reviewer(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    monkeypatch.setitem(CFG["heavy"], "concurrency", 1)
    bot = fresh_bot("Pay")
    llm.script("worker", "A", "B", _quota("budget_exceeded", "budget", status=402))
    llm.script("reviewer", "SHOULD_NOT_RUN")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "pay", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "failed"
    assert "没有交给审稿人" in result[-1]["content"]
    assert llm.bodies("reviewer") == []
    assert len(llm.bodies("worker")) == 3


async def test_insufficient_quota_fails_single_task(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    bot = fresh_bot("Insuff")
    llm.script("worker", _quota("insufficient_quota", "You exceeded your current quota"))
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "single quota"}), "ack")
    await _send(bot, "go")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "failed"
    assert "insufficient_quota" in result[-1]["content"]
    assert len(llm.bodies("worker")) == 1


async def test_free_limit_reached_is_quota(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 1)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 1)
    bot = fresh_bot("Free")
    llm.script("worker", _quota("free_limit_reached", "free limit"))
    llm.script("reviewer", "SHOULD_NOT_RUN")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "free", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "failed"
    assert llm.bodies("reviewer") == []
    assert len(llm.bodies("worker")) == 1


async def test_rate_limit_honors_retry_after(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["limits"], "provider_rate_retries", 1)
    monkeypatch.setitem(CFG["limits"], "provider_retry_cap_s", 120)
    slept = []

    async def spy(seconds):
        slept.append(seconds)

    monkeypatch.setattr(providers, "_pause", spy)
    bot = fresh_bot("Retry")
    llm.script(
        "worker",
        HttpError(429, {"error": {"code": "rate_limit_exceeded", "message": "slow down"}}, {"retry-after": "2.5"}),
        "RATE_OK",
    )
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "rate"}), "ack")
    await _send(bot, "go")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "done"
    assert "RATE_OK" in result[-1]["content"]
    assert slept == [2.5]
    assert len(llm.bodies("worker")) == 2


async def test_rate_limit_cap_and_give_up(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["limits"], "provider_rate_retries", 1)
    monkeypatch.setitem(CFG["limits"], "provider_retry_cap_s", 1.25)
    slept = []

    async def spy(seconds):
        slept.append(seconds)

    monkeypatch.setattr(providers, "_pause", spy)
    bot = fresh_bot("GiveUp")
    slow = HttpError(429, {"error": {"code": "rate_limit_exceeded", "message": "slow"}}, {"retry-after": "30"})
    llm.script("worker", slow, slow)
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "give up"}), "ack")
    await _send(bot, "go")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "failed"
    assert "请求太频繁" in result[-1]["content"]
    assert slept == [1.25]
    assert len(llm.bodies("worker")) == 2


@pytest.mark.parametrize("concurrency, peak", [(1, 1), (3, 3)])
async def test_heavy_worker_concurrency(llm, events, fresh_bot, monkeypatch, concurrency, peak):
    monkeypatch.setattr(i18n, "_lang", "zh")
    monkeypatch.setitem(CFG["heavy"], "workers", 3)
    monkeypatch.setitem(CFG["heavy"], "concurrency", concurrency)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    bot = fresh_bot(f"Conc{concurrency}")
    llm.gap = 0.05
    llm.script("worker", "a", "b", "c")
    llm.script("reviewer", "R")
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "conc", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "done"
    assert llm.worker_peak == peak


# ---------- B3：审稿人只回开场白 ----------
LONG = "Bản nháp {i}: " + "phân tích chi tiết từng phương án với rủi ro và phép đo cụ thể. " * 12


async def test_reviewer_preamble_falls_back_to_longest_draft(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setitem(CFG["heavy"], "workers", 2)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    bot = fresh_bot("Preamble")
    short, longer = LONG.format(i=1), LONG.format(i=2) + " Thêm kết luận."
    llm.script("worker", short, longer)
    llm.script("reviewer", "Tôi sẽ nạp skill rồi đối chiếu.", "Tôi sẽ nạp skill trước.")
    goal = "So sánh 3 cách.\nSkill Flow: ai-work-method -> unslop-vi\nWorker phải load_skill ai-work-method trước khi viết.\nOutput: 200 từ."
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": goal, "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    meta = result[-1]["meta"]
    assert meta["status"] == "partial"
    assert longer.strip()[:60] in result[-1]["content"]
    assert "Tôi sẽ nạp skill" not in result[-1]["content"]
    rev = llm.bodies("reviewer")
    assert len(rev) == 2   # một lần hỏi lại, không hơn
    q = rev[0]["messages"][-1]["content"]
    assert "load_skill" not in q and "Skill Flow" not in q and "So sánh 3 cách." in q and "Output: 200 từ." in q
    assert "no tools" in rev[0]["messages"][0]["content"]
    notes = [s["title"] for s in tasklog.steps(meta["task_id"]) if s["kind"] == "note"]
    assert any("dùng bản nháp 2" in n for n in notes)


async def test_reviewer_retry_recovers(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setitem(CFG["heavy"], "workers", 2)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    bot = fresh_bot("Recover")
    llm.script("worker", LONG.format(i=1), LONG.format(i=2))
    merged = "Kết luận gộp: " + "chọn cách (c) vì một màn hình và một Chromium. " * 4
    llm.script("reviewer", "Tôi sẽ đối chiếu.", merged)
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "so sánh", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "done"
    assert merged.strip()[:40] in result[-1]["content"]
    assert len(llm.bodies("reviewer")) == 2


async def test_reviewer_good_merge_not_retried(llm, events, fresh_bot, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setitem(CFG["heavy"], "workers", 2)
    monkeypatch.setitem(CFG["heavy"], "min_drafts", 2)
    bot = fresh_bot("GoodMerge")
    llm.script("worker", LONG.format(i=1), LONG.format(i=2))
    merged = "Kết luận gộp: " + "chọn cách (c) vì một màn hình và một Chromium. " * 4
    llm.script("reviewer", merged)
    llm.script(f"router:{bot['name']}", Call("dispatch", {"goal": "so sánh", "mode": "heavy"}), "ack")
    await _send(bot, "heavy")
    result = await _results(bot)
    assert result[-1]["meta"]["status"] == "done"
    assert len(llm.bodies("reviewer")) == 1
