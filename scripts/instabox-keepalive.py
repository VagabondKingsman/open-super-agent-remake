"""Giữ máy ảo Instabox khỏi bị nền tảng tạm dừng và khỏi vào cooldown (OPEN-KEEPALIVE).

Instabox áp trần `maxRunMinutes` cho mỗi lượt chạy (480 phút lúc đo 10/11); hết trần là máy bị pause
dù lease còn, rồi còn 5 phút cooldown. Cách chống là gọi OSA đánh thức máy đều đặn: `Computer.start()`
tự resume/wake và mỗi lần wake lại gia hạn nhịp sống. `Idempotency-Key` cho suspend/resume nằm sẵn
trong `osa/computer/instabox.py` (lỗi 400 của 10/11 là của script cũ, ngoài repo).

    .venv/bin/python scripts/instabox-keepalive.py           # chạy mãi, mặc định 200 giây một lần
    .venv/bin/python scripts/instabox-keepalive.py --once    # một lần rồi thoát (cho cron/systemd timer)

Mã thoát: 0 bình thường, 1 không đăng nhập được hoặc máy không lên.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import _paths

BASE = _paths.base()
EVERY = 200          # giây: ngắn hơn nhiều so với trần, đủ thưa để không spam API


def _opener():
    """Đăng nhập bằng cookie; mật khẩu lấy như các script khác (_paths.password())."""
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(BASE + "/login", urllib.parse.urlencode({"password": _paths.password()}).encode(), timeout=15)
    return op


def wake(op, bot_id: int) -> str:
    """Đánh thức máy của bot. Trả về trạng thái máy sau đó."""
    req = urllib.request.Request(f"{BASE}/api/bots/{bot_id}/computer/start", data=b"{}",
                                 headers={"Content-Type": "application/json"})
    op.open(req, timeout=180).read()          # start() 可能要等桌面装好，给足时间
    st = op.open(f"{BASE}/api/bots/{bot_id}/computer", timeout=30).read()
    try:
        return json.loads(st).get("state", "?")
    except ValueError:
        return "?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bot", type=int, default=1, help="bot giữ máy (mặc định 1, bot chính)")
    ap.add_argument("--every", type=int, default=EVERY, help=f"giây giữa hai lần (mặc định {EVERY})")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    try:
        op = _opener()
    except urllib.error.URLError as e:
        print(f"không đăng nhập được OSA: {e}", file=sys.stderr)
        return 1
    while True:
        try:
            state = wake(op, a.bot)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} bot {a.bot}: {state}", flush=True)
        except urllib.error.HTTPError as e:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} HTTP {e.code}: {e.read()[:200]!r}", flush=True)
            op = _opener()                     # phiên hết hạn thì đăng nhập lại
        except urllib.error.URLError as e:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} không gọi được OSA: {e}", flush=True)
        if a.once:
            return 0
        time.sleep(max(30, a.every))


if __name__ == "__main__":
    sys.exit(main())
