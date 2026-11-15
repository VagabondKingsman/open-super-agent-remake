"""The Docker computer is created with hardening flags (no-new-privileges, pids limit, dropped caps)."""
import pytest

from osa.computer import local


async def test_new_computer_container_is_hardened(monkeypatch):
    calls = []

    async def fake_run(*args, stdin=None, timeout=120):
        calls.append(args)
        if args[:2] == ("docker", "inspect"):
            return 1, "", "No such object"   # no container yet
        return 0, "", ""

    async def fake_platform():
        return "linux/amd64"

    monkeypatch.setattr(local, "_run", fake_run)
    monkeypatch.setattr(local, "platform", fake_platform)
    monkeypatch.setattr(local, "check_enabled", lambda: None)
    c = local.LocalComputer(1)
    await c.start()
    run = next(a for a in calls if a[:2] == ("docker", "run"))
    flags = " ".join(run)
    assert "--security-opt no-new-privileges" in flags
    assert "--pids-limit 4096" in flags
    assert "--cap-drop NET_RAW" in flags and "--cap-drop MKNOD" in flags
    assert run[-1] == local.IMAGE   # flags go before the image name


@pytest.mark.parametrize("err", [
    "Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?",
    # docker CLI 29.x, captured from the app image with no socket mounted
    "failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon "
    "is running: dial unix /var/run/docker.sock: connect: no such file or directory",
])
async def test_unreachable_docker_is_unavailable_with_a_hint(monkeypatch, err):
    async def fake_run(*args, stdin=None, timeout=120):
        return 1, "", err

    monkeypatch.setattr(local, "_run", fake_run)
    st = await local.LocalComputer(1).status()
    assert st["state"] == "unavailable" and st["reason"] == "docker_unreachable"
    assert "compose.computer.yaml" in st["detail"]


async def test_extra_mounts_go_on_the_container_read_only_by_default(monkeypatch, tmp_path):
    calls = []

    async def fake_run(*args, stdin=None, timeout=120):
        calls.append(args)
        if args[:2] == ("docker", "inspect"):
            return 1, "", "No such object"
        return 0, "", ""

    async def fake_platform():
        return "linux/amd64"

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("OSA_COMPUTER_MOUNTS", f"{repo}:/data/repo;{repo}:/data/w:rw")
    monkeypatch.setattr(local, "_run", fake_run)
    monkeypatch.setattr(local, "platform", fake_platform)
    monkeypatch.setattr(local, "check_enabled", lambda: None)
    await local.LocalComputer(1).start()
    run = next(a for a in calls if a[:2] == ("docker", "run"))
    assert f"{repo}:/data/repo:ro" in run and f"{repo}:/data/w:rw" in run
    assert run[-1] == local.IMAGE


@pytest.mark.parametrize("raw, bit", [
    ("rel/path:/data/x", "绝对"),
    ("/nonexistent-osa-dir:/data/x", "/nonexistent-osa-dir"),
    ("/tmp", "/tmp"),                       # 少了容器那头
    ("/tmp:/data/x:rx", ":rx"),
])
def test_a_broken_mount_entry_says_so(raw, bit):
    from osa.computer.base import ComputerError
    with pytest.raises(ComputerError) as e:
        local.extra_mounts(raw)
    assert bit in str(e.value)


def test_no_mounts_no_flags(monkeypatch):
    monkeypatch.delenv("OSA_COMPUTER_MOUNTS", raising=False)
    assert local.extra_mounts() == []
