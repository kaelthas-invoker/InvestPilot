from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from investpilot.storage import SessionListItem, SessionRepository
from investpilot.utils import format_age


class ResumeListScreen(ModalScreen[str | None]):
    """显示所有已持久化会话的 Modal。Enter 加载，Esc 取消。"""

    BINDINGS = [
        Binding("escape", "dismiss_none", "取消", show=False),
        Binding("q", "dismiss_none", "取消", show=False),
        Binding("j", "cursor_down", "下移", show=False),
        Binding("k", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False, priority=True),
        Binding("up", "cursor_up", "上移", show=False, priority=True),
    ]

    def __init__(self, repo: SessionRepository) -> None:
        super().__init__()
        self._repo = repo
        self._items: list[SessionListItem] = []

    def compose(self) -> ComposeResult:
        try:
            self._items = self._repo.list_sessions()
        except Exception:
            self._items = []
        with VerticalScroll():
            if not self._items:
                yield Static("暂无历史会话，按 Esc 返回", classes="empty")
                return
            now = datetime.now(timezone.utc)
            children: list[ListItem] = []
            for item in self._items:
                age_text = format_age(now - item.updated_at)
                preview = item.preview or "(空会话)"
                label = f"{preview}  {age_text:>6}"
                children.append(ListItem(Label(label), id=f"session-{item.id}"))
            yield ListView(*children)

    def on_mount(self) -> None:
        """Modal 挂载时把焦点交给 ListView，让方向键 + Enter 直接生效。

        不主动 focus 会让焦点留在上一个屏幕（#transcript 的 VerticalScroll），
        导致 Enter / 方向键走到错误 widget，用户只能靠鼠标点击。
        """
        try:
            self.query_one(ListView).focus()
        except Exception:
            # 空列表时没有 ListView，焦点保持默认即可
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id.startswith("session-"):
            self.dismiss(item_id[len("session-"):])

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def action_cursor_down(self) -> None:
        list_view = self.query_one(ListView)
        list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        list_view = self.query_one(ListView)
        list_view.action_cursor_up()
