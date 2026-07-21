from __future__ import annotations

import pytest

from investpilot.assistant.session import ChatSession
from investpilot.providers.base import Message, StreamChunk


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
