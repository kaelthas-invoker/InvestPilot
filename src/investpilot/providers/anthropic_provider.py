from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from anthropic import NOT_GIVEN, Anthropic

from investpilot.providers.base import Message, StreamChunk


class AnthropicProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._client = client or Anthropic(api_key=api_key, base_url=base_url)

    async def stream_chat(self, messages: list[Message]) -> AsyncIterator[StreamChunk]:
        try:
            system_parts = [m.content for m in messages if m.role == "system"]
            system = "\n".join(system_parts) if system_parts else NOT_GIVEN
            api_messages = [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role != "system"
            ]
            stream = await asyncio.to_thread(
                self._client.messages.create,
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=api_messages,
                stream=True,
            )
            async for event in _iterate_sync_stream(stream):
                if getattr(event, "type", None) != "content_block_delta":
                    continue
                delta = getattr(event, "delta", None)
                if delta is None or getattr(delta, "type", None) != "text_delta":
                    continue
                text = getattr(delta, "text", None)
                if text:
                    yield StreamChunk("text", text)
        except Exception as exc:
            yield StreamChunk("error", f"Anthropic 调用失败: {exc}")
        yield StreamChunk("done")


async def _iterate_sync_stream(stream: Iterator[Any]) -> AsyncIterator[Any]:
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
