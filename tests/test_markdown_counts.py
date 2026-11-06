import pytest
from osa import verification


def test_markdown_body_exact_rule_vi_en():
    text="---\ntitle: Not body\n---\n# Title excluded\nHello world.\n## Another heading\nTiếng Việt ở nhà.\n```python\nprint('not counted')\n```\n    code ignored\nFinal line."
    r=verification.verify({"texts":[{"id":"body","text":text,"mode":"markdown_body","claimed_words":8}]})
    assert r["checks"][0]["words"]==8
    assert r["checks"][0]["mode"]=="markdown_body" and r["overall"]=="PASS"


def test_long_fence_and_plain_compatibility():
    text="# Heading\none two\n````python\n```\nstill code\n````\nthree"
    assert len(verification.markdown_body(text).split())==3
    assert verification.verify({"texts":[{"id":"all","text":text}]})["checks"][0]["words"]==len(text.split())


def test_unclosed_yaml_and_unknown_mode_fail_closed():
    for item in ({"id":"x","text":"---\nmissing end","mode":"markdown_body"},{"id":"x","text":"hi","mode":"invalid"}):
        assert verification.verify({"texts":[item]})["overall"]=="NOT_CHECKED"


def test_blog_previous_headings_scope_regression():
    text="# Title\n"+"word "*186+"\n## "+"heading "*20
    assert len(verification.markdown_body(text).split())==186
    assert verification.verify({"texts":[{"id":"b","text":text,"mode":"markdown_body","min_words":160,"max_words":200,"claimed_words":186}]})["overall"]=="PASS"
