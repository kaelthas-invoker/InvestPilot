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


def _static_text(widget: Static) -> str:
    """Read the current renderable of a Static as plain text."""
    renderable = widget.render()
    if hasattr(renderable, "plain"):
        return renderable.plain
    if hasattr(renderable, "markup"):
        return renderable.markup
    return str(renderable)


@pytest.mark.asyncio
async def test_app_boot_and_send_smoke() -> None:
    app = InvestPilotApp(_FakeSession(), title_suffix="fake/model")
    async with app.run_test() as pilot:
        # Boot: #thinking 存在且无 active class
        thinking = app.query_one("#thinking", Static)
        assert not thinking.has_class("active")

        # Mount 后 transcript 第一条是大 logo markup=True Static（含半块字符）
        transcript_msgs = list(app.query(".msg"))
        assert len(transcript_msgs) >= 2
        first = transcript_msgs[0]
        assert isinstance(first, Static)
        rendered_first = _static_text(first)
        assert any(ch in rendered_first for ch in ("▀", "▄", "█"))

        # 常驻 mascot：#mascot 存在且内容非空
        mascot = app.query_one("#mascot", Static)
        mascot_text = _static_text(mascot)
        assert mascot_text.strip()  # non-empty

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
        texts = [_static_text(w) for w in app.query(".msg")]
        assert any("你: 你好" in t for t in texts)
        assert any("测试回复" in t for t in texts)


@pytest.mark.asyncio
async def test_mascot_cycles_through_frames() -> None:
    """Driving ``_tick_mascot`` repeatedly walks the blink_ear frames.

    v0.2.3 has only the single ``blink_ear`` animation, so a complete
    cycle is 4 ticks — across them the mascot must render ≥ 2 distinct
    frames (eyes-open vs eyes-closed at minimum).
    """
    app = InvestPilotApp(_FakeSession())
    async with app.run_test():
        from investpilot.interface import logo

        seen: set[str] = set()
        for _ in range(8):  # two full loops of 4 frames
            logo.advance_state()
            app._tick_mascot()  # noqa: SLF001 — verify harness only
            from textual.widgets import Static

            mascot = app.query_one("#mascot", Static)
            seen.add(_static_text(mascot))
        # At least 2 distinct frame renderings across the loop.
        assert len(seen) >= 2
