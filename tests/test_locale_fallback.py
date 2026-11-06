"""Catalog faults must not crash import. Missing VI uses EN; missing EN uses source Chinese."""
import logging
import shutil
from pathlib import Path

import pytest

from osa import i18n

KEY = "任务 #{id}"
PLURAL = "每 {n} 分钟"
PLAIN = "没有这个 Bot"
BOTH = "允许一次"


@pytest.fixture
def catalogs(tmp_path, monkeypatch):
    dest = tmp_path / "locales"
    shutil.copytree(Path(i18n.__file__).resolve().parent / "locales", dest)
    saved = (i18n.EN, i18n.VI)
    monkeypatch.setattr(i18n, "_catalog_path", lambda name: dest / f"{name}.json")

    def reload():
        i18n._load_locales()

    yield dest, reload
    i18n.EN, i18n.VI = saved


def _warnings(caplog):
    return [r for r in caplog.records if r.levelno >= logging.WARNING and r.name == "osa.i18n"]


def test_missing_vi_falls_back_to_english(catalogs, caplog):
    dest, reload = catalogs
    (dest / "vi.json").unlink()
    with caplog.at_level(logging.WARNING, logger="osa.i18n"):
        reload()
    assert i18n.VI == {} and i18n.EN[KEY] == "Task #{id}"
    assert any("vi.json" in r.getMessage() for r in _warnings(caplog))
    assert i18n.t(KEY, in_lang="vi", id=7) == "Task #7"
    assert i18n.t(PLURAL, in_lang="vi", n=1) == "Every minute"
    assert i18n.t(PLURAL, in_lang="vi", n=3) == "Every 3 minutes"
    assert i18n.t(PLAIN, in_lang="vi") == "Bot not found"
    assert i18n.t(KEY, in_lang="en", id=7) == "Task #7"
    assert i18n.t(KEY, in_lang="zh", id=7) == "任务 #7"
    assert i18n.both(BOTH) == {"允许一次", "Allow once"}


def test_missing_en_falls_back_to_source(catalogs, caplog):
    dest, reload = catalogs
    (dest / "en.json").unlink()
    with caplog.at_level(logging.WARNING, logger="osa.i18n"):
        reload()
    assert i18n.EN == {} and i18n.VI[KEY] == "Tác vụ #{id}"
    assert any("en.json" in r.getMessage() for r in _warnings(caplog))
    assert i18n.t(KEY, in_lang="vi", id=7) == "Tác vụ #7"
    assert i18n.t(PLURAL, in_lang="vi", n=3) == "Mỗi 3 phút"
    assert i18n.t(PLAIN, in_lang="vi") == "Không có Bot này"
    assert i18n.t(KEY, in_lang="en", id=7) == "任务 #7"
    assert i18n.t(PLURAL, in_lang="en", n=3) == "每 3 分钟"
    assert i18n.t(PLAIN, in_lang="en") == "没有这个 Bot"
    assert i18n.t(KEY, in_lang="zh", id=7) == "任务 #7"
    assert i18n.both(BOTH) == {"允许一次", "Cho phép một lần"}


def test_both_catalogs_missing_use_source(catalogs, caplog):
    dest, reload = catalogs
    (dest / "vi.json").unlink()
    (dest / "en.json").unlink()
    with caplog.at_level(logging.WARNING, logger="osa.i18n"):
        reload()
    assert i18n.EN == {} and i18n.VI == {}
    messages = [r.getMessage() for r in _warnings(caplog)]
    assert any("vi.json" in message for message in messages)
    assert any("en.json" in message for message in messages)
    for language in ("vi", "en", "zh"):
        assert i18n.t(KEY, in_lang=language, id=7) == "任务 #7"
        assert i18n.t(PLURAL, in_lang=language, n=3) == "每 3 分钟"
        assert i18n.t(PLAIN, in_lang=language) == "没有这个 Bot"
    assert i18n.both(BOTH) == {"允许一次"}


def test_invalid_json_catalog_is_empty(catalogs, caplog):
    dest, reload = catalogs
    (dest / "vi.json").write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="osa.i18n"):
        reload()
    assert i18n.VI == {} and i18n.EN
    assert any("vi.json" in r.getMessage() for r in _warnings(caplog))
    assert i18n.t(KEY, in_lang="vi", id=7) == "Task #7"
    assert i18n.t(PLURAL, in_lang="vi", n=1) == "Every minute"
    assert i18n.t(PLURAL, in_lang="vi", n=3) == "Every 3 minutes"
    assert i18n.t(PLAIN, in_lang="vi") == "Bot not found"
    assert i18n.t(KEY, in_lang="en", id=7) == "Task #7"
    assert i18n.t(KEY, in_lang="zh", id=7) == "任务 #7"


def test_non_object_json_catalog_is_empty(catalogs, caplog):
    dest, reload = catalogs
    (dest / "en.json").write_text("[1, 2]", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="osa.i18n"):
        reload()
    assert i18n.EN == {} and i18n.VI
    assert any("en.json" in r.getMessage() for r in _warnings(caplog))
    assert i18n.t(KEY, in_lang="en", id=7) == "任务 #7"
    assert i18n.t(PLURAL, in_lang="en", n=4) == "每 4 分钟"
    assert i18n.t(PLAIN, in_lang="en") == "没有这个 Bot"
    assert i18n.t(KEY, in_lang="vi", id=7) == "Tác vụ #7"
    assert i18n.t(PLURAL, in_lang="vi", n=3) == "Mỗi 3 phút"
    assert i18n.t(KEY, in_lang="zh", id=7) == "任务 #7"


def test_unreadable_catalog_is_empty(catalogs, caplog):
    dest, reload = catalogs
    path = dest / "vi.json"
    path.chmod(0)
    try:
        with caplog.at_level(logging.WARNING, logger="osa.i18n"):
            reload()
        assert i18n.VI == {} and i18n.EN
        assert any("vi.json" in r.getMessage() for r in _warnings(caplog))
        assert i18n.t(KEY, in_lang="vi", id=7) == "Task #7"
        assert i18n.t(PLURAL, in_lang="vi", n=3) == "Every 3 minutes"
        assert i18n.t(KEY, in_lang="en", id=7) == "Task #7"
        assert i18n.t(KEY, in_lang="zh", id=7) == "任务 #7"
    finally:
        path.chmod(0o644)
