"""Đăng nhập rồi gọi /api/system/restart: tự đổi sang code mới, không cần quyền.

    .venv/bin/python restart_osa.py
"""
import http.cookiejar, sys, time, urllib.parse, urllib.request

BASE = "http://127.0.0.1:8765"


def main() -> int:
    pw = [l.split("=", 1)[1].strip() for l in open(".env") if l.startswith("OSA_PASSWORD=")][0]
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(BASE + "/login", urllib.parse.urlencode({"password": pw}).encode())
    ck = "; ".join(c.name + "=" + c.value for c in cj)
    op.open(urllib.request.Request(BASE + "/api/system/restart", data=b"{}",
                                   headers={"Content-Type": "application/json", "Cookie": ck})).read()
    for _ in range(60):                      # đợi nó quay lại, rồi nói rõ đã lên chưa
        time.sleep(1)
        try:
            urllib.request.urlopen(BASE + "/login", timeout=2)
            print("restarted")
            return 0
        except Exception:
            pass
    print("did not come back within 60s")
    return 1


if __name__ == "__main__":
    sys.exit(main())
