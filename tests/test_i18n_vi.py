"""VI port regressions. conftest isolates the database and model providers."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from osa import auth, computer, i18n, memories, memory, router, routines, server, templates, worker
from osa.computer import local


@pytest.fixture
def language_settings(monkeypatch):
    before = memory.conn.execute("select key, value from settings where key in ('language', 'overrides')").fetchall()
    memory.conn.execute("delete from settings where key in ('language', 'overrides')")
    memory.conn.commit()
    monkeypatch.setattr(i18n, "_lang", None)
    yield
    memory.conn.execute("delete from settings where key in ('language', 'overrides')")
    memory.conn.executemany("insert into settings values(?, ?)", before)
    memory.conn.commit()


def test_default_is_vietnamese(language_settings):
    assert i18n.chosen() == ""
    assert i18n.lang() == "vi"


@pytest.mark.parametrize("header, expected", [
    ("vi-VN, en;q=0.9", "vi"), ("VI", "vi"), ("zh-TW", "zh"),
    ("en-US", "en"), ("fr-FR,vi;q=0.8", "en"), (None, "en"),
])
def test_detection(header, expected):
    assert i18n.from_header(header) == expected


@pytest.mark.parametrize("value", ["vi", "en", "zh"])
def test_legacy_database_preference_migrates_once(language_settings, monkeypatch, value):
    memory.conn.execute("insert into settings values('overrides', ?)", (json.dumps({"locale": value}),))
    memory.conn.commit()
    assert i18n.chosen() == value
    memory.conn.execute("update settings set value=? where key='overrides'", (json.dumps({"locale": "invalid"}),))
    memory.conn.commit()
    monkeypatch.setattr(i18n, "_lang", None)
    assert i18n.chosen() == value


def test_language_setting_wins_over_legacy(language_settings):
    memory.conn.execute("insert into settings values('overrides', ?)", (json.dumps({"locale": "zh"}),))
    memory.conn.commit()
    i18n.set_lang("en")
    assert i18n.chosen() == "en"
    with pytest.raises(ValueError):
        i18n.set_lang("bad")


@pytest.mark.parametrize("language, expected", [("vi", "Tác vụ #7"), ("en", "Task #7"), ("zh", "任务 #7")])
def test_translation_and_worker_language(monkeypatch, language, expected):
    monkeypatch.setattr(i18n, "_lang", language)
    assert i18n.t("任务 #{id}", id=7) == expected
    assert language in worker.ANSWER_LANG
    if language == "vi":
        assert "tiếng Việt" in i18n.model_hint()
        assert "越南语" in memories._import_prompt()
    assert "Cho phép một lần" in i18n.both("允许一次")


def test_dictionary_parity_and_placeholders():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for base in (root / "osa/locales", root / "web/src/locales"):
        en = json.loads((base / "en.json").read_text())
        vi = json.loads((base / "vi.json").read_text())
        assert en.keys() == vi.keys()
        for key, value in vi.items():
            assert isinstance(value, str) and value
            assert set(i18n.PH.findall(value)) == set(i18n.PH.findall(key))
            assert not i18n.CJK.search(value)
            assert "{{" not in value and "}}" not in value


async def test_bootstrap_default_and_preference(language_settings):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test") as client:
        first = await client.get("/api/bootstrap", headers={"accept-language": "en-US"})
        assert first.status_code == 200 and first.json()["settings"]["language"] == "vi"
        i18n.set_lang("en")
        second = await client.get("/api/bootstrap?lang=zh")
        assert second.json()["settings"]["language"] == "en"
        for language in ("vi", "en", "zh"):
            response = await client.put("/api/settings", json={"language": language})
            assert response.status_code == 200 and response.json()["language"] == language


async def test_first_bootstrap_honors_migrated_browser_preference(language_settings):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test") as client:
        response = await client.get("/api/bootstrap?lang=zh")
        assert response.json()["settings"]["language"] == "zh"


async def test_docker_missing_is_unavailable(monkeypatch):
    async def missing(*args, **kw):
        raise FileNotFoundError("docker")
    monkeypatch.setattr(local.asyncio, "create_subprocess_exec", missing)
    monkeypatch.setattr(i18n, "_lang", "vi")
    assert await local._run("docker", "inspect") == (127, "", "docker-missing")
    pc = local.LocalComputer(0)
    info = await pc.status()
    assert info["state"] == "unavailable" and info["reason"] == "docker_missing"
    assert "Docker" in info["detail"]
    with pytest.raises(computer.ComputerError, match="Docker"):
        await pc.start()
    monkeypatch.setattr(computer, "get", lambda *args: pc)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test") as client:
        response = await client.get("/api/files")
        assert response.status_code == 200
        assert response.json()["state"] == "unavailable" and "Docker" in response.json()["detail"]


@pytest.mark.parametrize("text", ["[Không có nội dung mới]", "Không có nội dung mới."])
def test_vietnamese_quiet_marker(text):
    assert routines.is_quiet(text)
    assert not routines.is_quiet(text + " Nhưng có một tin.")


def test_templates_use_english_overlay_in_vi(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    text = "osa_template: 1\nname: 原文\nen:\n  name: English name\n"
    assert templates.parse(text)["name"] == "English name"


def test_login_and_oauth_language(monkeypatch):
    from starlette.requests import Request
    monkeypatch.setattr(i18n, "_lang", "vi")
    request = Request({"type": "http", "headers": [], "query_string": b""})
    assert 'lang="vi"' in auth._page(request, "/").body.decode()
    assert 'lang="vi"' in server._oauth_page(True, "OK").body.decode()


@pytest.mark.parametrize("trigger", [
    [], {"kind": "daily", "times": "09:00"}, {"kind": "daily", "times": [1]},
    {"kind": "daily", "times": ["09:00"], "days": [8]},
    {"kind": "daily", "times": ["09:00"], "days": [True]},
    {"kind": "daily", "times": ["09:00"], "days": False},
    {"kind": "every", "minutes": True}, {"kind": "every", "minutes": 5.5},
    {"kind": "webhook", "include": "bug"}, {"kind": "webhook", "llm_filter": []},
])
def test_schedule_validation(trigger):
    with pytest.raises(ValueError):
        routines._clean_trigger(trigger)


async def test_webhook_filter_reserved_before_await(monkeypatch, make_bot):
    bot = make_bot()
    r = routines.save(bot["id"], {"name": f"race-{bot['id']}", "prompt": "Read only", "trigger": {"kind": "webhook", "llm_filter": "Check"}})
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def filter_(*args):
        entered.set()
        await release.wait()
        return True, "ok"
    async def dispatch(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(id=123)
    monkeypatch.setattr(routines, "_llm_filter", filter_)
    monkeypatch.setattr(router, "runtime", lambda *args: SimpleNamespace(dispatch=dispatch))
    first = asyncio.create_task(routines.fire(r, "webhook", "event"))
    await asyncio.wait_for(entered.wait(), 2)
    second = await routines.fire(r, "webhook", "event")
    release.set()
    try:
        assert (await first)["accepted"] and not second["accepted"]
        assert len(calls) == 1 and r["id"] not in routines.FIRING
    finally:
        routines.RUNNING.pop(r["id"], None)
        routines.delete(r["id"])


async def test_runtime_failure_clears_reservations(monkeypatch, make_bot):
    bot = make_bot()
    r = routines.save(bot["id"], {"name": "runtime-failure", "prompt": "Read only", "trigger": {"kind": "every", "minutes": 5}})
    def fail(*args):
        raise RuntimeError("test-runtime-failure")
    monkeypatch.setattr(router, "runtime", fail)
    try:
        result = await routines.fire(r, "test")
        assert not result["accepted"]
        assert r["id"] not in routines.FIRING and r["id"] not in routines.RUNNING
    finally:
        routines.delete(r["id"])
