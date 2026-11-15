"""保险库：加密保存密钥（API key、token 等）。

明文只在两个地方出现：用户在界面上录入的那一刻，以及启动应用时注入进程环境变量。
接口和模型只能看到名字。主密钥优先取环境变量 OSA_VAULT_KEY，没有就在数据目录生成一个（权限 600）。

口令（不是 Fernet 格式的 OSA_VAULT_KEY）要派生成密钥：旧版直接 SHA-256，一个口令试一次就那么快，
弱口令可离线硬撞（audit L2）。现在走 scrypt（n=2**15, r=8, p=1），salt 存库里；旧条目在第一次
读到时就地换成新密钥重新加密，所以不用停机迁移、也不会把旧值留在库里。
"""
import base64
import hashlib
import os
import re
import time

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from . import i18n
from .memory import conn, db_path

conn.execute("create table if not exists vault(name text primary key, ciphertext blob, created real)")
conn.execute("create table if not exists vault_meta(k text primary key, v blob)")
conn.commit()

NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
SCRYPT = {"n": 1 << 15, "r": 8, "p": 1}   # ~64 MiB, 十几毫秒：够慢，又不会让每次启动都等
_fernet: Fernet | None = None


def _raw() -> str:
    """主密钥原文：环境变量，或者数据目录里的 vault.key（没有就生成）。"""
    raw = os.environ.get("OSA_VAULT_KEY")
    if raw:
        return raw.strip()
    f = db_path.parent / "vault.key"
    if not f.exists():
        # Create with 0600 from the start: write-then-chmod leaves the key world-readable for a moment.
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(Fernet.generate_key())
    return f.read_text().strip()


def _salt() -> bytes:
    """口令派生的 salt：一次生成，之后一直用它（换 salt 等于换密钥，旧密文就都解不开了）。"""
    r = conn.execute("select v from vault_meta where k='salt'").fetchone()
    if r:
        return r[0]
    s = os.urandom(16)
    conn.execute("insert or replace into vault_meta values('salt', ?)", (s,))
    conn.commit()
    return s


def _from_secret(raw: str) -> Fernet:
    """口令 -> Fernet。口令已经长成 Fernet 密钥就照用，否则 scrypt 派生。"""
    try:
        return Fernet(raw.encode())
    except ValueError:
        pass
    key = Scrypt(salt=_salt(), length=32, **SCRYPT).derive(raw.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def _legacy(raw: str) -> Fernet | None:
    """旧版的派生方式（SHA-256 一口吃下）：只用来读旧密文，读到就换钥匙。"""
    try:
        Fernet(raw.encode())
    except ValueError:
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest()))
    return None


def _key() -> Fernet:
    global _fernet
    if not _fernet:
        _fernet = _from_secret(_raw())
    return _fernet


def put(name: str, value: str):
    if not NAME.match(name):
        raise ValueError(i18n.t("名字只能用字母、数字和下划线，且不能以数字开头"))
    if not value:
        raise ValueError(i18n.t("值不能为空"))
    conn.execute("insert or replace into vault values(?,?,?)", (name, _key().encrypt(value.encode()), time.time()))
    conn.commit()


def get(name: str) -> str | None:
    r = conn.execute("select ciphertext from vault where name=?", (name,)).fetchone()
    if not r:
        return None
    try:
        return _key().decrypt(r[0]).decode()
    except InvalidToken:
        pass
    if (old := _legacy(_raw())) is not None:   # 旧派生方式加密的条目：解开就地换成新密钥
        try:
            value = old.decrypt(r[0]).decode()
        except InvalidToken:
            return None
        put(name, value)
        return value
    return None   # 主密钥换过了，旧值解不开


def delete(name: str):
    conn.execute("delete from vault where name=?", (name,))
    conn.commit()


def names() -> list[dict]:
    return [{"name": n, "created": c, "ok": get(n) is not None}
            for n, c in conn.execute("select name, created from vault order by name")]
