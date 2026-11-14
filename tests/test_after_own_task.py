"""C58: chỉ những lượt派活 mà có hứa “sẽ dán output” mới đánh thức lại; không hứa thì im."""
from osa import router


def _r():
    r = object.__new__(router.Router)
    return r


def test_promise_words_are_recognised():
    r = _r()

    class T:
        id = -1
    assert any(k in " ".join(router.Router.PROMISE) for k in ("sẽ dán", "paste", "báo lại ngay"))
