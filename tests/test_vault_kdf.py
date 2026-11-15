"""audit L2: 口令派生的 vault 密钥走 scrypt（不是一次 SHA-256），旧条目读到时就地换钥匙。"""
import base64
import hashlib

import pytest
from cryptography.fernet import Fernet

from osa import vault


@pytest.fixture
def passphrase(monkeypatch):
    monkeypatch.setenv("OSA_VAULT_KEY", "mật khẩu dài nhưng vẫn là mật khẩu")
    monkeypatch.setattr(vault, "_fernet", None)
    yield
    monkeypatch.setattr(vault, "_fernet", None)


def test_a_passphrase_goes_through_scrypt(passphrase, monkeypatch):
    seen = {}
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt as Real

    def spy(**kw):
        seen.update(kw)
        return Real(**kw)

    monkeypatch.setattr(vault, "Scrypt", spy)
    vault._key()
    assert seen["n"] == 1 << 15 and seen["r"] == 8 and seen["p"] == 1   # 慢到值得
    assert seen["salt"] and len(seen["salt"]) == 16


def test_the_same_passphrase_gives_the_same_key_and_a_different_salt_is_not_needed(passphrase):
    first = vault._key().encrypt(b"x")
    monkeypatch_reset = vault._fernet
    vault._fernet = None
    assert vault._key().decrypt(first) == b"x"       # salt 存住了，重启解得开


def test_a_fernet_key_is_used_as_is(passphrase, monkeypatch):
    """已经是 Fernet 密钥的 OSA_VAULT_KEY 不派生：直接用的行为不能变。"""
    raw = Fernet.generate_key().decode()
    monkeypatch.setenv("OSA_VAULT_KEY", raw)
    vault._fernet = None
    assert vault._key().decrypt(vault._key().encrypt(b"y")) == b"y"


def test_an_old_sha256_entry_is_re_encrypted_on_read(passphrase):
    """旧版 SHA-256 加密的条目：读得出，而且读一次就换成新钥匙。"""
    old = Fernet(base64.urlsafe_b64encode(hashlib.sha256("mật khẩu dài nhưng vẫn là mật khẩu".encode()).digest()))
    vault.conn.execute("insert or replace into vault values('OLD', ?, 0)", (old.encrypt("giá trị".encode()),))
    vault.conn.commit()
    try:
        assert vault.get("OLD") == "giá trị"
        blob = vault.conn.execute("select ciphertext from vault where name='OLD'").fetchone()[0]
        with pytest.raises(Exception):
            old.decrypt(blob)                 # đã đổi钥匙：旧方式解不开了
        assert vault._key().decrypt(blob) == "giá trị".encode()
    finally:
        vault.conn.execute("delete from vault where name='OLD'")
        vault.conn.commit()
