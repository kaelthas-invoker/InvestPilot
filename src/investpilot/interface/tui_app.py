from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from investpilot.assistant.session import ChatSession


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
    #chat-input {
        width: 100%;
    }
    .msg {
        margin: 0 0 1 0;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出", show=False, priority=True),
        Binding("ctrl+d", "quit", "退出", show=False, priority=True),
    ]

    def __init__(self, session: ChatSession, title_suffix: str = "") -> None:
        super().__init__()
        self._session = session
        self._title_suffix = title_suffix
        self._busy = False

    def compose(self) -> ComposeResult:
        title = "InvestPilot"
        if self._title_suffix:
            title = f"{title} · {self._title_suffix}"
        yield Header()
        self.title = title
        yield VerticalScroll(id="transcript")
        with Container(id="input-dock"):
            yield Input(placeholder="输入消息，Enter 发送；/quit 退出", id="chat-input")
        yield Footer()

    def on_mount(self) -> None:
        self._append_line("InvestPilot 投研助手（研究辅助，不构成投资建议）")
        if self._title_suffix:
            self._append_line(f"模型: {self._title_suffix}")
        self.query_one("#chat-input", Input).focus()

    def _append_line(self, text: str) -> Static:
        scroll = self.query_one("#transcript", VerticalScroll)
        widget = Static(text, classes="msg", markup=False)
        scroll.mount(widget)
        widget.scroll_visible()
        return widget

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._busy:
            return
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return
        if is_quit_command(text):
            self.exit()
            return
        self.run_worker(self._handle_send(text), exclusive=True)

    async def _handle_send(self, text: str) -> None:
        inp = self.query_one("#chat-input", Input)
        self._busy = True
        inp.disabled = True
        try:
            self._append_line(format_user_line(text))
            reply = self._append_line(format_assistant_prefix())
            parts: list[str] = []
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
        finally:
            self._busy = False
            inp.disabled = False
            inp.focus()


def run_tui(session: ChatSession, *, provider: str, model: str) -> None:
    """阻塞运行 Textual app。"""
    suffix = f"{provider}/{model}".strip("/")
    app = InvestPilotApp(session, title_suffix=suffix)
    app.run()
