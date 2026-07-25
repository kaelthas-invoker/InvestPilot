from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

from investpilot.storage.models import RepoError

_DATA_DIR_NAME = ".invest-pilot"
_DB_FILE_NAME = "chat.db"
_MIGRATION_FILE_NAMES = ("chat.db", "chat.db-wal", "chat.db-shm")


def open_default_db() -> Path:
    """确保应用数据目录存在，返回默认 DB 路径 `~/.invest-pilot/storage/sqlite/chat.db`。

    - 建 `~/.invest-pilot/` 与 `~/.invest-pilot/storage/sqlite/` 两级目录（mode 0o700）。
    - 若新路径不存在而旧路径 `~/.invest-pilot/chat.db` 存在，则一次性迁移主 DB
      与 WAL/SHM 边车到新位置；迁移后断言旧文件已不在，否则抛 RepoError。
    - 不创建 DB 文件本身（由 schema 层在首次连接时创建），但确保其 mode 为 0o600。
    - 若 `~/.invest-pilot` 已作为普通文件存在，抛出 RepoError。
    """
    old_dir = Path.home() / _DATA_DIR_NAME
    new_dir = old_dir / "storage" / "sqlite"
    new = new_dir / _DB_FILE_NAME

    if old_dir.exists() and not old_dir.is_dir():
        raise RepoError(
            f"{old_dir} 已存在且不是目录，无法用作应用数据根目录。"
        )

    _ensure_dir(old_dir)
    _ensure_dir(new_dir)

    old_db = old_dir / _DB_FILE_NAME
    if not new.exists() and old_db.is_file():
        _migrate_from_old(old_dir, new_dir)
        print(f"已迁移 v0.3.0 历史库 {old_db} → {new}", file=sys.stderr)

    if not new.exists():
        new.touch(mode=0o600)
    new.chmod(0o600)

    return new


def _ensure_dir(path: Path) -> None:
    """确保目录存在；仅在本次新建时设置 mode 0o700，已存在则保留原 mode。"""
    if path.exists():
        return
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)


def _migrate_from_old(old_dir: Path, new_dir: Path) -> None:
    """把旧位置的主 DB 与 WAL/SHM 边车迁移到新位置。"""
    for name in _MIGRATION_FILE_NAMES:
        src = old_dir / name
        if not src.exists():
            continue
        target = new_dir / name
        if target.exists():
            raise RepoError(f"目标已存在 {target}; 无法覆盖")
        try:
            shutil.move(str(src), str(target))
        except OSError as e:
            raise RepoError(f"迁移 {src} 失败: {e}; 请手动处理后重试") from e

    for name in _MIGRATION_FILE_NAMES:
        if (old_dir / name).exists():
            raise RepoError(
                f"迁移后旧文件仍存在 {old_dir / name}; 可能为跨文件系统 "
                f"copy+delete 失败，请手动处理后重试"
            )


def open_db(path: Path) -> sqlite3.Connection:
    """打开一个 SQLite 连接并设置 WAL / 外键 / row_factory。"""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
