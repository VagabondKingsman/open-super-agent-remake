"""OSA-029 R4: Docker 默认时区是越南（Asia/Ho_Chi_Minh），compose、Dockerfile、文档和 .env.example 要一致。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TZ = "Asia/Ho_Chi_Minh"


def test_compose_default_tz():
    assert f"TZ: ${{TZ:-{TZ}}}" in (ROOT / "compose.yaml").read_text()


def test_dockerfile_default_tz():
    assert re.search(rf"^\s*TZ={TZ}\b", (ROOT / "Dockerfile").read_text(), re.M)


def test_docs_and_env_example_state_the_same_default():
    assert f"| `TZ` | `{TZ}` |" in (ROOT / "docs/docker.md").read_text()
    assert f"# TZ={TZ}" in (ROOT / ".env.example").read_text()
