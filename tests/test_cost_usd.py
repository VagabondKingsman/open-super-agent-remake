"""Costs are USD. models.dev prices are not multiplied, the shipped DeepSeek table is the USD list, and old CNY rows convert once."""
import json
import sqlite3
import time
from pathlib import Path

import pytest

from osa.config import CFG
from osa import memory, prices, tasklog

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_deepseek_table_is_official_usd():
    text = (ROOT / "config.yaml").read_text(encoding="utf-8")
    assert 'currency: "$"' in text
    assert "usd_rate:" not in text
    assert "¥" not in text
    models = CFG["pricing"]["models"]
    assert models["deepseek-flash"]["cache_hit"] == pytest.approx([0.006, 0.003])
    assert models["deepseek-flash"]["input"] == pytest.approx([0.3, 0.15])
    assert models["deepseek-flash"]["output"] == pytest.approx([1.2, 0.6])
    assert models["deepseek-v4-pro"]["cache_hit"] == pytest.approx([0.044, 0.022])
    assert models["deepseek-v4-pro"]["input"] == pytest.approx([1.32, 0.66])
    assert models["deepseek-v4-pro"]["output"] == pytest.approx([3.96, 1.98])
    assert prices.CURRENCY == memory.USAGE_CURRENCY == "$"
    assert prices.manual_table_is_cny() is False
    # Peak cache-hit and off-peak cache-miss, USD per million tokens.
    assert prices.cost(None, "deepseek-flash", 1_000_000, 0, 0, True) == pytest.approx(0.006)
    assert prices.cost(None, "deepseek-flash", 0, 1_000_000, 0, False) == pytest.approx(0.15)
    assert prices.cost(None, "deepseek-v4-pro", 0, 0, 1_000_000, True) == pytest.approx(3.96)
    assert prices.cost(None, "deepseek-v4-pro", 0, 1_000_000, 0, False) == pytest.approx(0.66)
    info = prices.info()
    assert info["currency"] == "$"
    assert info["unit"] == "USD"
    assert info["rate"] == 1


def test_models_dev_price_stays_usd(monkeypatch):
    saved_data, saved_matched = prices._data, dict(prices._matched)
    try:
        monkeypatch.setitem(CFG["providers"], "acme", {"base_url": "https://api.acme.test/v1", "preset": "acme"})
        prices._data = {"ts": 99, "providers": {"acme": {
            "api": "https://api.acme.test/v1", "name": "Acme",
            "models": {"m1": {"i": 2.5, "o": 10.0, "c": 0.5, "v": 0, "t": "chat", "n": "M1"}},
        }}}
        prices._matched.clear()
        assert prices.cost("acme", "m1", 0, 1_000_000, 0, False) == pytest.approx(2.5)
        assert prices.cost("acme", "m1", 1_000_000, 0, 1_000_000, False) == pytest.approx(10.5)
        looked = prices.lookup("acme", "m1")
        assert looked["source"] == "models.dev"
        assert looked["input"] == 2.5
        assert looked["cache"] == 0.5
        # 7.1 would have been the old CNY multiplier. It must not be applied.
        assert prices.cost("acme", "m1", 0, 1_000_000, 0, False) != pytest.approx(2.5 * 7.1)
    finally:
        prices._data = saved_data
        prices._matched.clear()
        prices._matched.update(saved_matched)


def test_local_model_costs_zero(monkeypatch):
    monkeypatch.setitem(CFG["providers"], "ollama-test", {"base_url": "http://127.0.0.1:11434/v1"})
    assert prices.cost("ollama-test", "llama", 0, 1_000_000, 1_000_000, True) == 0
    assert prices.lookup("ollama-test", "llama")["source"] == "local"


def test_legacy_cny_table_is_divided_once_into_usd(monkeypatch):
    monkeypatch.setitem(CFG["pricing"], "currency", "¥")
    monkeypatch.setitem(CFG["pricing"], "models", {
        "legacy-model": {"cache_hit": [0.71, 0.355], "input": [7.1, 3.55], "output": [14.2, 7.1]},
    })
    assert prices.manual_table_is_cny() is True
    assert prices.legacy_cny_per_usd() == pytest.approx(7.1)
    assert prices.cost(None, "legacy-model", 0, 1_000_000, 0, True) == pytest.approx(1)
    assert prices.cost(None, "legacy-model", 0, 1_000_000, 0, False) == pytest.approx(0.5)
    looked = prices.lookup(None, "legacy-model")
    assert looked["source"] == "config"
    assert looked["input"] == pytest.approx(1)
    assert looked["offpeak"][0] == pytest.approx(0.5)


class _Usage:
    def __init__(self, prompt, completion, hit=0):
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.prompt_cache_hit_tokens = hit


def test_record_usage_stores_usd(monkeypatch):
    monkeypatch.setattr(memory, "_is_peak", lambda ts: True)
    memory.record_usage("cost-usd-probe", "deepseek-flash", _Usage(1_000_000, 2_000_000), provider="deepseek")
    try:
        cost = memory.conn.execute(
            "select cost from llm_calls where role=? and model=?", ("cost-usd-probe", "deepseek-flash")).fetchone()[0]
        # Peak: 1e6 miss * $0.3 + 2e6 output * $1.2.
        assert cost == pytest.approx(2.7)
        stats = memory.usage_stats()
        assert stats["currency"] == "$"
        row = next(r for r in stats["by_role"] if r["role"] == "cost-usd-probe")
        assert row["cost"] == pytest.approx(2.7)
        assert row["tokens"] == 3_000_000
    finally:
        memory.conn.execute("delete from llm_calls where role=?", ("cost-usd-probe",))
        memory.conn.commit()


def test_usage_sums_and_task_detail_are_usd():
    now = time.time()
    before = memory.usage_stats()
    cur = memory.conn.execute(
        "insert into messages(ts, role, content, meta, chat_id, bot_id) values(?,?,?,?,?,?)",
        (now, "task", "[任务已派发] cost probe", json.dumps({"kind": "dispatch", "status": "done"}), None, None))
    task_id = cur.lastrowid
    rows = [
        (now, "cost-usd-sum", "a", task_id, 0, 0, 0, 0.0123, 0),
        (now, "cost-usd-sum", "a", task_id, 0, 0, 0, 0.0200, 0),
        (now - 3 * 86400, "cost-usd-sum", "b", task_id, 0, 0, 0, 0.1000, 0),
    ]
    memory.conn.executemany(
        "insert into llm_calls(ts, role, model, task_id, cache_hit, cache_miss, output, cost, estimated) values(?,?,?,?,?,?,?,?,?)",
        rows)
    memory.conn.commit()
    try:
        after = memory.usage_stats()
        assert after["currency"] == "$"
        assert after["today"]["cost"] - before["today"]["cost"] == pytest.approx(0.0323, abs=1e-5)
        assert after["week"]["cost"] - before["week"]["cost"] == pytest.approx(0.1323, abs=1e-5)
        assert after["month"]["cost"] - before["month"]["cost"] == pytest.approx(0.1323, abs=1e-5)
        assert after["today"]["calls"] - before["today"]["calls"] == 2
        task = next(t for t in after["by_task"] if t["id"] == task_id)
        assert task["cost"] == pytest.approx(0.1323)
        detail = tasklog.detail(task_id)
        assert detail["currency"] == "$"
        assert detail["cost"] == pytest.approx(0.1323)
        assert detail["usage"] == "recorded"
    finally:
        memory.conn.execute("delete from llm_calls where task_id=?", (task_id,))
        memory.conn.execute("delete from messages where id=?", (task_id,))
        memory.conn.commit()


def test_token_budget_ignores_usd_cost():
    before = memory.tokens_today()
    memory.conn.execute(
        """insert into llm_calls(ts, role, model, task_id, cache_hit, cache_miss, output, cost, estimated)
           values(?,?,?,?,?,?,?,?,?)""",
        (time.time(), "cost-usd-budget", "m", None, 0, 1, 0, 999, 0))
    memory.conn.commit()
    try:
        assert memory.tokens_today() - before == 1
        # Watchdog and the router compare tokens_today() with this cap, not the USD cost on the row.
        assert CFG["limits"]["daily_token_budget"] == 2_000_000
    finally:
        memory.conn.execute("delete from llm_calls where role=?", ("cost-usd-budget",))
        memory.conn.commit()


def _legacy_db():
    db = sqlite3.connect(":memory:")
    db.execute("""create table llm_usage(ts real, role text, model text, task_id integer,
        cache_hit integer, cache_miss integer, output integer, cost real, estimated integer)""")
    db.execute("create table settings(key text primary key, value text)")
    return db


def test_migration_reprices_manual_models_and_divides_the_rest(monkeypatch):
    monkeypatch.setattr(memory, "_is_peak", lambda ts: True)
    db = _legacy_db()
    # Old CNY list for deepseek-flash peak input was 2 per million tokens.
    db.execute("insert into llm_usage values(1,'r','deepseek-flash',1,0,1000000,0,2,0)")
    # A models.dev row was stored as USD * 7.1.
    db.execute("insert into llm_usage values(1,'r','glm-5.3-flash',2,0,0,0,7.1,0)")
    db.execute("insert into llm_usage values(1,'r','free',3,0,0,0,0,0)")
    first = memory.migrate_usage_currency(db, divisor=7.1)
    flash, glm, free = [r[0] for r in db.execute("select cost from llm_usage order by task_id")]
    assert flash == pytest.approx(0.3)
    assert glm == pytest.approx(1)
    assert free == 0
    assert first["currency"] == "USD"
    assert first["repriced_models"] == 1
    assert first["divided_rows"] == 1
    second = memory.migrate_usage_currency(db, divisor=99)
    assert db.execute("select cost from llm_usage where model='deepseek-flash'").fetchone()[0] == pytest.approx(0.3)
    assert db.execute("select cost from llm_usage where model='glm-5.3-flash'").fetchone()[0] == pytest.approx(1)
    assert second["legacy_cny_per_usd"] == 7.1


def test_migration_converts_rows_already_moved_into_llm_calls():
    # v0.12 copies llm_usage rows into llm_calls at startup, before prices runs the currency
    # migration. Both copies are CNY then and must be converted exactly once.
    db = _legacy_db()
    db.execute("""create table llm_calls(id integer primary key, ts real, role text, model text, task_id integer,
        cache_hit integer, cache_miss integer, output integer, cost real, estimated integer default 0)""")
    db.execute("insert into llm_usage values(1,'r','glm-5.3-flash',2,0,0,0,7.1,0)")
    db.execute("insert into llm_calls(ts, role, model, task_id, cache_hit, cache_miss, output, cost) "
               "values(1,'r','glm-5.3-flash',2,0,0,0,7.1)")
    done = memory.migrate_usage_currency(db, divisor=7.1)
    assert done["divided_rows"] == 2
    assert db.execute("select cost from llm_calls").fetchone()[0] == pytest.approx(1)
    memory.migrate_usage_currency(db, divisor=7.1)
    assert db.execute("select cost from llm_calls").fetchone()[0] == pytest.approx(1)


def test_migration_can_skip_when_rows_were_already_usd():
    db = _legacy_db()
    db.execute("insert into llm_usage values(1,'r','deepseek-flash',1,0,1000000,0,0.3,0)")
    done = memory.migrate_usage_currency(db, divisor=1)
    assert done["divided_rows"] == 0
    assert done["repriced_models"] == 0
    assert db.execute("select cost from llm_usage").fetchone()[0] == pytest.approx(0.3)
    assert memory.migrate_usage_currency(db, divisor=7.1)["legacy_cny_per_usd"] == 1


def test_fresh_database_is_marked_usd():
    saved = json.loads(memory.conn.execute("select value from settings where key='cost_unit'").fetchone()[0])
    assert saved["currency"] == "USD"
    assert saved["rows"] == 0


def test_ui_sources_have_no_yuan_symbol():
    files = [ROOT / "osa/static/index.html"]
    files += [p for p in (ROOT / "web/src").rglob("*") if p.suffix in {".ts", ".tsx", ".json"}]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "¥" not in text, path
        assert "人民币" not in text, path
        assert "CNY" not in text, path
