from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investpilot.storage import (
    SessionNotFound,
    SessionRepository,
    first_line_preview,
    open_default_db,
)
from investpilot.storage.db import open_db
from investpilot.storage.schema import apply_schema


def _repo(tmp_path: Path) -> SessionRepository:
    return SessionRepository(tmp_path / "chat.db")


_BASE = datetime(2026, 7, 25, tzinfo=timezone.utc)


def _at(seconds: int) -> datetime:
    return _BASE + timedelta(seconds=seconds)


# -- schema ------------------------------------------------------------


def test_apply_schema_is_idempotent(tmp_path: Path) -> None:
    conn = open_db(tmp_path / "chat.db")
    try:
        apply_schema(conn)
        apply_schema(conn)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()
    assert version == 1


# -- create / get ------------------------------------------------------


def test_create_session_returns_hex_uuid(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(provider="anthropic", model="m", system_prompt="p")
    # SPEC §5: id 为 uuid4 hex -> 32 个十六进制字符
    assert len(sid) == 32
    int(sid, 16)  # 必须是合法 hex


def test_create_session_returns_unique_ids(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    a = repo.create_session(provider="anthropic", model="m", system_prompt="p")
    b = repo.create_session(provider="anthropic", model="m", system_prompt="p")
    assert a != b


def test_get_session_unknown_returns_none(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert repo.get_session("does-not-exist") is None


def test_get_session_roundtrip_fields(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(
        provider="openai", model="gpt", system_prompt="sys", now=_at(0)
    )
    meta = repo.get_session(sid)
    assert meta is not None
    assert meta.provider == "openai"
    assert meta.model == "gpt"
    assert meta.system_prompt == "sys"
    assert meta.message_count == 0
    assert meta.created_at == _at(0)
    assert meta.updated_at == _at(0)
    assert meta.created_at.tzinfo is not None


# -- append / load -----------------------------------------------------


def test_append_message_returns_monotonic_seq(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(provider="a", model="m", system_prompt="p")
    seqs = [
        repo.append_message(session_id=sid, role="user", content=f"m{i}")
        for i in range(3)
    ]
    assert seqs == [1, 2, 3]


def test_append_message_updates_session_atomically(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(
        provider="a", model="m", system_prompt="p", now=_at(0)
    )
    repo.append_message(session_id=sid, role="user", content="hi", now=_at(10))
    meta = repo.get_session(sid)
    assert meta is not None
    assert meta.message_count == 1
    assert meta.updated_at == _at(10)


def test_load_messages_seq_ascending(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(provider="a", model="m", system_prompt="p")
    repo.append_message(session_id=sid, role="user", content="one")
    repo.append_message(session_id=sid, role="assistant", content="two")
    repo.append_message(session_id=sid, role="user", content="three")
    msgs = repo.load_messages(sid)
    assert [m.seq for m in msgs] == [1, 2, 3]
    assert [m.content for m in msgs] == ["one", "two", "three"]


def test_load_messages_nonexistent_session_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(SessionNotFound):
        repo.load_messages("missing")


# -- update / finalize -------------------------------------------------


def test_update_message_content_preserves_metadata(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(
        provider="a", model="m", system_prompt="p", now=_at(0)
    )
    seq = repo.append_message(
        session_id=sid, role="assistant", content="", now=_at(5)
    )
    before = repo.get_session(sid)
    orig = repo.load_messages(sid)[0]

    repo.update_message_content(sid, seq, "partial text")

    after = repo.get_session(sid)
    updated = repo.load_messages(sid)[0]
    assert updated.content == "partial text"
    assert updated.seq == orig.seq
    assert updated.created_at == orig.created_at
    assert before is not None and after is not None
    assert after.message_count == before.message_count
    assert after.updated_at == before.updated_at


def test_update_message_content_noop_when_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(provider="a", model="m", system_prompt="p")
    # 不应抛异常
    repo.update_message_content(sid, 999, "nothing")
    assert repo.load_messages(sid) == []


def test_finalize_message_sets_status_final(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(provider="a", model="m", system_prompt="p")
    seq = repo.append_message(
        session_id=sid, role="assistant", content="", status="streaming"
    )
    assert repo.load_messages(sid)[0].status == "streaming"
    repo.finalize_message(sid, seq, "done")
    msg = repo.load_messages(sid)[0]
    assert msg.status == "final"
    assert msg.content == "done"


# -- list_sessions -----------------------------------------------------


def test_list_sessions_only_with_messages_sorted_desc(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    empty = repo.create_session(
        provider="a", model="m", system_prompt="p", now=_at(0)
    )
    older = repo.create_session(
        provider="a", model="m", system_prompt="p", now=_at(0)
    )
    newer = repo.create_session(
        provider="a", model="m", system_prompt="p", now=_at(0)
    )
    repo.append_message(session_id=older, role="user", content="old", now=_at(10))
    repo.append_message(session_id=newer, role="user", content="new", now=_at(20))

    items = repo.list_sessions()
    ids = [i.id for i in items]
    assert empty not in ids
    assert ids == [newer, older]


def test_list_sessions_preview_is_first_user_first_line(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(provider="a", model="m", system_prompt="p")
    repo.append_message(
        session_id=sid, role="user", content="第一行\n第二行"
    )
    repo.append_message(session_id=sid, role="assistant", content="回复")
    repo.append_message(session_id=sid, role="user", content="后续问题")

    items = repo.list_sessions()
    assert len(items) == 1
    assert items[0].preview == "第一行"


# -- first_line_preview ------------------------------------------------


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", ""),
        ("hi", "hi"),
        ("\n下一行", ""),
        ("第一行\n第二行", "第一行"),
        ("a" * 60, "a" * 60),
        ("a" * 61, "a" * 59 + "…"),
        ("中文", "中文"),
    ],
)
def test_first_line_preview(content: str, expected: str) -> None:
    assert first_line_preview(content) == expected


# -- concurrency -------------------------------------------------------


def test_concurrent_append_no_duplicate_seq(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sid = repo.create_session(provider="a", model="m", system_prompt="p")

    results: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        local: list[int] = []
        for _ in range(50):
            seq = repo.append_message(session_id=sid, role="user", content="x")
            local.append(seq)
        with lock:
            results.extend(local)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 100
    assert sorted(results) == list(range(1, 101))
    meta = repo.get_session(sid)
    assert meta is not None
    assert meta.message_count == 100


# -- open_default_db ---------------------------------------------------


def test_open_default_db_creates_dir_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path1 = open_default_db()
    assert path1 == tmp_path / ".invest-pilot" / "chat.db"
    assert (tmp_path / ".invest-pilot").is_dir()
    # DB 文件本身不被创建（由 schema 层负责）
    assert not path1.exists()
    # 幂等
    path2 = open_default_db()
    assert path2 == path1
