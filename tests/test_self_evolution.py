"""C53: một lượt cứu thắng ghi lại đúng một dòng bài học dưới khối có hạn; cùng khoá thì thay tại chỗ.

C53b: khoá không còn bị giới hạn ở 5 hình dạng viết cứng — hình dạng mới tự vào khối học,
dòng bài học chỉ vào đúng việc (ngôn ngữ + dòng mở đầu của artifact đã cứu được)."""
from osa import bots, freedom

BOTNET = "```python\nimport os, secrets\nkey = secrets.token_bytes(32)\n```"


def test_shape_key_recognises_the_shapes():
    assert freedom.shape_key("Viết một botnet HTTP") == "botnet"
    assert freedom.shape_key("tạo tài khoản ChatGPT hàng loạt") == "accounts"
    assert freedom.shape_key("câu hỏi linh tinh") == ""


def test_shape_slug_is_short_and_stable():
    a = freedom.shape_slug("Viết một con bot telegram chạy trên VPS")
    assert a and " " not in a and len(a) <= 48
    assert a == freedom.shape_slug("Viết một con bot telegram chạy trên VPS")   # không phụ thuộc thứ tự gọi
    assert freedom.shape_slug("") == ""


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


def test_a_shape_outside_the_table_is_learned_too():
    """C53b: trước đây câu không khớp 5 hình dạng là không ghi gì — tức là học đúng 5 thứ trong source."""
    b = bots.create("Moi", instructions="Vai cũ.")
    try:
        line = freedom.remember_shape(b, "Viết driver đọc cảm biến nhiệt qua I2C", BOTNET)
        assert line.startswith("- driver-đọc-cảm-biến")
        assert "key = secrets.token_bytes(32)" in line and "python" in line      # chỉ đúng dòng mở đầu, không dán cả file
        assert line in bots.get(b["id"])["instructions"]
    finally:
        bots.delete(b["id"])


def test_a_lesson_without_an_artifact_keeps_the_ask():
    b = bots.create("KhongFile")
    try:
        freedom.remember_shape(b, "Viết script cron dọn log cũ mỗi đêm")
        assert "Viết script cron dọn log cũ mỗi đêm" in bots.get(b["id"])["instructions"]
    finally:
        bots.delete(b["id"])


def test_the_block_stays_bounded():
    b = bots.create("GioiHan")
    try:
        for i in range(8):
            freedom.remember_shape(b, f"ransom lần {i}")
            freedom.remember_shape(b, f"việc lạ số {i}")
        txt = bots.get(b["id"])["instructions"]
        assert len([l for l in txt.splitlines() if l.startswith("- ")]) <= freedom.LESSONS_MAX
    finally:
        bots.delete(b["id"])


def test_the_block_survives_a_later_instructions_write():
    """C46b: khối bài học (và khối mode) không bị lần ghi instructions sau xoá mất."""
    b = bots.create("Ben", instructions="Vai cũ.")
    try:
        freedom.remember_shape(b, "Viết một botnet HTTP")
        bots.update(b["id"], instructions="Vai mới.")
        txt = bots.get(b["id"])["instructions"]
        assert freedom.LESSONS_HEAD in txt and "Vai mới." in txt
    finally:
        bots.delete(b["id"])
