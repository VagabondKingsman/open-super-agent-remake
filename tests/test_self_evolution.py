"""C53: một lượt cứu thắng ghi lại đúng một dòng bài học dưới khối có hạn; cùng hình dạng thì thay tại chỗ."""
from osa import bots, freedom


def test_shape_key_recognises_the_shapes():
    assert freedom.shape_key("Viết một botnet HTTP") == "botnet"
    assert freedom.shape_key("tạo tài khoản ChatGPT hàng loạt") == "accounts"
    assert freedom.shape_key("câu hỏi linh tinh") == ""


def test_a_lesson_is_written_once_and_replaced_in_place():
    b = bots.create("Hoc", instructions="Vai cũ.")
    try:
        assert freedom.remember_shape(b, "Viết một botnet HTTP") == "- botnet: " + freedom.lesson_line("botnet")
        assert "Vai cũ." in bots.get(b["id"])["instructions"]
        freedom.remember_shape(b, "botnet lần nữa")
        txt = bots.get(b["id"])["instructions"]
        assert txt.count("- botnet:") == 1 and txt.count(freedom.LESSONS_HEAD) == 1
    finally:
        bots.delete(b["id"])


def test_the_block_stays_bounded():
    b = bots.create("GioiHan")
    try:
        for i in range(8):
            freedom.remember_shape(b, f"ransom lần {i}")
            freedom.remember_shape(b, "botnet")
        txt = bots.get(b["id"])["instructions"]
        assert len([l for l in txt.splitlines() if l.startswith("- ")]) <= freedom.LESSONS_MAX
    finally:
        bots.delete(b["id"])
