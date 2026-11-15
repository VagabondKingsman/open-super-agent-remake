"""audit L3: 销毁全部会话 —— 加签的版本号一改，所有旧 cookie 立刻失效，且重启不放回来。"""
import time

import pytest

from osa import auth


@pytest.fixture
def password(monkeypatch):
    monkeypatch.setenv("OSA_PASSWORD", "mật-khẩu-thử")
    before = auth.sessions_revoked()
    yield
    monkeypatch.setattr(auth, "_VER", before)          # 别把版本号带进别的测试
    auth.conn.execute("update auth_meta set v=? where k='ver'", (before,))
    auth.conn.commit()


def test_a_fresh_token_is_valid(password):
    t = auth.new_token()
    assert auth.check_token(t) and auth.check_token(t) > time.time()


def test_revoke_all_kills_every_existing_token(password):
    a, b = auth.new_token(), auth.new_token()
    assert auth.check_token(a) and auth.check_token(b)
    new_ver = auth.revoke_all()
    assert new_ver == auth.sessions_revoked()
    assert auth.check_token(a) is None and auth.check_token(b) is None
    fresh = auth.new_token()
    assert auth.check_token(fresh)                     # 销毁之后新登录的照常有效


def test_the_version_survives_a_restart(password):
    auth.revoke_all()
    dead = auth.new_token()
    auth.revoke_all()
    assert auth.check_token(dead) is None
    monkeypatch_ver = auth._VER
    auth._VER = None                                   # 当成刚启动：从库里重读
    assert auth.sessions_revoked() == monkeypatch_ver
    assert auth.check_token(dead) is None


def test_revoking_is_monotonic(password):
    one = auth.revoke_all()
    two = auth.revoke_all()
    assert two == one + 1
