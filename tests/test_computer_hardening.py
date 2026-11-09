"""The Docker computer is created with hardening flags (no-new-privileges, pids limit, dropped caps)."""
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
