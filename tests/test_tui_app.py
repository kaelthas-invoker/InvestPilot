from __future__ import annotations

import pytest
from textual.widgets import Input, Static

from investpilot.interface.tui_app import InvestPilotApp
from investpilot.providers.base import StreamChunk


class _FakeSession:
    """最小 ChatSession 替身：send 为异步生成器方法。"""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, user_text: str):
        self.sent.append(user_text)
        yield StreamChunk("text", "测试回复")
        yield StreamChunk("done")


@pytest.mark.asyncio
async def test_app_boot_and_send_smoke() -> None:
    app = InvestPilotApp(_FakeSession(), title_suffix="fake/model")
    async with app.run_test() as pilot:
        # Boot: #thinking 存在且无 active class
        thinking = app.query_one("#thinking", Static)
        assert not thinking.has_class("active")
        # 挂载后 transcript 至少有狗头 + 欢迎语两条 .msg
        assert len(app.query(".msg")) >= 2

        # 提交一条消息
        inp = app.query_one("#chat-input", Input)
        inp.value = "你好"
        await pilot.press("enter")
        for _ in range(100):
            await pilot.pause()
            if not app._busy:
                break
        assert not app._busy
        assert not thinking.has_class("active")

        # transcript 增加用户行与助手回复
        texts = [str(w.render()) for w in app.query(".msg")]
        assert any("你: 你好" in t for t in texts)
        assert any("测试回复" in t for t in texts)
