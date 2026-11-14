"""dump prompt：能开着不关——只留最新的几个，太大的 body 直接跳过。"""
import os

from osa import providers


def _dump(tmp_path, monkeypatch, keep: int | None = 500, max_mb: float = 4):
    d = tmp_path / "prompts"
    monkeypatch.setenv("OSA_PROMPT_DUMP", str(d))
    if keep is None:
        monkeypatch.delenv("OSA_PROMPT_DUMP_KEEP", raising=False)
    else:
        monkeypatch.setenv("OSA_PROMPT_DUMP_KEEP", str(keep))
    monkeypatch.setenv("OSA_PROMPT_DUMP_MAX_MB", str(max_mb))
    d.mkdir()
    return d


def _body(name: str) -> dict:
    return {"model": name, "messages": [{"role": "user", "content": name}]}


def test_dump_writes_one_file_per_request(tmp_path, monkeypatch):
    d = _dump(tmp_path, monkeypatch, keep=0)
    providers.dump_prompt(_body("m"))
    assert len(list(d.glob("*.json"))) == 1


def test_dump_keeps_only_the_newest(tmp_path, monkeypatch):
    d = _dump(tmp_path, monkeypatch, keep=3)
    for i in range(5):
        providers.dump_prompt(_body(f"m{i}"))
    kept = sorted(d.glob("*.json"))
    assert len(kept) == 3
    # mtime tăng dần theo thứ tự ghi → 3 tệp mới nhất còn lại là m2, m3, m4
    for i, p in enumerate(kept):
        os.utime(p, (1000 + i, 1000 + i))
    providers.dump_prompt(_body("m5"))
    os.utime(sorted(d.glob("*.json"))[-1], (2000, 2000))
    assert len(list(d.glob("*.json"))) == 3
    assert not any(p.name.endswith("-m0.json") for p in d.glob("*.json"))


def test_dump_skips_a_body_over_the_limit(tmp_path, monkeypatch):
    d = _dump(tmp_path, monkeypatch, keep=0, max_mb=0.001)
    providers.dump_prompt({"model": "m", "messages": [{"role": "user", "content": "x" * 5000}]})
    assert list(d.glob("*.json")) == []
    providers.dump_prompt(_body("nhỏ"))
    assert len(list(d.glob("*.json"))) == 1


def test_dump_off_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("OSA_PROMPT_DUMP", raising=False)
    monkeypatch.setenv("OSA_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    providers.dump_prompt(_body("m"))
    assert not (tmp_path / "data" / "prompts").exists()
