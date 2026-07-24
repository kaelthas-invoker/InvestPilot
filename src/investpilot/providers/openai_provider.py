from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import OpenAI

from investpilot.providers.base import Message, StreamChunk, iterate_sync_stream

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
            async for chunk in iterate_sync_stream(stream):
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                text = getattr(delta, "content", None) if delta is not None else None
                if text:
                    yield StreamChunk("text", text)
        except Exception as exc:
            logger.error(f"OpenAI 调用失败: {exc}")
            yield StreamChunk("error", f"OpenAI 调用失败: {exc}")
        yield StreamChunk("done")
