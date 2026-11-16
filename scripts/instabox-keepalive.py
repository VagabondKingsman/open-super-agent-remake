"""Giữ máy ảo Instabox khỏi bị nền tảng tạm dừng và khỏi vào cooldown (OPEN-KEEPALIVE).

Instabox áp trần `maxRunMinutes` cho mỗi lượt chạy (480 phút lúc đo 10/11); hết trần là máy bị pause
dù lease còn, rồi còn 5 phút cooldown. Cách chống là gọi OSA đánh thức máy đều đặn: `Computer.start()`
tự resume/wake và mỗi lần wake lại gia hạn nhịp sống. `Idempotency-Key` cho suspend/resume nằm sẵn
trong `osa/computer/instabox.py` (lỗi 400 của 10/11 là của script cũ, ngoài repo).

    .venv/bin/python scripts/instabox-keepalive.py           # chạy mãi, mặc định 200 giây một lần
    .venv/bin/python scripts/instabox-keepalive.py --once    # một lần rồi thoát (cho cron/systemd timer)

Mã thoát của `--once`: 0 máy đang chạy (hoặc đang dựng); 1 không đăng nhập được, gọi OSA hỏng, hoặc
máy vẫn pause / không có máy. Chế độ chạy mãi không thoát: lần nào hỏng thì in lý do ra stderr và đi tiếp.
Mỗi dòng có số lần, để kiểm "qua một mốc 480 phút" bằng `journalctl --user -u instabox-keepalive`:
đếm số dòng và so mốc thời gian, không phải tin vào một lần chạy.

Mật khẩu: `OSA_PASSWORD` (biến môi trường, hoặc .env của repo) — unit systemd chạy được mà không cần .env.
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
OK_STATES = ("running", "starting")   # starting = desktop đang dựng, máy vẫn đang được giữ


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _opener():
    """Đăng nhập bằng cookie; mật khẩu lấy như các script khác (_paths.password())."""
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(BASE + "/login", urllib.parse.urlencode({"password": _paths.password()}).encode(), timeout=15)
    return op


def wake(op, bot_id: int) -> str:
    """Đánh thức máy của bot. Trả về trạng thái máy sau đó ('?' nếu OSA không trả JSON)."""
    req = urllib.request.Request(f"{BASE}/api/bots/{bot_id}/computer/start", data=b"{}",
                                 headers={"Content-Type": "application/json"})
    op.open(req, timeout=180).read()          # start() 可能要等桌面装好，给足时间
    st = op.open(f"{BASE}/api/bots/{bot_id}/computer", timeout=30).read()
    try:
        return str(json.loads(st).get("state", "?"))
    except (ValueError, AttributeError):
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
    n = 0
    while True:
        n += 1
        ok = True
        try:
            state = wake(op, a.bot)
        except urllib.error.HTTPError as e:
            ok = False
            print(f"{_now()} lần {n}: HTTP {e.code}: {e.read()[:200]!r}", file=sys.stderr, flush=True)
            try:
                op = _opener()                 # phiên hết hạn thì đăng nhập lại
            except urllib.error.URLError as e2:
                print(f"{_now()} lần {n}: không đăng nhập lại được: {e2}", file=sys.stderr, flush=True)
        except urllib.error.URLError as e:
            ok = False
            print(f"{_now()} lần {n}: không gọi được OSA: {e}", file=sys.stderr, flush=True)
        else:
            ok = state in OK_STATES
            print(f"{_now()} bot {a.bot}: {state} (lần {n})", flush=True)
            if not ok:
                print(f"{_now()} lần {n}: máy không lên (state={state})", file=sys.stderr, flush=True)
        if a.once:
            return 0 if ok else 1
        time.sleep(max(30, a.every))


if __name__ == "__main__":
    sys.exit(main())
