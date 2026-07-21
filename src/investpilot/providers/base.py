from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Message:
    role: str  # system | user | assistant
    content: str


@dataclass(frozen=True)
class StreamChunk:
    kind: str  # text | error | done
    text: str = ""


class ChatProvider(Protocol):
    async def stream_chat(self, messages: list[Message]) -> AsyncIterator[StreamChunk]:
        ...
