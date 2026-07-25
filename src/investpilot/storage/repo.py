from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from investpilot.storage.db import open_db
from investpilot.storage.models import (
    MessageRecord,
    SessionListItem,
    SessionMetadata,
    SessionNotFound,
)
from investpilot.storage.preview import first_line_preview
from investpilot.storage.schema import apply_schema


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    """序列化为 ISO8601，UTC 用 `Z` 后缀。"""
    return dt.isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    """把存储的 ISO8601 字符串解析回 timezone-aware UTC datetime。"""
    return datetime.fromisoformat(value)


class SessionRepository:
    """会话 / 消息存储仓库（SPEC §13）。

    每个方法打开一条短连接；写方法在 `BEGIN IMMEDIATE` 单事务内完成，
    因此可安全跨线程使用（不共享 connection）。
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    # -- 内部 -----------------------------------------------------------

    def _ensure_schema(self) -> None:
        conn = open_db(self._db_path)
        try:
            apply_schema(conn)
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        return open_db(self._db_path)

    # -- 元数据 ---------------------------------------------------------

    def create_session(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        now: datetime | None = None,
    ) -> str:
        ts = _iso(now or _now())
        session_id = uuid.uuid4().hex
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO session(
                    id, provider, model, system_prompt,
                    created_at, updated_at, message_count
                ) VALUES(?, ?, ?, ?, ?, ?, 0)
                """,
                (session_id, provider, model, system_prompt, ts, ts),
            )
            conn.commit()
        finally:
            conn.close()
        return session_id

    def get_session(self, session_id: str) -> SessionMetadata | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM session WHERE id = ?", (session_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return SessionMetadata(
            id=row["id"],
            provider=row["provider"],
            model=row["model"],
            system_prompt=row["system_prompt"],
            created_at=_parse(row["created_at"]),
            updated_at=_parse(row["updated_at"]),
            message_count=row["message_count"],
        )

    def list_sessions(self) -> list[SessionListItem]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT
                    s.id AS id,
                    s.updated_at AS updated_at,
                    s.message_count AS message_count,
                    (
                        SELECT m.content FROM message m
                        WHERE m.session_id = s.id AND m.role = 'user'
                        ORDER BY m.seq ASC LIMIT 1
                    ) AS first_user_content
                FROM session s
                WHERE s.message_count > 0
                ORDER BY s.updated_at DESC, s.id DESC
                """
            ).fetchall()
        finally:
            conn.close()
        return [
            SessionListItem(
                id=row["id"],
                preview=first_line_preview(row["first_user_content"] or ""),
                updated_at=_parse(row["updated_at"]),
                message_count=row["message_count"],
            )
            for row in rows
        ]

    # -- 消息 -----------------------------------------------------------

    def append_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        status: str = "final",
        now: datetime | None = None,
    ) -> int:
        ts = _iso(now or _now())
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            seq = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM message WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO message(
                    session_id, role, content, status, created_at, seq
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, status, ts, seq),
            )
            conn.execute(
                """
                UPDATE session
                SET updated_at = ?, message_count = message_count + 1
                WHERE id = ?
                """,
                (ts, session_id),
            )
            conn.commit()
        finally:
            conn.close()
        return seq

    def load_messages(self, session_id: str) -> list[MessageRecord]:
        conn = self._connect()
        try:
            exists = conn.execute(
                "SELECT 1 FROM session WHERE id = ?", (session_id,)
            ).fetchone()
            if exists is None:
                raise SessionNotFound(session_id)
            rows = conn.execute(
                """
                SELECT role, content, status, created_at, seq
                FROM message WHERE session_id = ?
                ORDER BY seq ASC
                """,
                (session_id,),
            ).fetchall()
        finally:
            conn.close()
        return [
            MessageRecord(
                role=row["role"],
                content=row["content"],
                status=row["status"],
                created_at=_parse(row["created_at"]),
                seq=row["seq"],
            )
            for row in rows
        ]

    def update_message_content(
        self, session_id: str, seq: int, content: str
    ) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE message SET content = ? WHERE session_id = ? AND seq = ?",
                (content, session_id, seq),
            )
            conn.commit()
        finally:
            conn.close()

    def finalize_message(
        self,
        session_id: str,
        seq: int,
        content: str,
        *,
        now: datetime | None = None,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE message SET content = ?, status = 'final'
                WHERE session_id = ? AND seq = ?
                """,
                (content, session_id, seq),
            )
            conn.commit()
        finally:
            conn.close()
