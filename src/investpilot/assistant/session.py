from __future__ import annotations

from collections.abc import AsyncIterator

from investpilot.providers.base import ChatProvider, Message, StreamChunk

SYSTEM_PROMPT = (
    "你是 InvestPilot，面向投资研究的个人助手。"
    "回答简洁、有条理。你提供研究辅助信息，不构成投资建议。"
)


class ChatSession:
    def __init__(
        self, provider: ChatProvider, system_prompt: str = SYSTEM_PROMPT
    ) -> None:
        self._provider = provider
        self._messages: list[Message] = [Message("system", system_prompt)]

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    async def send(self, user_text: str) -> AsyncIterator[StreamChunk]:
        text = user_text.strip()
        if not text:
            return
            yield  # pragma: no cover
        self._messages.append(Message("user", text))
        parts: list[str] = []
        errored = False
        async for chunk in self._provider.stream_chat(self._messages):
            if chunk.kind == "text" and chunk.text:
                parts.append(chunk.text)
            if chunk.kind == "error":
                errored = True
            yield chunk
        if not errored and parts:
            self._messages.append(Message("assistant", "".join(parts)))
        elif errored or not parts:
            self._messages.append(Message("assistant", "[错误：生成失败]"))
