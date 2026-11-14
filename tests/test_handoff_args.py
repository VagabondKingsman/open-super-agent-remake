"""C56: handoff 的工具参数模型常写成 bot/note，处理要认，认不出就还名单。"""
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "osa" / "router.py"


def test_the_handler_accepts_bot_and_note():
    src = SRC.read_text(encoding="utf-8")
    assert 'args.get("to") or args.get("bot")' in src
    assert 'args.get("request") or args.get("note")' in src
    assert "the members are" in src      # 认不出时把名单还回去，模型能重试
