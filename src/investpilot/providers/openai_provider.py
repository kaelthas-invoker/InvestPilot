from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from openai import OpenAI

from investpilot.providers.base import Message, StreamChunk


class OpenAIProvider:
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
        self._client = client or OpenAI(api_key=api_key, base_url=base_url)

    async def stream_chat(self, messages: list[Message]) -> AsyncIterator[StreamChunk]:
        try:
            payload = [
                {"role": m.role, "content": m.content} for m in messages
            ]
            stream = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self._model,
                messages=payload,
                max_tokens=self._max_tokens,
                stream=True,
            )
            async for chunk in _iterate_sync_stream(stream):
                if not chunk.choices:
                    continue
                text = chunk.choices[0].delta.content
                if text:
                    yield StreamChunk("text", text)
        except Exception as exc:
            yield StreamChunk("error", f"OpenAI 调用失败: {exc}")
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
