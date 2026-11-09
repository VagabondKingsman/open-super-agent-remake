"""回复语言的轻量检查：界面是越南语或英文，模型的回复却大半是中文时记一笔。只提醒，不拦、不改、不额外调用模型。

判断很保守，宁可漏报也不误报：
- 先去掉代码块、行内代码、网址、引用行（> 开头）、引号里的原文和 [附件] 标记：这些可以合理地是中文。
- 剩下的文字里，汉字不少于 MIN_HAN 个，且占（汉字 + 拉丁字母）的比例不低于 RATIO，才算。
- 用户自己的请求就是中文的（模型的规则是“用户用哪种语言就用哪种”），不算。
- 界面是中文时不检查。

记在两处：日志里一条警告；回复消息（或任务结果消息）的 meta.lang_flag，任务另在过程记录里写一条提示。
"""
import logging
import re
from . import i18n

log = logging.getLogger(__name__)

MIN_HAN = 20
RATIO = 0.6
USER_RATIO = 0.3   # 用户请求里汉字占这么多，就当用户在用中文
_HAN = re.compile(r"[\u3400-\u9fff]")
_LATIN = re.compile(r"[A-Za-z\u00c0-\u024f\u1e00-\u1eff]")
_NOISE = [
    re.compile(r"```.*?(?:```|\Z)|~~~.*?(?:~~~|\Z)", re.S),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"https?://\S+|www\.\S+"),
    re.compile(r"^[ \t]*>.*$", re.M),
    re.compile(r"“[^”\n]{0,200}”|\"[^\"\n]{0,200}\"|「[^」\n]{0,200}」|『[^』\n]{0,200}』|《[^》\n]{0,200}》"),
    re.compile(r"\[附件\]"),   # 附件标记是存下来的约定，不是语言
]


def _counts(text: str) -> tuple[int, int]:
    for rx in _NOISE:
        text = rx.sub(" ", text or "")
    return len(_HAN.findall(text)), len(_LATIN.findall(text))


def check(text: str, request: str = "", ui: str | None = None) -> dict | None:
    """回复 text 大半是中文、而界面语言是 vi / en 时返回 {"ui", "han", "latin"}，否则 None。
    request 是它在回应的那条用户消息（或任务目标）。"""
    ui = ui or i18n.lang()
    if ui not in ("vi", "en"):
        return None
    han, latin = _counts(text)
    if han < MIN_HAN or han / (han + latin) < RATIO:
        return None
    ask_han, ask_latin = _counts(request)
    if ask_han and ask_han / (ask_han + ask_latin) >= USER_RATIO:
        return None
    return {"ui": ui, "han": han, "latin": latin}


def record(text: str, request: str = "", where: str = "") -> dict | None:
    """check() 加一条日志。返回的 flag 由调用的地方存进消息的 meta；没问题返回 None。"""
    flag = check(text, request)
    if flag:
        log.warning("回复语言和界面语言（%s）不一致：%s，汉字 %d、拉丁字母 %d", flag["ui"], where or "-", flag["han"], flag["latin"])
    return flag
