"""vault.key is created 0600 from the start, never written first and chmod-ed afterwards."""
import os
import stat
from pathlib import Path

from osa import vault


def test_vault_key_is_private_from_creation(tmp_path, monkeypatch):
    monkeypatch.delenv("OSA_VAULT_KEY", raising=False)
    monkeypatch.setattr(vault, "db_path", tmp_path / "osa.db")
    monkeypatch.setattr(vault, "_fernet", None)

    def no_late_chmod(self, mode, *a, **kw):
        raise AssertionError(f"chmod after write leaves {self.name} readable for a moment")
    monkeypatch.setattr(Path, "chmod", no_late_chmod)
    old = os.umask(0)
    try:
        vault._key()
    finally:
        os.umask(old)
    key = tmp_path / "vault.key"
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    first = key.read_bytes()
    monkeypatch.setattr(vault, "_fernet", None)
    vault._key()
    assert key.read_bytes() == first   # existing key is reused, not replaced
