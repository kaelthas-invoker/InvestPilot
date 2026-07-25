from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SessionMetadata:
    """会话元数据（对应 session 表一行）。datetimes 为 timezone-aware UTC。"""

    id: str
    provider: str
    model: str
    system_prompt: str
    created_at: datetime
    updated_at: datetime
    message_count: int


@dataclass(frozen=True)
class SessionListItem:
    """`/resume` 列表项。"""

    id: str
    preview: str
    updated_at: datetime
    message_count: int


@dataclass(frozen=True)
class MessageRecord:
    """单条消息记录。datetimes 为 timezone-aware UTC。"""

    role: str
    content: str
    status: str
    created_at: datetime
    seq: int


class SessionNotFound(LookupError):
    """请求的 session_id 不存在。"""


class RepoError(RuntimeError):
    """存储层不可恢复错误（如数据根路径冲突）。"""
