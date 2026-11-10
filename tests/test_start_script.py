"""AUDIT-F8：scripts/osa-start.sh 认 OSA_PORT，等 /manifest.json 答了才说 started，超时就报错；osa-stop.sh 跟着用同一个端口。
用一个假的 uv（起一个静态 HTTP 服务）代替真的服务，不用模型、不碰真数据。"""
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="bash scripts")

FAKE_UV = r'''#!/usr/bin/env bash
# called as: uv run uvicorn osa.server:app --host 127.0.0.1 --port N
port="${@: -1}"
case "${FAKE_MODE:-ok}" in
  die) echo "boom: cannot import" ; exit 3 ;;
  hang) exec sleep 60 ;;
esac
python3 -m http.server --bind 127.0.0.1 "$port" --directory "$FAKE_SITE" &
child=$!
trap 'kill $child 2>/dev/null; exit 0' TERM INT
wait $child
'''


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def env(tmp_path):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "uv").write_text(FAKE_UV)
    (bin_ / "uv").chmod(0o755)
    site = tmp_path / "site"
    site.mkdir()
    (site / "manifest.json").write_text("{}")
    e = {k: v for k, v in os.environ.items() if not k.startswith("OSA_")}
    e.update({"PATH": f"{bin_}:{e['PATH']}", "OSA_DATA_DIR": str(tmp_path / "data"), "OSA_DOTENV": "0",
              "FAKE_SITE": str(site), "OSA_PORT": str(_free_port()), "OSA_START_TIMEOUT": "15"})
    yield e
    pid = tmp_path / "data" / "logs" / "osa.pid"
    if pid.exists():
        try:
            os.kill(int(pid.read_text().strip()), 15)
        except (OSError, ValueError):
            pass


def _run(script: str, env: dict, **kw):
    return subprocess.run(["bash", str(ROOT / "scripts" / script)], cwd=ROOT, env={**env, **kw},
                          capture_output=True, text=True, timeout=60)


def test_dry_run_reports_port(env):
    out = _run("osa-start.sh", env, OSA_START_DRY_RUN="1", OSA_PORT="9123")
    assert out.returncode == 0 and "port=9123" in out.stdout
    assert _run("osa-start.sh", env, OSA_START_DRY_RUN="1", OSA_PORT="nope").returncode == 2


def test_waits_for_manifest_then_stop_uses_same_port(env):
    port = env["OSA_PORT"]
    out = _run("osa-start.sh", env)
    assert out.returncode == 0, out.stderr
    assert "started pid=" in out.stdout and f"http://127.0.0.1:{port}" in out.stdout
    import urllib.request
    assert urllib.request.urlopen(f"http://127.0.0.1:{port}/manifest.json", timeout=3).status == 200
    again = _run("osa-start.sh", env)
    assert again.returncode == 0 and "already running" in again.stdout and port in again.stdout
    stop = _run("osa-stop.sh", env)
    assert stop.returncode == 0, stop.stderr
    assert f":{port}" in stop.stdout
    assert not (Path(env["OSA_DATA_DIR"]) / "logs" / "osa.pid").exists()


def test_timeout_fails_with_message(env):
    out = _run("osa-start.sh", env, FAKE_MODE="hang", OSA_START_TIMEOUT="2")
    assert out.returncode == 1
    assert "did not answer" in out.stderr and "/manifest.json" in out.stderr
    assert "started pid" not in out.stdout


def test_server_dies_early_shows_log(env):
    out = _run("osa-start.sh", env, FAKE_MODE="die")
    assert out.returncode == 1 and "exited before it was ready" in out.stderr and "boom" in out.stderr
    assert not (Path(env["OSA_DATA_DIR"]) / "logs" / "osa.pid").exists()
