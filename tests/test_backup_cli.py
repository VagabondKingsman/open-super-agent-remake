"""AUDIT-F7 / F12：备份命令行的输出跟着语言走；导出的备份文件只有自己能读（0600）。"""
import os
import shutil
import stat
import sys

import pytest

from osa import backup, i18n

PASS = "mot-mat-khau-dai-12"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_exported_backup_is_owner_only():
    path, _ = backup.export(PASS)
    try:
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    finally:
        shutil.rmtree(path.parent, ignore_errors=True)


def test_cli_export_output_translated(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(i18n, "_lang", "vi")
    monkeypatch.setenv("OSA_BACKUP_PASSPHRASE", PASS)
    backup.main(["export", "-o", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Đã xuất ra" in out and "Bản sao lưu lúc" in out and "khóa bí mật" in out
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in out)   # 没有漏掉的中文
    files = list(tmp_path.glob("*.osabak"))
    assert len(files) == 1 and stat.S_IMODE(files[0].stat().st_mode) == 0o600


def test_summary_english_plural(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "en")
    s = backup._summary({"counts": {"bots": 1, "messages": 3}, "secrets": 2, "version": "1.0", "created": 0})
    assert "1 bot" in s and "3 messages" in s and "2 secrets" in s and s.startswith("Backup from")


def test_cli_error_translated(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "en")
    monkeypatch.setattr(backup, "key_matches", lambda: False)
    with pytest.raises(SystemExit) as e:
        backup.main(["export"])
    assert str(e.value).startswith("Failed: the vault master key")


def test_no_password_warning_translated(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", "vi")
    assert i18n.t("未设置 OSA_PASSWORD：网页不用登录就能访问，只能在本机或内网使用").startswith("Chưa đặt OSA_PASSWORD")
    import inspect
    from osa import server
    assert 'i18n.t("未设置 OSA_PASSWORD' in inspect.getsource(server.lifespan)
