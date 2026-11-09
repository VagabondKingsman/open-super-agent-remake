"""OSA_DATA_DIR 把数据库、密钥、应用清单和工作目录放到指定目录，代码目录可以只读。"""
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import ROOT, TMP

PROBE = """
import json
from osa import auth, backup, catalog, config, mcp_hub, memory, prices
from osa.computer.local import LocalComputer
auth._signing_key()
print(json.dumps({"db": str(memory.db_path), "backup_db": str(backup.DB), "apps": str(backup.APPS),
                  "catalog_apps": str(catalog.LOCAL), "workspace": str(mcp_hub.WORKSPACE),
                  "catalog_workspace": str(catalog.WORKSPACE), "prices": str(prices.FILE),
                  "computer": LocalComputer(1).data, "db_outside": config.db_outside_data_dir()}))
"""


def _paths(**env) -> dict:
    full = {k: v for k, v in os.environ.items() if k not in ("OSA_DATA_DIR", "OSA_CONFIG")}
    full.update(env)
    full["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=full, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def _runtime_files(root: Path) -> set[str]:
    found = set()
    for name in ("data", "logs"):
        base = root / name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            found.add(str(path.relative_to(root)))
    return found


def test_everything_goes_into_the_data_dir():
    data = TMP / "desktop-data"
    before = _runtime_files(ROOT)
    p = _paths(OSA_DATA_DIR=str(data), OSA_CONFIG=str(ROOT / "config.yaml"))   # 仓库里的配置：memory.db 是相对路径 data/osa.db
    assert p["db"] == p["backup_db"] == str(data / "osa.db")
    assert p["apps"] == p["catalog_apps"] == str(data / "apps")
    assert p["workspace"] == p["catalog_workspace"] == str(data / "workspace")
    assert p["prices"] == str(data / "model-prices.json")
    assert p["computer"] == str(data / "computers" / "shared")
    assert (data / "osa.db").exists() and (data / "session.key").exists()
    assert not Path(p["db"]).is_relative_to(ROOT)
    assert _runtime_files(ROOT) == before


def test_absolute_db_path_still_wins():
    data = TMP / "desktop-data-2"
    p = _paths(OSA_DATA_DIR=str(data), OSA_CONFIG=str(TMP / "config.yaml"))     # 测试用的配置：memory.db 是绝对路径
    assert p["db"] == str(TMP / "osa.db")
    assert p["apps"] == str(data / "apps")


def test_default_is_unchanged():
    p = _paths(OSA_CONFIG=str(TMP / "config.yaml"))
    assert p["db"] == str(TMP / "osa.db")
    assert p["apps"] == str(ROOT / "data" / "apps")
    assert p["workspace"] == str(ROOT / "data" / "workspace")
    assert p["computer"] == str(ROOT / "data" / "computers" / "shared")


def test_start_script_puts_logs_outside_the_repo():
    data = TMP / "start-data"
    before = _runtime_files(ROOT)
    env = {k: v for k, v in os.environ.items() if k not in ("OSA_DATA_DIR", "OSA_START_DRY_RUN")}
    env.update({"OSA_DATA_DIR": str(data), "OSA_START_DRY_RUN": "1", "OSA_DOTENV": "0"})
    out = subprocess.run(["bash", str(ROOT / "scripts/osa-start.sh")], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    lines = dict(part.split("=", 1) for part in out.stdout.splitlines() if "=" in part)
    assert lines["data"] == str(data)
    assert lines["log"] == str(data / "logs" / "osa.log")
    assert lines["pid"] == str(data / "logs" / "osa.pid")
    assert (data / "logs").is_dir()
    assert not (ROOT / "logs" / "osa.log").exists() or "logs/osa.log" in before
    assert _runtime_files(ROOT) == before
