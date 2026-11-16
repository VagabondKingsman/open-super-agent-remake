"""OPEN-KEEPALIVE: script giữ máy phải nói được là nó đã thất bại.

Unit systemd chỉ thấy mã thoát và journal. Nếu `--once` luôn trả 0 thì máy bị pause lúc hết trần 480 phút
mà không có dấu hiệu nào (`Restart=on-failure` không chạy, timer + `OnFailure=` không báo), và cũng không
kiểm được "qua một mốc 480 phút" vì không có gì để đếm.

Bốn đường: máy lên → 0; máy vẫn pause/không có máy → 1; `start` trả 500 → 1; đăng nhập hỏng → 1.
Mật khẩu phải đọc được từ biến môi trường (unit chạy không có `.env` của người dùng).
"""
import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "instabox-keepalive.py"


class FakeOSA:
    """OSA tối thiểu: /login, POST /api/bots/<id>/computer/start, GET /api/bots/<id>/computer."""

    def __init__(self, *, state="running", start_status=200, login_status=200, state_json=None):
        self.state = state
        self.state_json = state_json
        self.start_status = start_status
        self.login_status = login_status
        self.calls = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):        # im lặng, pytest không cần log của http.server
                pass

            def _send(self, code, body=b"{}", ctype="application/json", cookie=None):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                if cookie:
                    self.send_header("Set-Cookie", cookie)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(n)
                outer.calls.append(("POST", self.path))
                if self.path == "/login":
                    if outer.login_status != 200:
                        return self._send(outer.login_status, b'{"detail":"wrong password"}')
                    return self._send(200, cookie="session=ok; Path=/")
                if self.path.endswith("/computer/start"):
                    if outer.start_status != 200:
                        return self._send(outer.start_status, b'{"detail":"boom"}')
                    return self._send(200, b'{"ok": true}')
                return self._send(404)

            def do_GET(self):
                outer.calls.append(("GET", self.path))
                if self.path.endswith("/computer"):
                    body = outer.state_json if outer.state_json is not None else json.dumps({"state": outer.state})
                    return self._send(200, body.encode())
                return self._send(404)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


def run_once(osa: FakeOSA, **extra_env):
    env = {k: v for k, v in os.environ.items() if not k.startswith("OSA_")}
    env.update({"OSA_BASE": osa.base, "OSA_PASSWORD": "pw-test", "TZ": "Asia/Ho_Chi_Minh"})
    env.update(extra_env)
    return subprocess.run([sys.executable, str(SCRIPT), "--once"], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=120)


def test_once_exits_0_when_machine_is_running():
    with FakeOSA(state="running") as osa:
        r = run_once(osa)
    assert r.returncode == 0, r.stderr
    assert "bot 1: running" in r.stdout
    assert ("POST", "/api/bots/1/computer/start") in osa.calls


def test_once_exits_1_when_machine_stays_paused():
    with FakeOSA(state="paused") as osa:
        r = run_once(osa)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    assert "paused" in (r.stdout + r.stderr)


def test_once_exits_1_when_start_fails():
    with FakeOSA(start_status=500) as osa:
        r = run_once(osa)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    assert "500" in (r.stdout + r.stderr)


def test_once_exits_1_when_login_fails():
    with FakeOSA(login_status=403) as osa:
        r = run_once(osa)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)


def test_state_that_is_not_json_is_a_failure_not_a_crash():
    with FakeOSA(state_json="<html>502</html>") as osa:
        r = run_once(osa)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    assert "Traceback" not in r.stderr


def test_password_comes_from_env_before_dotenv(monkeypatch):
    """Unit chạy dưới systemd không có `.env`; mọi script khác đã đọc env, `_paths` thì chưa."""
    spec = importlib.util.spec_from_file_location("_paths_keepalive", ROOT / "scripts" / "_paths.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                       # ROOT không có .env: chỉ còn đường env
    monkeypatch.setenv("OSA_PASSWORD", "tu-env")
    assert mod.password() == "tu-env"
