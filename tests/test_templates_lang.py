"""Built-in bot templates: vi/en/zh versions, fallback order, and the vi validator."""
import pytest

from osa import i18n, templates


def _ids():
    return sorted(p.stem for p in templates.BUILTIN.glob("*.yaml"))


@pytest.mark.parametrize("tid", _ids())
def test_every_builtin_has_clean_vi_block(tid):
    text = templates.builtin_text(tid)
    assert templates.vi_problems(text) == []
    vi, en, zh = (templates.parse(text, lang) for lang in ("vi", "en", "zh"))
    assert vi["name"] != en["name"] != zh["name"]
    assert not i18n.CJK.search(" ".join([vi["name"], vi["description"], vi["instructions"]]
                                         + [s["name"] + s["description"] + s["body"] for s in vi["skills"]]
                                         + [r["name"] for r in vi["routines"]]))
    assert len(vi["skills"]) == len(en["skills"]) == len(zh["skills"])
    assert [r["trigger"] for r in vi["routines"]] == [r["trigger"] for r in zh["routines"]]
    # routines keep pointing at an installed skill after the rename
    for r in vi["routines"]:
        assert r["skill"] in {s["name"] for s in vi["skills"]}


def test_parse_follows_ui_language(monkeypatch):
    text = templates.builtin_text("news")
    monkeypatch.setattr(i18n, "_lang", "vi")
    assert templates.parse(text)["name"] == "Trợ lý tin tức"
    monkeypatch.setattr(i18n, "_lang", "en")
    assert templates.parse(text)["name"] == "News assistant"
    monkeypatch.setattr(i18n, "_lang", "zh")
    assert templates.parse(text)["name"] == "资讯助手"


def test_vi_falls_back_field_by_field_to_en_then_zh():
    text = ("osa_template: 1\nname: 原文\ndescription: 中文说明\ninstructions: 中文人设\n"
            "skills:\n  - {name: 技能, body: 做点事}\nroutines:\n  - {name: 例行, skill: 技能, prompt: 干活, trigger: {kind: daily, times: ['08:00']}}\n"
            "en:\n  name: English name\n  description: English description\n"
            "  skills:\n    - {name: skill-en, body: do things}\n  routines:\n    - {name: routine-en}\n"
            "vi:\n  name: Tên Việt\n")
    vi = templates.parse(text, "vi")
    assert vi["name"] == "Tên Việt"
    assert vi["description"] == "English description"
    assert vi["instructions"] == "中文人设"
    assert vi["skills"][0]["name"] == "skill-en" and vi["routines"][0]["skill"] == "skill-en"
    assert vi["routines"][0]["prompt"] == "干活"
    # en does not see the vi block; zh sees neither
    assert templates.parse(text, "en")["name"] == "English name"
    assert templates.parse(text, "zh")["name"] == "原文"


def test_vi_without_en_overlays_zh_source():
    text = "osa_template: 1\nname: 原文\ndescription: 中文说明\nvi:\n  name: Tên Việt\n"
    t = templates.parse(text, "vi")
    assert (t["name"], t["description"]) == ("Tên Việt", "中文说明")


def test_vi_block_structure_is_checked(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "en")
    with pytest.raises(ValueError, match="vi"):
        templates.parse("osa_template: 1\nname: x\nvi:\n  bogus: 1\n")
    with pytest.raises(ValueError, match="vi.skills"):
        templates.parse("osa_template: 1\nname: x\nskills: [{name: a, body: b}]\nvi:\n  skills: []\n")


def test_vi_problems_flags_drift():
    base = templates.builtin_text("news")
    assert templates.vi_problems(base) == []
    # wrong @app, lost save_page, leftover Chinese, copied English
    bad = (base.replace("dùng @exa", "dùng @fetch").replace("bằng save_page", "bằng trang")
           .replace("Trợ lý tin tức", "资讯助手"))
    found = " ".join(templates.vi_problems(bad))
    assert "vi.skills[0].body" in found and "vi.name 里还有中文" in found
    copied = base.replace("description: Mỗi sáng gom tin mới về các lĩnh vực bạn quan tâm thành một bản tin sáng và lưu vào Thư viện",
                          "description: Every morning, turns news on the topics you follow into a brief and saves it to your Library")
    assert any("vi.description 和 en 一样" in p for p in templates.vi_problems(copied))
    assert templates.vi_problems("osa_template: 1\nname: x\n") == []
