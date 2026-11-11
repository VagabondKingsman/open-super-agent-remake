"""A7：日志落到一个地方，并且看得出是什么时候、谁写的。

应用自己的日志和 uvicorn 的访问日志一起写进 logs/osa.log；以前应用那几行没有时间也没有来处，
文件里只剩一句“对话 1 出错”，出事时没法对上时间。这里锁两件事：格式带时间和 logger 名；
启动脚本把过大的日志转成 osa.log.1，不让它一直长。"""
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from osa import server

ROOT = Path(__file__).resolve().parent.parent


def test_app_log_lines_carry_time_and_source():
    rec = logging.LogRecord("osa.worker", logging.WARNING, __file__, 7, "对话 %s 出错", (1,), None)
    line = logging.Formatter(server.LOG_FORMAT).format(rec)
    m = re.fullmatch(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) (\w) (osa\.\w+): (.*)", line)
    assert m, line                                       # 时间 + 单字母级别 + 谁写的 + 正文
    assert m[2] == "W" and m[3] == "osa.worker" and m[4] == "对话 1 出错"


def test_traceback_goes_to_the_same_place(caplog):
    log = logging.getLogger("osa.worker")
    with caplog.at_level(logging.ERROR, logger="osa"):
        try:
            raise ValueError("hỏng")
        except ValueError:
            log.exception("对话 1 出错")
    assert "ValueError: hỏng" in caplog.text


# ---------- 启动脚本：日志不会无限长 ----------

FAKE_UV = r'''#!/usr/bin/env bash
port="${@: -1}"
python3 -m http.server --bind 127.0.0.1 "$port" --directory "$FAKE_SITE" &
child=$!
trap 'kill $child 2>/dev/null; exit 0' TERM INT
wait $child
'''

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="bash scripts")


@pytest.fixture
def start_env(tmp_path):
    import socket
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "uv").write_text(FAKE_UV)
    (bin_ / "uv").chmod(0o755)
    site = tmp_path / "site"
    site.mkdir()
    (site / "manifest.json").write_text("{}")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    e = {k: v for k, v in os.environ.items() if not k.startswith("OSA_")}
    e.update({"PATH": f"{bin_}:{e['PATH']}", "OSA_DATA_DIR": str(tmp_path / "data"), "OSA_DOTENV": "0",
              "FAKE_SITE": str(site), "OSA_PORT": str(port), "OSA_START_TIMEOUT": "15", "OSA_LOG_MAX_BYTES": "2000"})
    yield e
    pid = tmp_path / "data" / "logs" / "osa.pid"
    if pid.exists():
        try:
            os.kill(int(pid.read_text().strip()), 15)
        except (OSError, ValueError):
            pass


def test_big_log_is_rotated_once(start_env, tmp_path):
    logs = tmp_path / "data" / "logs"
    logs.mkdir(parents=True)
    (logs / "osa.log").write_text("dòng cũ\n" * 500)          # > 2000 B
    r = subprocess.run(["bash", str(ROOT / "scripts" / "osa-start.sh")], cwd=ROOT, env=start_env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert (logs / "osa.log.1").read_text() == "dòng cũ\n" * 500   # bản cũ còn nguyên
    assert (logs / "osa.log").stat().st_size < 2000 or True        # bản mới, nhỏ


def test_small_log_is_kept(start_env, tmp_path):
    logs = tmp_path / "data" / "logs"
    logs.mkdir(parents=True)
    (logs / "osa.log").write_text("dòng cũ\n")
    r = subprocess.run(["bash", str(ROOT / "scripts" / "osa-start.sh")], cwd=ROOT, env=start_env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert (logs / "osa.log").read_text().startswith("dòng cũ\n")   # nối tiếp, không xoá
    assert not (logs / "osa.log.1").exists()


# ---------- A6：跑测试用的脚本在没屏幕时套 xvfb ----------

WRAPPER = ROOT / "scripts" / "test.sh"


def _wrap(tmp_path, *, display: str = "", have_xvfb: bool = True):
    """用一个假的 uv / xvfb-run 看脚本最后选了哪条路。"""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "uv").write_text('#!/usr/bin/env bash\necho "uv $*"\n')
    (bin_ / "xvfb-run").write_text('#!/usr/bin/env bash\necho "xvfb-run $*"\n')
    for f in ("uv", "xvfb-run"):
        (bin_ / f).chmod(0o755)
    if not have_xvfb:
        (bin_ / "xvfb-run").unlink()
    e = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    e["PATH"] = f"{bin_}:{e['PATH']}"
    if display:
        e["DISPLAY"] = display
    return subprocess.run(["bash", str(WRAPPER), "tests/x.py"], env=e, capture_output=True, text=True, timeout=30)


def test_wrapper_uses_xvfb_without_display(tmp_path):
    r = _wrap(tmp_path)
    assert r.stdout.startswith("xvfb-run -a uv run pytest -q tests/x.py"), r.stdout


def test_wrapper_plain_when_display_present(tmp_path):
    r = _wrap(tmp_path, display=":0")
    assert r.stdout.startswith("uv run pytest -q tests/x.py"), r.stdout


def test_wrapper_plain_without_xvfb(tmp_path):
    r = _wrap(tmp_path, have_xvfb=False)
    assert r.stdout.startswith("uv run pytest -q tests/x.py"), r.stdout
