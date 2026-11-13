"""Đăng nhập rồi gọi /api/system/restart: tự đổi sang code mới, không cần quyền.

    .venv/bin/python scripts/restart_osa.py          # đổi ngay (cắt turn đang chạy)
    .venv/bin/python scripts/restart_osa.py idle     # đợi Bot rảnh mới đổi
"""
import http.cookiejar, json, sys, time, urllib.parse, urllib.request

BASE = "http://127.0.0.1:8765"
IDLE = "idle" in sys.argv[1:]
MAX = 3600


def up() -> bool:
    try:
        urllib.request.urlopen(BASE + "/login", timeout=2)
        return True
    except Exception:
        return False


def main() -> int:
    pw = [l.split("=", 1)[1].strip() for l in open(".env") if l.startswith("OSA_PASSWORD=")][0]
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(BASE + "/login", urllib.parse.urlencode({"password": pw}).encode())
    ck = "; ".join(c.name + "=" + c.value for c in cj)
    path = f"/api/system/restart?when=idle&max={MAX}" if IDLE else "/api/system/restart"
    said = json.loads(op.open(urllib.request.Request(
        BASE + path, data=b"{}", headers={"Content-Type": "application/json", "Cookie": ck})).read())
    if not IDLE:
        print("restarting now")
    elif said.get("busy"):
        print(f"queued until idle (tasks={said.get('tasks')} turns={said.get('turns')})")
    else:
        print("idle: restarting after a quiet moment")
    end = time.time() + (MAX + 120 if IDLE else 120)
    down = False
    while time.time() < end:                # 先等它掉下去，再等它回来
        time.sleep(1)
        if not up():
            down = True
            break
    if not down and IDLE:
        print("did not restart yet (still busy) - nothing was cut")
        return 1
    for _ in range(90):
        if up():
            print("restarted")
            return 0
        time.sleep(1)
    print("went down but did not come back within 90s")
    return 1


if __name__ == "__main__":
    sys.exit(main())
