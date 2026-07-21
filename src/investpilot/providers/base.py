from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any, Protocol


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


async def iterate_sync_stream(stream: Iterator[Any]) -> AsyncIterator[Any]:
    it = iter(stream)

    def _next() -> Any:
        try:
            return next(it)
        except StopIteration:
            return None

    while True:
        item = await asyncio.to_thread(_next)
        if item is None:
            break
        yield item
