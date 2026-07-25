from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investpilot.assistant.session import ChatSession
from investpilot.providers.base import Message, StreamChunk
from investpilot.storage import SessionNotFound, SessionRepository


class _ScriptedProvider:
    def __init__(self) -> None:
        self.calls: list[list[Message]] = []

    async def stream_chat(self, messages: list[Message]):
        self.calls.append(list(messages))
        n = len(self.calls)
        yield StreamChunk("text", f"reply-{n}")
        yield StreamChunk("done")


@pytest.mark.asyncio
async def test_two_turns_keep_history() -> None:
    p = _ScriptedProvider()
    s = ChatSession(p)
    chunks1 = [c async for c in s.send("第一轮")]
    assert any(c.text == "reply-1" for c in chunks1 if c.kind == "text")
    chunks2 = [c async for c in s.send("第二轮")]
    assert any(c.text == "reply-2" for c in chunks2 if c.kind == "text")
    roles = [m.role for m in s.messages]
    assert roles[0] == "system"
    assert roles[1:] == ["user", "assistant", "user", "assistant"]
    assert s.messages[1].content == "第一轮"
    assert s.messages[3].content == "第二轮"
    # 第二轮请求应包含第一轮 assistant
    assert any(m.role == "assistant" and m.content == "reply-1" for m in p.calls[1])


@pytest.mark.asyncio
async def test_error_appends_assistant_placeholder() -> None:
    class ErrP:
        async def stream_chat(self, messages):
            yield StreamChunk("error", "boom")
            yield StreamChunk("done")

    s = ChatSession(ErrP())
    _ = [c async for c in s.send("x")]
    assert [m.role for m in s.messages] == ["system", "user", "assistant"]
    assert s.messages[-1].content == "[错误：生成失败]"


@pytest.mark.asyncio
async def test_empty_success_appends_assistant_placeholder() -> None:
    class EmptyP:
        async def stream_chat(self, messages):
            yield StreamChunk("done")

    s = ChatSession(EmptyP())
    _ = [c async for c in s.send("x")]
    assert [m.role for m in s.messages] == ["system", "user", "assistant"]
    assert s.messages[-1].content == "[错误：生成失败]"


# =====================================================================
# Execute-B 新增测试：持久化 + load_session
# =====================================================================


_BASE = datetime(2026, 7, 25, tzinfo=timezone.utc)


def _repo(tmp_path: Path) -> SessionRepository:
    return SessionRepository(tmp_path / "chat.db")


def _at(seconds: int) -> datetime:
    return _BASE + timedelta(seconds=seconds)


class _FixedClock:
    """单调递增的钟：每次调用返回 now + _step 秒。"""

    def __init__(self, base: datetime, step: float = 0.0) -> None:
        self._now = base
        self._step = step
        self.calls = 0

    def __call__(self) -> datetime:
        self.calls += 1
        if self.calls == 1:
            self._now = self._now
        else:
            self._now = self._now + timedelta(seconds=self._step)
        return self._now


@pytest.mark.asyncio
async def test_persist_user_and_assistant_after_send(tmp_path: Path) -> None:
    class TwoChunkProvider:
        async def stream_chat(self, messages):
            yield StreamChunk("text", "hello ")
            yield StreamChunk("text", "world")
            yield StreamChunk("done")

    repo = _repo(tmp_path)
    session = ChatSession(
        TwoChunkProvider(),
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
        clock=lambda: _BASE,
    )
    chunks = [c async for c in session.send("ping")]
    assert any(c.text == "hello " for c in chunks if c.kind == "text")
    assert any(c.text == "world" for c in chunks if c.kind == "text")

    sid = session.session_id
    assert sid is not None
    meta = repo.get_session(sid)
    assert meta is not None
    assert meta.provider == "anthropic"
    assert meta.model == "claude-test"
    assert meta.message_count == 2

    msgs = repo.load_messages(sid)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].content == "ping"
    assert msgs[0].status == "final"
    assert msgs[0].seq == 1
    assert msgs[1].content == "hello world"
    assert msgs[1].status == "final"
    assert msgs[1].seq == 2


@pytest.mark.asyncio
async def test_streaming_message_persists_partial(tmp_path: Path) -> None:
    """Provider 在第一个 chunk 后抛异常 → DB 仍写满（finalize 在 except 后跑）。

    ChatSession 把异常"吃掉"并把 ``errored=True`` 标到 final_text 上；
    调用方不再看到 ``RuntimeError``，但 DB 里的 assistant 行已被 finalize。
    """

    class ChunkThenRaise:
        async def stream_chat(self, messages):
            yield StreamChunk("text", "partial-")
            raise RuntimeError("provider 崩了")

    repo = _repo(tmp_path)
    session = ChatSession(
        ChunkThenRaise(),
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
        clock=lambda: _BASE,
    )
    # 不应该把异常往外抛（除非调用方另作安排）
    async for _ in session.send("hi"):
        pass

    sid = session.session_id
    assert sid is not None
    msgs = repo.load_messages(sid)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[1].content == "partial-"
    # finalize 仍应跑：status=final
    assert msgs[1].status == "final"


@pytest.mark.asyncio
async def test_first_chunk_flushes_immediately(tmp_path: Path) -> None:
    """首 chunk 立即 flush；后续 chunk 因为钟差小于 0.5s 不 flush。

    用 monkeypatch 监听 ``update_message_content`` 调用次数：
    - 仅 1 个 chunk 的流：update 被调 1 次（首 chunk flush），
      finalize 另算 1 次 → 共 2 次
    - 我们在 provider 内部 monkeypatch repo.update_message_content 来计数
    """
    flush_calls: list[tuple[str, int, str]] = []

    class SingleChunkProvider:
        async def stream_chat(self, messages):
            yield StreamChunk("text", "first-only")
            yield StreamChunk("done")

    repo = _repo(tmp_path)
    # 让所有 clock() 调用返回 _BASE（不变）；首 chunk flush 仍会触发
    clock = _FixedClock(_BASE, step=0.0)
    session = ChatSession(
        SingleChunkProvider(),
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
        clock=clock,
    )

    # 用 monkeypatch 计数
    orig_update = repo.update_message_content

    def spy_update(session_id, seq, content):
        flush_calls.append((session_id, seq, content))
        orig_update(session_id, seq, content)

    repo.update_message_content = spy_update  # type: ignore[method-assign]

    _ = [c async for c in session.send("q")]

    # 预期：
    # - 首 chunk 触发 1 次 flush（first_chunk_seen=False → 立刻 flush）
    # - finalize 再调一次 update-like（其实是 finalize_message，与 update 不同）
    assert len(flush_calls) == 1
    sid = session.session_id
    assert sid is not None
    assert flush_calls[0][0] == sid
    assert flush_calls[0][1] == 2  # assistant_seq = 2
    assert flush_calls[0][2] == "first-only"

    # 验证 DB 行最终 content/status
    msgs = repo.load_messages(sid)
    assert msgs[1].content == "first-only"
    assert msgs[1].status == "final"


@pytest.mark.asyncio
async def test_no_repo_means_no_persistence(tmp_path: Path) -> None:
    """ChatSession(provider)（无 repo）——DB 文件不应被创建。"""
    db_path = tmp_path / "should_not_exist.db"
    assert not db_path.exists()

    session = ChatSession(_ScriptedProvider())
    assert session.session_id is None
    _ = [c async for c in session.send("hi")]

    assert session.session_id is None
    assert not db_path.exists()
    # 内存行为仍照旧
    assert [m.role for m in session.messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert session.messages[-1].content == "reply-1"


@pytest.mark.asyncio
async def test_load_session_then_send_includes_history(tmp_path: Path) -> None:
    """load_session 之后 send，provider 收到完整历史。"""
    # 先建一个有内容的 session A
    repo = _repo(tmp_path)
    a = ChatSession(
        _ScriptedProvider(),
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
        clock=lambda: _BASE,
    )
    _ = [c async for c in a.send("first Q")]
    _ = [c async for c in a.send("second Q")]
    sid_a = a.session_id
    assert sid_a is not None

    # 新建一个空 session B
    scripted_b = _ScriptedProvider()
    b = ChatSession(
        scripted_b,
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
        clock=lambda: _BASE + timedelta(seconds=10),
    )
    assert b.session_id is None
    b.load_session(sid_a)

    # 内存已被覆盖：system + A 的 user + assistant + user + assistant
    msgs = b.messages
    assert msgs[0].role == "system"
    assert msgs[1].content == "first Q"
    assert msgs[2].content == "reply-1"
    assert msgs[3].content == "second Q"
    assert msgs[4].content == "reply-2"
    assert b.session_id == sid_a

    # B 发新消息：provider 应收到完整历史 + 新 user + 空 assistant 占位
    _ = [c async for c in b.send("third Q")]
    sent_to_provider = scripted_b.calls[-1]
    assert [m.role for m in sent_to_provider] == [
        "system",
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",  # 空字符串占位 — 由 ChatSession 在调 provider 前 append
    ]
    assert sent_to_provider[-1].content == ""  # 占位仍是空
    assert sent_to_provider[-2].content == "third Q"
    assert "InvestPilot" in sent_to_provider[0].content


@pytest.mark.asyncio
async def test_load_session_restores_system_prompt(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    # Session A：自定义 system_prompt
    a = ChatSession(
        _ScriptedProvider(),
        system_prompt="A prompt",
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
        clock=lambda: _BASE,
    )
    _ = [c async for c in a.send("hi")]
    sid_a = a.session_id
    assert sid_a is not None

    # Session B：不同的 system_prompt
    scripted_b = _ScriptedProvider()
    b = ChatSession(
        scripted_b,
        system_prompt="B prompt",
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
        clock=lambda: _BASE + timedelta(seconds=5),
    )
    assert b.messages[0].content == "B prompt"

    # load_session(A) 后 B 的 system 应变为 "A prompt"
    b.load_session(sid_a)
    assert b.messages[0].content == "A prompt"

    # provider 收到的第一条消息是 A prompt（不是 B prompt）
    _ = [c async for c in b.send("again")]
    assert scripted_b.calls[-1][0].content == "A prompt"


def test_load_session_raises_when_missing(tmp_path: Path) -> None:
    """load_session 在 session_id 不存在时抛 SessionNotFound。"""
    repo = _repo(tmp_path)
    session = ChatSession(
        _ScriptedProvider(),
        repo=repo,
        provider_name="anthropic",
        model="claude-test",
    )
    with pytest.raises(SessionNotFound):
        session.load_session("nonexistent-session-id")
