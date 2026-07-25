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
async def test_mascot_walks_its_whole_pose_schedule() -> None:
    """One tick per frame over a full loop must surface every pose.

    This is the regression guard for the animation actually running: if the
    ticker stalled or the schedule collapsed to a single pose, the set of
    distinct renderings would shrink.
    """
    from investpilot.interface import logo

    app = InvestPilotApp(_FakeSession())
    async with app.run_test():
        mascot = app.query_one("#mascot", Static)
        logo.set_frame(0)
        seen: set[str] = set()
        for _ in range(logo.FRAME_COUNT):
            seen.add(_static_text(mascot))
            app._tick_mascot()  # noqa: SLF001 — drives one frame deterministically
        assert len(seen) == len(set(logo.SCHEDULE))


@pytest.mark.asyncio
async def test_mascot_survives_a_chat_round() -> None:
    """Sending a message must not disturb the resident mascot."""
    from investpilot.interface import logo

    app = InvestPilotApp(_FakeSession())
    async with app.run_test() as pilot:
        mascot = app.query_one("#mascot", Static)
        before = _static_text(mascot)
        assert before.strip()

        app.query_one("#chat-input", Input).value = "你好"
        await pilot.press("enter")
        for _ in range(100):
            await pilot.pause()
            if not app._busy:
                break

        # Still mounted, still rendering a scheduled pose.
        after = _static_text(mascot)
        assert after.strip()
        assert any(ch in after for ch in ("▀", "▄", "█"))
        assert logo.pose_at(logo.get_frame()) in logo.POSES
