from __future__ import annotations

import sqlite3
from pathlib import Path

from investpilot.storage.models import RepoError

_DATA_DIR_NAME = ".invest-pilot"
_DB_FILE_NAME = "chat.db"


def open_default_db() -> Path:
    """确保 `~/.invest-pilot/` 目录存在（mode 0o700），返回默认 DB 路径。

    不创建 DB 文件本身（由 schema 层在首次连接时创建）。
    若 `~/.invest-pilot` 已作为普通文件存在，抛出 RepoError。
    """
    data_dir = Path.home() / _DATA_DIR_NAME
    if data_dir.exists() and not data_dir.is_dir():
        raise RepoError(
            f"{data_dir} 已存在且不是目录，无法用作应用数据根目录。"
        )
    data_dir.mkdir(mode=0o700, exist_ok=True)
    return data_dir / _DB_FILE_NAME


def open_db(path: Path) -> sqlite3.Connection:
    """打开一个 SQLite 连接并设置 WAL / 外键 / row_factory。"""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
