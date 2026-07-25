from __future__ import annotations

import sqlite3

_SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE session (
  id            TEXT PRIMARY KEY,
  provider      TEXT NOT NULL,
  model         TEXT NOT NULL,
  system_prompt TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL,
  message_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_session_updated_at ON session(updated_at DESC);

CREATE TABLE message (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES session(id) ON DELETE CASCADE,
  role       TEXT NOT NULL,
  content    TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'final',
  created_at TEXT NOT NULL,
  seq        INTEGER NOT NULL,
  UNIQUE(session_id, seq)
);

CREATE INDEX idx_message_session_seq ON message(session_id, seq);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    """幂等地应用 baseline schema（SPEC §5）。

    读取 `PRAGMA user_version`；为 0 时执行 DDL 并写入 user_version=1；
    非 0 时不做任何改动。
    """
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version == 0:
        conn.executescript(_DDL)
        conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        conn.commit()
