# InvestPilot v0.2.1 柴犬 Logo 与加载动画 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 TUI 中加入柴犬像素 Logo（启动大狗头 + 加载时小跑狗动画）。

**Architecture:** 新增 `interface/logo.py` 存放像素资产与染色；`tui_app.py` 在 `on_mount` 渲染大狗头，在 `_handle_send` 期间用状态行播放跑狗帧。

**Tech Stack:** Python 3.12+、Textual、Rich markup、pytest、ruff

**Spec:** `docs/iterations/v0.2.1/SPEC.md`

## Global Constraints

- 主色 `#35C4E8`；脸颊浅蓝 `#A9E5F5`；眼/鼻深蓝 `#0C3C5A`
- 像素资产逐行宽度恒定：HEAD_ART 每行 24 列、13 行；RUN_FRAMES 3 帧、每帧 5 行、每行 16 列
- `░`=脸颊浅蓝，`▓`=眼/鼻深蓝，其余 `█▄▀`=主色
- 动画 interval 0.15s；状态行 id 固定为 `thinking`
- 不破坏现有聊天/流式/错误恢复；现有测试必须继续通过
- 中文 UI 文案；TDD；每任务 commit

## File map

| 路径 | 职责 |
|------|------|
| `src/investpilot/interface/logo.py` | 像素资产 + 染色渲染 + 偏移 |
| `tests/test_logo.py` | 资产与偏移单测 |
| `src/investpilot/interface/tui_app.py` | 集成大狗头 + 动画状态行 |

---

### Task 1: logo 资产模块

**Files:**
- Create: `src/investpilot/interface/logo.py`
- Create: `tests/test_logo.py`
- Test: `tests/test_logo.py`

**Interfaces:**
- Produces:
  - `HEAD_ART: list[str]`（13 行 × 24 列）
  - `RUN_FRAMES: list[list[str]]`（3 × 5 × 16）
  - `render_head_markup() -> str`：返回带 Rich markup 染色的多行字符串，可直接给 `Static(..., markup=True)`
  - `run_frame_text(frame_index: int, offset: int) -> str`：返回某一帧加左侧空格的字符串
  - 常量 `FRAME_COUNT`, `FRAME_WIDTH`, `MAX_OFFSET`（= 状态行可用宽度 - FRAME_WIDTH，实现取 `MAX_OFFSET = 20` 常量即可）

- [ ] **Step 1: 写失败测试**

`tests/test_logo.py`:
```python
from investpilot.interface import logo


def test_head_art_shape() -> None:
    assert len(logo.HEAD_ART) == 13
    assert all(len(line) == 24 for line in logo.HEAD_ART)


def test_run_frames_shape() -> None:
    assert len(logo.RUN_FRAMES) == 3
    for frame in logo.RUN_FRAMES:
        assert len(frame) == 5
        assert all(len(line) == 16 for line in frame)


def test_render_head_markup_contains_color() -> None:
    text = logo.render_head_markup()
    assert "#35c4e8" in text.lower()
    assert "█" in text


def test_run_frame_text_offset_moves_content() -> None:
    a = logo.run_frame_text(0, 0)
    b = logo.run_frame_text(0, 5)
    assert a != b
    # 所有行等宽（左 padding 后总宽 = FRAME_WIDTH + offset）
    lines = b.splitlines()
    assert all(len(line) == 16 + 5 for line in lines)


def test_run_frame_text_wraps_offset() -> None:
    w0 = logo.run_frame_text(0, 0)
    wrapped = logo.run_frame_text(0, logo.MAX_OFFSET + 1)
    assert wrapped.splitlines() == logo.run_frame_text(0, 1).splitlines()
    assert w0 != wrapped
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/test_logo.py -v`  
Expected: FAIL（无模块/无常量）

- [ ] **Step 3: 实现 logo.py**

`src/investpilot/interface/logo.py`:

```python
from __future__ import annotations

MAIN = "#35C4E8"
LIGHT = "#A9E5F5"
DARK = "#0C3C5A"

FRAME_COUNT = 3
FRAME_WIDTH = 16
MAX_OFFSET = 20

HEAD_ART: list[str] = [
    "     ██          ██     ",
    "    ████        ████    ",
    "   █████▄▄▄▄▄▄▄▄█████   ",
    "   ██████████████████   ",
    "  ██▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀██  ",
    "  ██   ▓▓      ▓▓   ██  ",
    "  ██   ▓▓      ▓▓   ██  ",
    "  ██░░░░░░░▄▄░░░░░░░██  ",
    "  ██░░░░░░░▓▓░░░░░░░██  ",
    "   ██░░░░░▓▓▓▓░░░░░██   ",
    "   ██░░░░░▀  ▀░░░░░██   ",
    "    ▀██████████████▀    ",
    "      ▀▀▀▀▀▀▀▀▀▀▀▀      ",
]

RUN_FRAMES: list[list[str]] = [
    [
        " ██         ███ ",
        " ████▄▄▄▄▄▄▄  █ ",
        " █▓██████████▄  ",
        "████ ███████    ",
        "  █  █  █  █    ",
    ],
    [
        " ██         ███ ",
        " ████▄▄▄▄▄▄▄  █ ",
        " █▓██████████▄  ",
        "████ ▀█████▀    ",
        "  █     █       ",
    ],
    [
        " ██         ███ ",
        " ████▄▄▄▄▄▄▄  █ ",
        " █▓██████████▄  ",
        "██▀█ ███▀███    ",
        "     █     █    ",
    ],
]


def _colorize(line: str) -> str:
    """按字符染色：░浅蓝脸颊、▓深蓝眼鼻、其余主色。"""
    out: list[str] = []
    for ch in line:
        if ch == " ":
            out.append(" ")
        elif ch == "░":
            out.append(f"[{LIGHT}]█[/]")
        elif ch == "▓":
            out.append(f"[{DARK}]█[/]")
        else:
            out.append(f"[{MAIN}]{ch}[/]")
    return "".join(out)


def render_head_markup() -> str:
    """狗头多行 markup，可直接给 Static(markup=True)。"""
    return "\n".join(_colorize(line) for line in HEAD_ART)


def run_frame_text(frame_index: int, offset: int) -> str:
    """取一帧，左侧加 offset 空格；offset 超出 MAX_OFFSET 取模回绕。"""
    frame = RUN_FRAMES[frame_index % FRAME_COUNT]
    pad = " " * (offset % (MAX_OFFSET + 1))
    return "\n".join(pad + line for line in frame)
```

- [ ] **Step 4: 跑测通过 + ruff**

Run:
```bash
uv run pytest tests/test_logo.py -v
uv run ruff check src tests
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investpilot/interface/logo.py tests/test_logo.py
git commit -m "feat: add Shiba pixel logo assets"
```

---

### Task 2: TUI 集成大狗头与跑狗动画

**Files:**
- Modify: `src/investpilot/interface/tui_app.py`
- Test: `tests/test_tui_helpers.py`（保持通过即可）

**Interfaces:**
- Consumes: `logo.render_head_markup`, `logo.run_frame_text`, `logo.FRAME_COUNT`, `logo.MAX_OFFSET`
- Produces: 无新公共函数；`InvestPilotApp` 行为增强

- [ ] **Step 1: 确认基线测试通过**

Run: `uv run pytest tests/test_tui_helpers.py -v`  
Expected: PASS（未改前应过）

- [ ] **Step 2: 修改 tui_app.py**

在 `compose` 的 `#input-dock` 容器内、`Input` 之前加入状态行：

```python
with Container(id="input-dock"):
    yield Static("", id="thinking")
    yield Input(placeholder="输入消息，Enter 发送；/quit 退出", id="chat-input")
```

CSS 增加：

```python
    #thinking {
        height: auto;
        color: #35C4E8;
        display: none;
        white-space: pre;
    }
    #thinking.active {
        display: block;
    }
```

`on_mount` 第一行之前插入大狗头：

```python
def on_mount(self) -> None:
    from investpilot.interface import logo
    head = Static(logo.render_head_markup(), classes="msg", markup=True)
    self.query_one("#transcript", VerticalScroll).mount(head)
    self._append_line("InvestPilot 投研助手（研究辅助，不构成投资建议）")
    if self._title_suffix:
        self._append_line(f"模型: {self._title_suffix}")
    self.query_one("#chat-input", Input).focus()
```

动画控制（类内新增方法与 `_handle_send` 集成）：

```python
    def _start_thinking(self) -> None:
        from investpilot.interface import logo
        self._think_frame = 0
        self._think_offset = 0
        bar = self.query_one("#thinking", Static)
        bar.add_class("active")
        self._think_timer = self.set_interval(0.15, self._tick_thinking)
        bar.update(logo.run_frame_text(0, 0))

    def _tick_thinking(self) -> None:
        from investpilot.interface import logo
        self._think_frame = (self._think_frame + 1) % logo.FRAME_COUNT
        self._think_offset = (self._think_offset + 1) % (logo.MAX_OFFSET + 1)
        try:
            self.query_one("#thinking", Static).update(
                logo.run_frame_text(self._think_frame, self._think_offset)
            )
        except Exception:
            self._stop_thinking()

    def _stop_thinking(self) -> None:
        timer = getattr(self, "_think_timer", None)
        if timer is not None:
            timer.stop()
            self._think_timer = None
        try:
            self.query_one("#thinking", Static).remove_class("active")
        except Exception:
            pass
```

`_handle_send` 中：
- 在 `self._append_line(format_user_line(text))` 之后调用 `self._start_thinking()`
- 收到首个 `chunk.kind == "text"` 且有内容时调用一次 `self._stop_thinking()`（用 `stopped` 标志保证只停一次）
- `finally` 中确保调用 `self._stop_thinking()`

`__init__` 增加字段：`self._think_timer = None; self._think_frame = 0; self._think_offset = 0`

- [ ] **Step 3: 全量测试 + ruff**

Run:
```bash
uv run pytest
uv run ruff check .
```
Expected: 全绿

- [ ] **Step 4: 手工冒烟（有 key 时可选）**

```bash
uv run invest-pilot chat
# 观察：启动狗头、发送后跑狗、流式开始后消失
```

- [ ] **Step 5: Commit**

```bash
git add src/investpilot/interface/tui_app.py
git commit -m "feat: show Shiba logo on start and running dog while thinking"
```

---

### Task 3: 验收对照

- [ ] **Step 1: 对照 SPEC §7 六条验收**
- [ ] **Step 2: `uv run pytest --cov=investpilot --cov-report=term-missing --cov-fail-under=20` + `uv run ruff check .`**
- [ ] **Step 3: 若有修复 commit：fix: close v0.2.1 acceptance gaps**
- [ ] **Step 4: 交付说明：改动文件、验证命令、剩余风险**

## Spec coverage

| SPEC §7 验收 | Task |
|--------------|------|
| 启动狗头 | 2 |
| 发送后跑狗、token 前出现 | 2 |
| 流式开始停止、可复现 | 2 |
| 报错停止动画 | 2（finally） |
| 多轮不受影响 | 2 + 全量测试 |
| pytest/ruff + 资产单测 | 1, 2, 3 |

## Placeholder scan

无 TBD；像素资产与代码均为完整可粘贴内容。

## Type consistency

`render_head_markup`、`run_frame_text`、`FRAME_COUNT`、`MAX_OFFSET` 全文一致。
