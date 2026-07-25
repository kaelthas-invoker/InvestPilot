from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from investpilot.assistant.session import ChatSession
from investpilot.interface import logo
from investpilot.interface._resume_screen import ResumeListScreen
from investpilot.storage import SessionRepository


def is_quit_command(text: str) -> bool:
    return text.strip().lower() in {"/quit", "/exit"}


def format_user_line(text: str) -> str:
    return f"你: {text}"


def format_assistant_prefix() -> str:
    return "助手: "


class InvestPilotApp(App[None]):
    CSS = """
    #transcript {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }
    #input-dock {
        dock: bottom;
        height: auto;
        padding: 0 1 1 1;
    }
    #mascot {
        height: auto;
        width: auto;
        align: left top;
    }
    #thinking {
        height: auto;
        color: #35C4E8;
        display: none;
    }
    #thinking.active {
        display: block;
    }
    #chat-input {
        width: 100%;
    }
    .msg {
        margin: 0 0 1 0;
        width: 100%;
    }
    .msg-user {
        border: heavy cyan;
        border-title-align: left;
        margin: 0 0 1 0;
        width: 100%;
        padding: 0 1;
    }
    .msg-assistant {
        border: heavy orange;
        border-title-align: left;
        margin: 0 0 1 0;
        width: 100%;
        padding: 0 1;
    }
    .msg-system {
        color: $text-muted;
        margin: 0 0 1 0;
        width: 100%;
    }
    #status-line {
        height: 1;
        color: $text-muted;
        background: $boost;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出", show=False, priority=True),
        Binding("ctrl+d", "quit", "退出", show=False, priority=True),
        Binding("up", "history_prev", "上一条", show=False),
        Binding("down", "history_next", "下一条", show=False),
    ]

    MASCOT_INTERVAL_SECONDS = 0.10
    HISTORY_CAP = 100

    def __init__(
        self,
        session: ChatSession,
        *,
        title_suffix: str = "",
        repo: SessionRepository | None = None,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__()
        self._session = session
        self._title_suffix = title_suffix
        self._repo = repo
        self._provider_name = provider_name or (
            title_suffix.split("/", 1)[0] if title_suffix else ""
        )
        self._model = model or (
            title_suffix.split("/", 1)[1] if "/" in title_suffix else title_suffix
        )
        self._history: list[str] = []
        self._history_index: int | None = None
        self._busy = False
        self._mascot_timer = None

    def compose(self) -> ComposeResult:
        title = "InvestPilot"
        if self._title_suffix:
            title = f"{title} · {self._title_suffix}"
        yield Header()
        self.title = title
        yield VerticalScroll(id="transcript")
        with Container(id="input-dock"):
            yield Static("", id="mascot", markup=True)
            yield Static("", id="thinking")
            yield Input(placeholder="输入消息，Enter 发送；/quit 退出", id="chat-input")
            yield Static("", id="status-line")
        yield Footer()

    def on_mount(self) -> None:
        # Mount the orange-cat boot logo as the first transcript line.
        head = Static(logo.render_big_head(), classes="msg", markup=True)
        self.query_one("#transcript", VerticalScroll).mount(head)
        self._append_line("InvestPilot 投研助手（研究辅助，不构成投资建议）")
        self.query_one("#chat-input", Input).focus()

        # Start the resident mascot ticker. The schedule walks a 24-frame
        # loop: ears wobble, hold, then one blink (see interface/logo.py).
        logo.set_frame(0)
        mascot = self.query_one("#mascot", Static)
        mascot.update(logo.render_small_static())
        self._mascot_timer = self.set_interval(
            self.MASCOT_INTERVAL_SECONDS, self._tick_mascot
        )
        self._refresh_status_line()

    def _tick_mascot(self) -> None:
        try:
            logo.advance_frame()
            self.query_one("#mascot", Static).update(logo.render_small_static())
        except Exception:
            # Widget detached (app shutting down) — stop the timer quietly.
            mascot_timer = getattr(self, "_mascot_timer", None)
            if mascot_timer is not None:
                mascot_timer.stop()
                self._mascot_timer = None

    def _append_line(self, text: str) -> Static:
        scroll = self.query_one("#transcript", VerticalScroll)
        widget = Static(text, classes="msg", markup=False)
        scroll.mount(widget)
        widget.scroll_visible()
        return widget

    def _append_user(self, text: str) -> Static:
        scroll = self.query_one("#transcript", VerticalScroll)
        widget = Static(format_user_line(text), classes="msg msg-user", markup=False)
        scroll.mount(widget)
        widget.scroll_visible()
        return widget

    def _append_assistant(self, text: str) -> Static:
        scroll = self.query_one("#transcript", VerticalScroll)
        widget = Static(
            format_assistant_prefix() + text, classes="msg msg-assistant", markup=False
        )
        scroll.mount(widget)
        widget.scroll_visible()
        return widget

    def _append_system_note(self, text: str) -> Static:
        scroll = self.query_one("#transcript", VerticalScroll)
        widget = Static(text, classes="msg msg-system", markup=False)
        scroll.mount(widget)
        widget.scroll_visible()
        return widget

    def _refresh_status_line(
        self, *, provider: str | None = None, model: str | None = None
    ) -> None:
        """Update status-line below input. Defaults to startup provider/model."""
        p = provider if provider is not None else self._provider_name
        m = model if model is not None else self._model
        text = f"{p} / {m}" if p and m else (p or m or "")
        self.query_one("#status-line", Static).update(text)

    def _record_history(self, text: str) -> None:
        """Append user text to history; trim to cap."""
        if not text or text.startswith("/"):
            return
        self._history.append(text)
        if len(self._history) > self.HISTORY_CAP:
            self._history = self._history[-self.HISTORY_CAP:]
        self._history_index = None

    def _set_input(self, text: str) -> None:
        inp = self.query_one("#chat-input", Input)
        inp.value = text
        # move cursor to end
        inp.cursor_position = len(text)

    def action_history_prev(self) -> None:
        if not self._history:
            return
        if self._history_index is None:
            self._history_index = len(self._history) - 1
        else:
            self._history_index = max(0, self._history_index - 1)
        self._set_input(self._history[self._history_index])

    def action_history_next(self) -> None:
        if self._history_index is None:
            return
        if self._history_index + 1 >= len(self._history):
            self._history_index = None
            self._set_input("")
            return
        self._history_index += 1
        self._set_input(self._history[self._history_index])

    def _clear_transcript_except_logo(self) -> None:
        """保留 transcript 第一条（大 logo），移除其余条目。"""
        scroll = self.query_one("#transcript", VerticalScroll)
        children = list(scroll.children)
        for child in children[1:]:
            child.remove()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return
        if is_quit_command(text):
            self.exit()
            return
        if text == "/resume":
            if self._busy:
                self._append_system_note("助手还在生成，请稍候")
                return
            if self._repo is None:
                self._append_system_note("历史会话不可用")
                return
            self.push_screen(ResumeListScreen(self._repo), self._on_resume_dismissed)
            return
        if self._busy:
            # 屏蔽流期间的非常规输入，避免和 worker 竞争
            self._append_system_note("助手还在生成，请稍候")
            return
        self.run_worker(self._handle_send(text), exclusive=True)

    async def _handle_send(self, text: str) -> None:
        inp = self.query_one("#chat-input", Input)
        self._busy = True
        self._record_history(text)
        try:
            self._append_user(text)
            reply = self._append_assistant("")
            parts: list[str] = []
            try:
                async for chunk in self._session.send(text):
                    if chunk.kind == "text" and chunk.text:
                        parts.append(chunk.text)
                        reply.update(format_assistant_prefix() + "".join(parts))
                        reply.scroll_visible()
                    elif chunk.kind == "error":
                        msg = chunk.text or "未知错误"
                        if parts:
                            reply.update(format_assistant_prefix() + "".join(parts))
                        self._append_line(f"错误: {msg}")
            except Exception as exc:
                self._append_line(f"错误: {exc}")
        finally:
            self._busy = False
            inp.focus()

    def _on_resume_dismissed(self, session_id: str | None) -> None:
        """`ResumeListScreen.dismiss(session_id)` 触发的回调（push_screen 注册）。

        SPEC §8：ModalScreen 的 dismiss 结果通过 push_screen 的回调进入；非空值
        即为 session_id 字符串。
        """
        if not session_id:
            return
        if self._repo is None:
            self._append_system_note("历史会话不可用")
            return
        metadata = self._repo.get_session(session_id)
        if metadata is None:
            self._append_system_note("会话不存在或已被删除")
            return
        messages = self._repo.load_messages(session_id)
        # 让 ChatSession 把历史灌进自己（覆盖 system_prompt / _messages / _session_id）
        self._session.load_session(session_id)
        self._clear_transcript_except_logo()
        for m in messages:
            if m.role == "user":
                self._append_user(m.content)
            elif m.role == "assistant":
                self._append_assistant(m.content)
        # /resume 后清零历史（避免与加载对话混淆）
        self._history = []
        self._history_index = None
        # 标题和 boot 提示使用被恢复会话的 provider/model
        self._title_suffix = f"{metadata.provider}/{metadata.model}"
        self.title = f"InvestPilot · {self._title_suffix}"
        # 状态行独立于 _title_suffix，用被恢复 session 的 provider / model
        self._refresh_status_line(
            provider=metadata.provider, model=metadata.model
        )


def run_tui(
    session: ChatSession,
    *,
    provider: str,
    model: str,
    repo: SessionRepository | None = None,
) -> None:
    """阻塞运行 Textual app。"""
    suffix = f"{provider}/{model}".strip("/")
    app = InvestPilotApp(session, title_suffix=suffix, repo=repo)
    app.run()
