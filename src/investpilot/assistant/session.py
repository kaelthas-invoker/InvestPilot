from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from investpilot.providers.base import ChatProvider, Message, StreamChunk

if TYPE_CHECKING:
    from investpilot.storage import SessionRepository

SYSTEM_PROMPT = (
    "你是 InvestPilot，面向投资研究的个人助手。"
    "回答简洁、有条理。你提供研究辅助信息，不构成投资建议。"
)


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession:
    """对话会话：可选地把 user / assistant 消息落到 SessionRepository（SPEC §6/§7）。

    兼容：``ChatSession(provider)``（旧形式）行为与 v0.2.x 一致，不做持久化。
    """

    def __init__(
        self,
        provider: ChatProvider,
        system_prompt: str = SYSTEM_PROMPT,
        *,
        repo: "SessionRepository | None" = None,
        provider_name: str | None = None,
        model: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._provider = provider
        self._system_prompt = system_prompt
        self._messages: list[Message] = [Message("system", system_prompt)]
        self._repo = repo
        self._provider_name = provider_name
        self._model = model
        self._clock: Callable[[], datetime] = clock or _default_clock
        self._session_id: str | None = None

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def session_id(self) -> str | None:
        return self._session_id

    async def send(self, user_text: str) -> AsyncIterator[StreamChunk]:
        text = user_text.strip()
        if not text:
            return
            yield  # pragma: no cover
        repo = self._repo

        # -- 持久化预写：session 行 + user 行 + assistant streaming 行 --
        if repo is not None:
            assert self._provider_name is not None and self._model is not None, (
                "repo is not None 时必须传 provider_name 与 model"
            )
            if self._session_id is None:
                self._session_id = repo.create_session(
                    provider=self._provider_name,
                    model=self._model,
                    system_prompt=self._system_prompt,
                    now=self._clock(),
                )
            user_seq = repo.append_message(
                session_id=self._session_id,
                role="user",
                content=text,
                status="final",
                now=self._clock(),
            )
            assistant_seq = repo.append_message(
                session_id=self._session_id,
                role="assistant",
                content="",
                status="streaming",
                now=self._clock(),
            )
            del user_seq  # 暂未使用；保留以备 debug / 未来审计

        # -- 内存上下文：user + assistant 占位 --
        self._messages.append(Message("user", text))
        placeholder = Message("assistant", "")
        self._messages.append(placeholder)
        placeholder_index = len(self._messages) - 1

        # -- 流式读取 / flush --
        parts: list[str] = []
        buffer: list[str] = []
        errored = False
        last_flush_at: datetime | None = None
        first_chunk_seen = False

        try:
            async for chunk in self._provider.stream_chat(self._messages):
                if chunk.kind == "text" and chunk.text:
                    parts.append(chunk.text)
                    if repo is not None:
                        buffer.append(chunk.text)
                        now = self._clock()
                        should_flush = (not first_chunk_seen) or (
                            last_flush_at is not None
                            and (now - last_flush_at).total_seconds() >= 0.5
                        )
                        if should_flush:
                            repo.update_message_content(
                                self._session_id,  # type: ignore[arg-type]
                                assistant_seq,
                                "".join(buffer),
                            )
                            last_flush_at = now
                            first_chunk_seen = True
                elif chunk.kind == "error":
                    errored = True
                yield chunk
        except Exception:
            errored = True

        # -- 收尾：final_text 与 DB / 内存同步 --
        if parts and not errored:
            final_text = "".join(parts)
        elif parts:
            # 流中出错但已生成部分文本：保留 buffer（与现状行为一致）
            final_text = "".join(parts)
        else:
            final_text = "[错误：生成失败]"

        self._messages[placeholder_index] = Message("assistant", final_text)
        if repo is not None:
            repo.finalize_message(
                self._session_id,  # type: ignore[arg-type]
                assistant_seq,
                final_text,
                now=self._clock(),
            )

    def load_session(self, session_id: str) -> None:
        """把历史会话灌进当前 session（SPEC §7）。

        - 覆盖 ``_system_prompt`` / ``_messages`` / ``_session_id``
        - 不切换 ``_provider``（继续使用启动时的 provider / model）
        - session_id 不存在时抛 ``SessionNotFound``
        """
        repo = self._repo
        if repo is None:
            raise RuntimeError("ChatSession 未配置 repo，无法 load_session")
        metadata = repo.get_session(session_id)
        if metadata is None:
            from investpilot.storage import SessionNotFound

            raise SessionNotFound(session_id)
        self._system_prompt = metadata.system_prompt
        self._messages = [Message("system", metadata.system_prompt)] + [
            Message(m.role, m.content) for m in repo.load_messages(session_id)
        ]
        self._session_id = session_id
