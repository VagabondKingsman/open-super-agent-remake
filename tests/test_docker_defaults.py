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


def test_docker_doc_clones_the_remake_branch():
    """AUDIT-F10：docs/docker.md 让人 clone remake 的 i18n-vi，不是 upstream。"""
    text = (ROOT / "docs/docker.md").read_text()
    assert "git clone -b i18n-vi https://github.com/VagabondKingsman/open-super-agent-remake.git" in text
    assert "git clone https://github.com/kadaliao/open-super-agent.git" not in text
