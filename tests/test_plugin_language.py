"""Shipped catalog plugins follow the UI language: user-visible text goes through i18n, model-facing text is English."""
import importlib.util

import pytest

from osa import i18n, plugins

NAMES = sorted(plugins._names(plugins.CATALOG))


def _module(name):
    spec = importlib.util.spec_from_file_location(f"lang_{name}", plugins.CATALOG / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(params=["vi", "en"])
def ui(request, monkeypatch):
    monkeypatch.setattr(i18n, "_lang", request.param)
    return request.param


def _no_cjk(*texts):
    return not any(i18n.CJK.search(t) for t in texts)


def test_budget_messages(ui):
    ba = _module("budget_alert")
    full = ba.token_message(100, 1_200_000, 1_000_000, 1.2, "$")
    warn = ba.token_message(80, 850_000, 1_000_000, 1.2, "$")
    cost = ba.cost_message(80, 4.0, 5.0, "$")
    assert _no_cjk(full, warn, cost)
    assert "1.20M / 1.00M" in full and "$1.20" in full and "85%" in warn and "80%" in cost and "$5" in cost


def test_budget_messages_zh_keep_wan(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    ba = _module("budget_alert")
    assert "85.0 万 / 100.0 万" in ba.token_message(80, 850_000, 1_000_000, 1.2, "$")


def test_keyword_notice(ui):
    ka = _module("keyword_alert")
    group = {"id": 9, "kind": "group", "title": "Ops"}
    text = ka.notice(group, "dingtalk", "server urgent", ["urgent", "down"])
    assert _no_cjk(text) and "Ops" in text and "DingTalk" in text and "urgent" in text and "down" in text
    direct = ka.where({"id": 3, "kind": "direct", "title": "Nova", "parent": 2}, "telegram")
    assert _no_cjk(direct) and "Nova" in direct and "Telegram" in direct


def test_keyword_notice_zh_unchanged(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "zh")
    ka = _module("keyword_alert")
    assert ka.where({"id": 9, "kind": "group", "title": "运维群"}, "dingtalk") == "群「运维群」（钉钉）"


def test_rss_and_webhook_and_push_messages(ui):
    rss, hook, push = _module("rss_watch"), _module("task_webhook"), _module("push_phone")
    one = rss.message("Feed", "https://x", [{"title": "A", "link": "https://x/a"}])
    many = rss.message("Feed", "https://x", [{"title": str(i), "link": ""} for i in range(13)])
    assert _no_cjk(one, many) and "1" in one and "13" in many and "3" in many.splitlines()[-1]
    task, bot = {"id": 7, "status": "done", "goal": "do it"}, {"name": "Nova"}
    done, failed = hook.message(task, bot, "ok"), hook.message(task | {"status": "error"}, bot, "")
    assert _no_cjk(done, failed) and "#7" in done and "Nova" in done and done != failed
    title, body = push.task_message({"id": 7, "status": "done"}, bot, "")
    assert _no_cjk(title, body) and "Nova" in title and "#7" in body
    assert _no_cjk(push.link("https://x"))


def test_config_errors_follow_language(ui):
    ba, sm, pp = _module("budget_alert"), _module("smtp_mail"), _module("push_phone")
    errors = []
    for fn in (lambda: ba._percents([]), lambda: sm.server_of({"user": "me@corp.example"}),
               lambda: sm.domains_of("x"), lambda: pp.check("", {}), lambda: pp.check("bark", {"device_key": ""})):
        with pytest.raises(ValueError) as e:
            fn()
        errors.append(str(e.value))
    assert _no_cjk(*errors)
    assert "bark.device_key" in errors[-1] and "corp.example" in errors[1]


@pytest.mark.parametrize("name", NAMES)
def test_plugin_title_and_description_are_localized(name, monkeypatch):
    meta = plugins.describe(plugins._entry(plugins.CATALOG, name))
    keys = i18n._plugin_keys()
    assert meta["title"] in keys and meta["description"] in keys    # the checker sees exactly what the UI translates
    for language in ("vi", "en"):
        monkeypatch.setattr(i18n, "_lang", language)
        shown = plugins._shown(meta)
        assert _no_cjk(shown["title"], shown["description"]), (language, shown)
    monkeypatch.setattr(i18n, "_lang", "zh")
    assert plugins._shown(meta)["title"] == meta["title"]


def test_user_plugin_text_is_left_alone(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    assert plugins._shown({"title": "我的插件", "description": "自己写的", "version": "1", "author": "me"})["title"] == "我的插件"


def test_catalog_tool_text_for_the_model_is_english(monkeypatch):
    """Tool schemas and capability lines of shipped plugins are read by the model: no Chinese."""
    monkeypatch.setattr(i18n, "_lang", "vi")
    for name in NAMES:
        m = _module(name)
        for schema in [v for k, v in vars(m).items() if k == "SCHEMA"]:
            blobs = [schema["function"]["description"]] + [p.get("description", "") for p in schema["function"]["parameters"]["properties"].values()]
            assert _no_cjk(*blobs), name
    sm = _module("smtp_mail")
    assert _no_cjk(*(str(e) for e in _raises(sm)))


def _raises(sm):
    out = []
    for fn in (lambda: sm.addresses("x y"), lambda: sm.check_recipients([], [], []),
               lambda: sm.build_message("a@b.co", "", ["c@d.co"], [], "", "x")):
        with pytest.raises(ValueError) as e:
            fn()
        out.append(e.value)
    return out
