from __future__ import annotations

import pytest

from investpilot.core.config import AppConfig
from investpilot.providers.anthropic_provider import AnthropicProvider
from investpilot.providers.base import Message
from investpilot.providers.factory import build_provider
from investpilot.providers.openai_provider import OpenAIProvider


class _FakeOpenAIStream:
    def __init__(self, pieces: list[str]):
        self._pieces = pieces

    def __iter__(self):
        for p in self._pieces:
            delta = type("D", (), {"content": p})()
            choice = type("C", (), {"delta": delta})()
            yield type("Chunk", (), {"choices": [choice]})()


class _FakeOpenAIClient:
    def __init__(self, pieces: list[str]):
        self.pieces = pieces
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        assert kwargs.get("stream") is True
        return _FakeOpenAIStream(self.pieces)


@pytest.mark.asyncio
async def test_openai_provider_streams_text() -> None:
    client = _FakeOpenAIClient(["你", "好"])
    p = OpenAIProvider("k", "https://example.com/v1", "m", 100, client=client)
    out: list[str] = []
    kinds: list[str] = []
    async for ch in p.stream_chat([Message("user", "hi")]):
        kinds.append(ch.kind)
        if ch.kind == "text":
            out.append(ch.text)
    assert "".join(out) == "你好"
    assert kinds[-1] == "done"


class _FakeAnthropicStream:
    def __init__(self, pieces: list[str]):
        self._pieces = pieces

    def __iter__(self):
        for p in self._pieces:
            delta = type("D", (), {"type": "text_delta", "text": p})()
            yield type("Ev", (), {"type": "content_block_delta", "delta": delta})()


class _FakeAnthropicMessages:
    def __init__(self, pieces: list[str]):
        self.pieces = pieces

    def create(self, **kwargs):
        assert kwargs.get("stream") is True
        return _FakeAnthropicStream(self.pieces)


class _FakeAnthropicClient:
    def __init__(self, pieces: list[str]):
        self.messages = _FakeAnthropicMessages(pieces)


@pytest.mark.asyncio
async def test_anthropic_provider_streams_text() -> None:
    client = _FakeAnthropicClient(["A", "B"])
    p = AnthropicProvider("k", "https://example.com/anthropic", "m", 100, client=client)
    out: list[str] = []
    async for ch in p.stream_chat(
        [Message("system", "sys"), Message("user", "hi")]
    ):
        if ch.kind == "text":
            out.append(ch.text)
    assert "".join(out) == "AB"


def test_build_provider_openai() -> None:
    cfg = AppConfig("openai", "m", 1, "k", "https://example.com/v1")
    assert isinstance(build_provider(cfg), OpenAIProvider)


def test_build_provider_anthropic() -> None:
    cfg = AppConfig("anthropic", "m", 1, "k", "https://example.com/anthropic")
    assert isinstance(build_provider(cfg), AnthropicProvider)
