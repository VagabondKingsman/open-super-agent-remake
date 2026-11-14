"""Nơi script tìm dữ liệu của OSA: OSA_DATA_DIR, rồi .env, rồi thư mục thật của máy này.

Trước 2026-11-14 ba script ghi cứng /home/boxes/osa-data nên chạy trên máy khác là đọc/ghi nhầm.
Chỉ stdlib, để script không phải import osa.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FALLBACK = Path("/home/boxes/osa-data")


def _dotenv(key: str) -> str:
    try:
        text = (ROOT / ".env").read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def data_dir() -> Path:
    """OSA_DATA_DIR (env rồi .env) nếu thư mục có thật, không thì thư mục mặc định của máy."""
    raw = os.environ.get("OSA_DATA_DIR", "").strip() or _dotenv("OSA_DATA_DIR")
    if raw:
        p = Path(raw).expanduser()
        if p.is_dir():
            return p
    return FALLBACK


def db(ro: bool = True) -> sqlite3.Connection:
    p = data_dir() / "osa.db"
    if ro:
        return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
    return sqlite3.connect(p, timeout=10)


def password() -> str:
    pw = _dotenv("OSA_PASSWORD")
    if not pw:
        raise SystemExit("OSA_PASSWORD không có trong .env")
    return pw
