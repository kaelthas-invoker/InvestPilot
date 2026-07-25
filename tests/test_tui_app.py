from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.app import App
from textual.containers import Container
from textual.widgets import Input, Static

from investpilot.interface._resume_screen import ResumeListScreen
from investpilot.interface.tui_app import InvestPilotApp
from investpilot.providers.base import StreamChunk
from investpilot.storage import SessionRepository


class _FakeSession:
    """最小 ChatSession 替身：send 为异步生成器方法。

    Execute-C 测试用：暴露可选的 `repo` 字段和 `load_session` 桩方法，
    让 TUI 能像真实 ChatSession 一样调用 load_session。
    """

    def __init__(self, repo: SessionRepository | None = None) -> None:
        self.sent: list[str] = []
        self._messages: list = []
        self._session_id: str | None = None
        self._repo = repo
        self._loaded: list[str] = []

    async def send(self, user_text: str):
        self.sent.append(user_text)
        yield StreamChunk("text", "测试回复")
        yield StreamChunk("done")

    def load_session(self, session_id: str) -> None:
        self._loaded.append(session_id)
        self._session_id = session_id
        if self._repo is not None:
            metadata = self._repo.get_session(session_id)
            messages = self._repo.load_messages(session_id)
            if metadata is not None:
                self._messages = [("system", metadata.system_prompt)] + [
                    (m.role, m.content) for m in messages
                ]


class _SlowProvider:
    """让流持续数秒的 provider，用于测试流中 /resume 屏蔽。"""

    async def stream_chat(self, messages):
        for _ in range(50):
            await asyncio.sleep(0.05)
            yield StreamChunk("text", "x")
        yield StreamChunk("done")


class _SlowSession:
    """带 _SlowProvider 的 ChatSession 替身，提供 load_session 桩。"""

    def __init__(self, repo: SessionRepository | None = None) -> None:
        self._provider = _SlowProvider()
        self._session_id: str | None = None
        self._repo = repo
        self._loaded: list[str] = []

    async def send(self, user_text: str):
        async for chunk in self._provider.stream_chat([]):
            yield chunk

    def load_session(self, session_id: str) -> None:
        self._loaded.append(session_id)


def _static_text(widget: Static) -> str:
    """Read the current renderable of a Static as plain text."""
    renderable = widget.render()
    if hasattr(renderable, "plain"):
        return renderable.plain
    if hasattr(renderable, "markup"):
        return renderable.markup
    return str(renderable)


def _seed_session(
    repo: SessionRepository, *, provider: str = "anthropic", model: str = "fake",
    user_text: str = "hi", assistant_text: str = "hello",
) -> str:
    sid = repo.create_session(
        provider=provider, model=model, system_prompt="sys"
    )
    repo.append_message(session_id=sid, role="user", content=user_text)
    repo.append_message(session_id=sid, role="assistant", content=assistant_text)
    return sid


def _render_compose_in_probe(modal_factory) -> str:
    """构造 Modal，挂在独立 App 内 dump 所有 Static 的渲染文本。

    必须在 active app 内调用 compose（compose 内部使用上下文管理器注册 widget）。
    """
    class _Probe(App):
        def compose(self):
            modal = modal_factory()
            yield Container(*list(modal.compose()))

    async def _run() -> str:
        probe = _Probe()
        async with probe.run_test():
            return "\n".join(_static_text(c) for c in probe.query(Static))

    return asyncio.run(_run())


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


# -- Execute-C 新增 ------------------------------------------------------


@pytest.mark.asyncio
async def test_message_styles() -> None:
    """发送一条消息后，user / assistant Static 必须分别有 msg-user / msg-assistant class。"""
    app = InvestPilotApp(_FakeSession(), title_suffix="fake/model")
    async with app.run_test() as pilot:
        inp = app.query_one("#chat-input", Input)
        inp.value = "hi"
        await pilot.press("enter")
        for _ in range(100):
            await pilot.pause()
            if not app._busy:
                break

        user_widgets = list(app.query(".msg-user"))
        assistant_widgets = list(app.query(".msg-assistant"))
        assert user_widgets, "expected at least one .msg-user widget"
        assert assistant_widgets, "expected at least one .msg-assistant widget"

        user_text = _static_text(user_widgets[0])
        assistant_text = _static_text(assistant_widgets[0])
        assert "你:" in user_text
        assert "hi" in user_text
        assert "助手:" in assistant_text
        assert "测试回复" in assistant_text

        # CSS 契约（SPEC §8 + AC9）：.msg-user 必须 heavy cyan；.msg-assistant 必须 heavy orange
        css = app.CSS
        assert ".msg-user" in css
        assert ".msg-assistant" in css
        assert ".msg-system" in css
        # 提取 .msg-user 块并断言包含 heavy + cyan
        user_block = css.split(".msg-user", 1)[1].split("}", 1)[0]
        assert "heavy" in user_block and "cyan" in user_block
        asst_block = css.split(".msg-assistant", 1)[1].split("}", 1)[0]
        assert "heavy" in asst_block and "orange" in asst_block


@pytest.mark.asyncio
async def test_resume_screen_jk_navigation(tmp_path: Path) -> None:
    """j / k 绑定能驱动 ListView 在条目间移动。"""
    repo = SessionRepository(tmp_path / "chat.db")
    _seed_session(repo, user_text="问题一", assistant_text="回答一")
    _seed_session(repo, user_text="问题二", assistant_text="回答二")
    _seed_session(repo, user_text="问题三", assistant_text="回答三")

    app = InvestPilotApp(_FakeSession(), repo=repo)
    async with app.run_test() as pilot:
        app.query_one("#chat-input", Input).value = "/resume"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ResumeListScreen)

        from textual.widgets import ListView as _LV

        list_view = app.screen.query_one(_LV)
        # 初始 index = 0
        assert list_view.index == 0
        await pilot.press("j")
        await pilot.pause()
        assert list_view.index == 1
        await pilot.press("k")
        await pilot.pause()
        assert list_view.index == 0


def test_resume_screen_empty(tmp_path: Path) -> None:
    """空 repo：ResumeListScreen 显示"暂无历史会话"。"""
    repo = SessionRepository(tmp_path / "chat.db")
    dump = _render_compose_in_probe(lambda: ResumeListScreen(repo))
    assert "暂无历史会话" in dump


def test_resume_screen_lists_items(tmp_path: Path) -> None:
    """预置 2 条会话后，ListView 含两个 ListItem，每个含 preview + age。"""
    repo = SessionRepository(tmp_path / "chat.db")
    _seed_session(repo, user_text="问题一", assistant_text="回答一")
    _seed_session(repo, user_text="问题二", assistant_text="回答二")
    dump = _render_compose_in_probe(lambda: ResumeListScreen(repo))
    assert "问题一" in dump
    assert "问题二" in dump
    # k8s 紧凑 age 至少有一个数字单位
    assert any(unit in dump for unit in ("s", "m", "h", "d"))


@pytest.mark.asyncio
async def test_resume_load_renders_with_styles(tmp_path: Path) -> None:
    """repo 中预置 2 条会话；选中后样式化重渲染。

    通过 push_screen(ResumeListScreen(repo), callback) 的回调路径触发，
    验证 ModalScreen 的 dismiss 结果真的能到达 callback（修复 execute-C 缺陷 #1）。
    """
    repo = SessionRepository(tmp_path / "chat.db")
    sid1 = _seed_session(repo, user_text="问题一", assistant_text="回答一")
    _seed_session(repo, user_text="问题二", assistant_text="回答二")

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        # 直接调用 dismiss 路径注册的回调（与 push_screen 走同一函数）
        app._on_resume_dismissed(sid1)
        await pilot.pause()

        user_widgets = list(app.query(".msg-user"))
        assistant_widgets = list(app.query(".msg-assistant"))
        assert user_widgets
        assert assistant_widgets

        user_texts = [_static_text(w) for w in user_widgets]
        assistant_texts = [_static_text(w) for w in assistant_widgets]
        assert any("问题一" in t for t in user_texts)
        assert any("回答一" in t for t in assistant_texts)
        # session.load_session 被调用
        assert session._loaded == [sid1]
        # 标题更新
        assert "/" in app._title_suffix


@pytest.mark.asyncio
async def test_resume_modal_e2e_dismiss_delivers_to_callback(tmp_path: Path) -> None:
    """端到端：输入 /resume → ListView 选中 → dismiss → callback 收到 session_id。

    这是对 Execute-C code-review 缺陷 #1 的回归测试 — 实际 push_screen
    + ListView.Selected 的 dismiss 结果必须到达 push_screen 注册的回调。
    """
    from textual.widgets import ListView

    repo = SessionRepository(tmp_path / "chat.db")
    sid1 = _seed_session(repo, user_text="问题一", assistant_text="回答一")
    sid2 = _seed_session(repo, user_text="问题二", assistant_text="回答二")

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        # 触发 /resume 命令
        app.query_one("#chat-input", Input).value = "/resume"
        await pilot.press("enter")
        await pilot.pause()

        # 确认 ResumeListScreen 被 push
        assert isinstance(app.screen, ResumeListScreen)

        # 通过 ListView.Selected 事件触发 dismiss
        list_view = app.screen.query_one(ListView)
        first_item = list_view.children[0]
        list_view.post_message(ListView.Selected(list_view, first_item, 0))
        await pilot.pause()

        # callback 已经被调用，session 被加载，transcript 含样式化消息
        # 注意：list_sessions() 按 updated_at DESC 排序，最新会话排第一
        # 即 _seed_session 调用顺序里，最后 seed 的"问题二"会排第一
        assert session._loaded == [sid2]
        # transcript 含被加载会话的 user 内容
        loaded_sid = session._loaded[0]
        if loaded_sid == sid1:
            assert any("问题一" in _static_text(w) for w in app.query(".msg-user"))
        else:
            assert any("问题二" in _static_text(w) for w in app.query(".msg-user"))
        # 至少一个 user/assistant widget 被样式化渲染
        assert list(app.query(".msg-user"))
        assert list(app.query(".msg-assistant"))


@pytest.mark.asyncio
async def test_loaded_messages_share_styles(tmp_path: Path) -> None:
    """恢复的 user / assistant Static 与 fresh-send 的 user / assistant Static class 一致。"""
    repo = SessionRepository(tmp_path / "chat.db")
    sid = _seed_session(repo, user_text="已存问题", assistant_text="已存回答")

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        app._on_resume_dismissed(sid)
        await pilot.pause()

        loaded_user = list(app.query(".msg-user"))
        loaded_assistant = list(app.query(".msg-assistant"))
        assert loaded_user
        assert loaded_assistant
        loaded_user_classes = set(loaded_user[0].classes)
        loaded_assistant_classes = set(loaded_assistant[0].classes)
        assert "msg-user" in loaded_user_classes
        assert "msg" in loaded_user_classes
        assert "msg-assistant" in loaded_assistant_classes
        assert "msg" in loaded_assistant_classes

        # 再发一条 — class 与加载版本完全一致
        app.query_one("#chat-input", Input).value = "新问题"
        await pilot.press("enter")
        for _ in range(100):
            await pilot.pause()
            if not app._busy:
                break

        all_user = list(app.query(".msg-user"))
        all_assistant = list(app.query(".msg-assistant"))
        assert len(all_user) == 2
        assert len(all_assistant) == 2

        fresh_user_classes = set(all_user[1].classes)
        fresh_assistant_classes = set(all_assistant[1].classes)
        assert fresh_user_classes == loaded_user_classes
        assert fresh_assistant_classes == loaded_assistant_classes


@pytest.mark.asyncio
async def test_resume_blocked_during_stream(tmp_path: Path) -> None:
    """流期间输入 /resume：被屏蔽，显示 system note，不 push Modal。"""
    repo = SessionRepository(tmp_path / "chat.db")
    _seed_session(repo)  # 确保列表非空，避免空屏分支干扰

    session = _SlowSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        # 触发长流
        app.query_one("#chat-input", Input).value = "慢问题"
        await pilot.press("enter")
        # 让 worker 启动进入 busy（最多 5 次 pause）
        for _ in range(5):
            await pilot.pause()
            if app._busy:
                break
        assert app._busy

        # 模拟在流中输入 /resume
        app.query_one("#chat-input", Input).value = "/resume"
        await pilot.press("enter")
        await pilot.pause()

        # 仍 busy；modal 没被 push；显示 system note
        assert app._busy
        # active screen 仍是主屏（不是 ResumeListScreen）
        assert not isinstance(app.screen, ResumeListScreen)
        system_notes = list(app.query(".msg-system"))
        assert any("助手还在生成" in _static_text(w) for w in system_notes), (
            f"expected system note, got: {[(_static_text(w)) for w in system_notes]}"
        )

        # 等流结束
        for _ in range(200):
            await pilot.pause()
            if not app._busy:
                break
        assert not app._busy


# -- Execute-B 新增 (status-line) -----------------------------------------


@pytest.mark.asyncio
async def test_status_line_shows_provider_model() -> None:
    """AC12: 状态行显示 `provider / model`（带空格）。"""
    app = InvestPilotApp(
        _FakeSession(), provider_name="anthropic", model="MiniMax-M3"
    )
    async with app.run_test():
        status = app.query_one("#status-line", Static)
        assert _static_text(status) == "anthropic / MiniMax-M3"


@pytest.mark.asyncio
async def test_status_line_updates_after_resume(tmp_path: Path) -> None:
    """AC13: /resume 后状态行更新为被恢复 session 的 provider/model。"""
    repo = SessionRepository(tmp_path / "chat.db")
    _seed_session(repo, provider="openai", model="gpt-4")

    # 找出唯一的 session_id
    sessions = repo.list_sessions()
    assert sessions, "expected at least one seeded session"
    sid = sessions[0].id

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(
        session, title_suffix="anthropic/MiniMax-M3", repo=repo
    )
    async with app.run_test() as pilot:
        # 启动后状态行是 startup 的 provider/model
        status = app.query_one("#status-line", Static)
        assert _static_text(status) == "anthropic / MiniMax-M3"

        # 触发 resume load
        app._on_resume_dismissed(sid)
        await pilot.pause()

        # 状态行应更新为被恢复 session 的 provider/model
        assert _static_text(status) == "openai / gpt-4"


# -- Execute-C 新增 (bash-style history) ---------------------------------


async def _send(app: App, pilot, text: str) -> None:
    """Helper: set input text, press Enter, wait for worker to finish."""
    app.query_one("#chat-input", Input).value = text
    await pilot.press("enter")
    for _ in range(100):
        await pilot.pause()
        if not app._busy:
            break


@pytest.mark.asyncio
async def test_history_up_recalls_previous() -> None:
    """AC4/5: Up 替换 input 为前一条；多次 Up 翻到第 1 条后停住。"""
    app = InvestPilotApp(_FakeSession())
    async with app.run_test() as pilot:
        await _send(app, pilot, "msg1")
        await _send(app, pilot, "msg2")
        await _send(app, pilot, "msg3")

        inp = app.query_one("#chat-input", Input)
        inp.value = ""
        # Up → msg3
        await pilot.press("up")
        assert inp.value == "msg3"
        # Up → msg2
        await pilot.press("up")
        assert inp.value == "msg2"
        # Up → msg1
        await pilot.press("up")
        assert inp.value == "msg1"
        # Up 再次 → 仍 msg1（clamp at start）
        await pilot.press("up")
        assert inp.value == "msg1"


@pytest.mark.asyncio
async def test_history_down_advances_and_clears_at_end() -> None:
    """AC6: Down 在历史中往前；到末尾清空，_history_index 重置为 None。"""
    app = InvestPilotApp(_FakeSession())
    async with app.run_test() as pilot:
        await _send(app, pilot, "a")
        await _send(app, pilot, "b")

        inp = app.query_one("#chat-input", Input)
        inp.value = ""
        # Up 两次 → "a"（index=0）
        await pilot.press("up")
        await pilot.press("up")
        assert inp.value == "a"
        # Down → "b"（index=1）
        await pilot.press("down")
        assert inp.value == "b"
        # Down 再次 → ""，_history_index 重置为 None
        await pilot.press("down")
        assert inp.value == ""
        assert app._history_index is None


@pytest.mark.asyncio
async def test_history_capped_at_100() -> None:
    """AC7: 历史容量 100，超出后保留最近 100 条。"""
    app = InvestPilotApp(_FakeSession())
    async with app.run_test() as pilot:
        for i in range(105):
            await _send(app, pilot, f"m{i}")
        assert len(app._history) == 100
        # 第一条是 index=5（即 "m5"），前 5 条已被裁掉
        assert app._history[0] == "m5"
        # 最后一条是 index=104
        assert app._history[-1] == "m104"


@pytest.mark.asyncio
async def test_slash_commands_not_in_history() -> None:
    """AC8: 斜杠命令不入历史。"""
    app = InvestPilotApp(_FakeSession())
    async with app.run_test():
        # 直接调用 _record_history 验证 /-prefix 过滤逻辑
        app._record_history("/foo")
        assert len(app._history) == 0
        app._record_history("/resume")
        assert len(app._history) == 0


@pytest.mark.asyncio
async def test_empty_text_not_in_history() -> None:
    """AC9: 空文本不入历史。"""
    app = InvestPilotApp(_FakeSession())
    async with app.run_test():
        # Empty submit: on_input_submitted 不会进入 _handle_send，
        # 直接验证 _record_history 过滤空文本。
        app._record_history("")
        assert len(app._history) == 0


@pytest.mark.asyncio
async def test_history_mid_edit_keeps_index() -> None:
    """AC10: 历史回看中手动编辑 input 不重置 _history_index。"""
    app = InvestPilotApp(_FakeSession())
    async with app.run_test() as pilot:
        await _send(app, pilot, "first")
        await _send(app, pilot, "second")

        inp = app.query_one("#chat-input", Input)
        inp.value = ""
        # Up → "second", index=1
        await pilot.press("up")
        assert inp.value == "second"
        assert app._history_index == 1

        # 中途手动编辑 input.value（不通过 binding）— index 应保留
        inp.value = "second-modified"
        assert app._history_index == 1

        # Up 再次 → 仍走历史（index 减到 0 → "first"）
        await pilot.press("up")
        assert inp.value == "first"


@pytest.mark.asyncio
async def test_resume_clears_history(tmp_path: Path) -> None:
    """AC11: /resume 加载历史后 _history 清空，_history_index 重置。"""
    repo = SessionRepository(tmp_path / "chat.db")
    _seed_session(repo)
    sid = repo.list_sessions()[0].id

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        await _send(app, pilot, "msg1")
        await _send(app, pilot, "msg2")
        assert len(app._history) == 2

        app._on_resume_dismissed(sid)
        await pilot.pause()

        assert app._history == []
        assert app._history_index is None


# -- Execute-D 新增 (resume 验证 + 移除 hint) -----------------------------


@pytest.mark.asyncio
async def test_resume_modal_arrow_keys_navigate_and_enter_selects(
    tmp_path: Path,
) -> None:
    """AC14: /resume Modal 中 Up/Down/Enter 工作正常。"""
    from textual.widgets import ListView

    repo = SessionRepository(tmp_path / "chat.db")
    _seed_session(repo, user_text="一", assistant_text="A")
    _seed_session(repo, user_text="二", assistant_text="B")
    _seed_session(repo, user_text="三", assistant_text="C")

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        app.query_one("#chat-input", Input).value = "/resume"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ResumeListScreen)

        list_view = app.screen.query_one(ListView)
        assert list_view.index == 0

        # Down 两次 → index = 2
        await pilot.press("down")
        await pilot.pause()
        assert list_view.index == 1
        await pilot.press("down")
        await pilot.pause()
        assert list_view.index == 2

        # Up → index = 1
        await pilot.press("up")
        await pilot.pause()
        assert list_view.index == 1

        # Enter → 触发 dismiss + load_session（用真键盘，不用 post_message）
        await pilot.press("enter")
        await pilot.pause()

        assert session._loaded, "expected load_session to be called"


@pytest.mark.asyncio
async def test_resume_modal_focuses_list_view(
    tmp_path: Path,
) -> None:
    """回归测试：Modal 挂载后焦点必须在 ListView，否则 Enter / 方向键走错 widget。

    Bug 现象：focus 留在主屏的 #transcript VerticalScroll，导致用户只能鼠标点击。
    """
    from textual.widgets import ListView

    repo = SessionRepository(tmp_path / "chat.db")
    _seed_session(repo)

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        app.query_one("#chat-input", Input).value = "/resume"
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, ResumeListScreen)
        # 焦点必须在 ListView
        assert app.screen.focused is not None
        assert isinstance(app.screen.focused, ListView), (
            f"focused widget is {type(app.screen.focused).__name__}, expected ListView"
        )


@pytest.mark.asyncio
async def test_no_restored_session_hint_after_resume(tmp_path: Path) -> None:
    """AC15: /resume 后 transcript 不含 '已恢复会话'。"""
    repo = SessionRepository(tmp_path / "chat.db")
    sid = _seed_session(repo, user_text="旧问题", assistant_text="旧回答")

    session = _FakeSession(repo=repo)
    app = InvestPilotApp(session, title_suffix="fake/model", repo=repo)
    async with app.run_test() as pilot:
        app._on_resume_dismissed(sid)
        await pilot.pause()

        all_msgs = [_static_text(w) for w in app.query(".msg")]
        joined = "\n".join(all_msgs)
        assert "已恢复会话" not in joined, (
            f"transcript should not contain '已恢复会话', got: {all_msgs}"
        )
