# InvestPilot v0.2.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 替换 v0.2.1 的 ASCII-style 柴犬像素 Logo，重做为 PIL 量化后的橙猫（半块字符 `▀ ▄` 渲染）、增加 5 类常驻动态小 Logo。

**Architecture:** `tools/build_logos.py` 用 PIL 绘制高清猫 → 量化到 6 色调色板 → 输出 `_logo_assets.py` (committed) + `docs/iterations/v0.2.2/preview/` PNG；`interface/logo.py` 改写为半块渲染；`interface/tui_app.py` 在 `#input-dock` 内常驻小 mascot、间隔 0.10s 自动循环 5×4=20 帧。

**Tech Stack:** Python 3.12+、Textual、Rich markup、pytest、ruff、Pillow（仅 dev）

**Spec:** `docs/iterations/v0.2.2/SPEC.md`

## Global Constraints

- 颜色：橙 `#F2B675`、深橙 `#E89B4A`、浅杏 `#FCE3C8`、深棕 `#3B2A20`、近黑 `#221814`、透明 `None`
- 大 Logo：32 cells × 18 cells（half-block → 32×36 视觉行）
- 小 Logo：16 cells × 9 cells（半块 → 16×18 视觉行）
- 5 类动画 × 4 帧 = 20 帧；interval 0.10s；轮播 wave→ear→tail→blink→peek→wave…
- 不破坏聊天/流式/多轮/错误恢复行为；v0.2.1 全部测试须保留通过（允许重写 `test_logo.py` 形状断言）
- 中文 UI 文案；TDD；每任务 commit

## File map

| 路径 | 状态 | 职责 |
|------|------|------|
| `tools/build_logos.py` | 新增 | PIL 绘制 + 量化 + 导出 .py / .png |
| `src/investpilot/interface/_logo_assets.py` | 新增（构建产物，提交） | grid 数据 + 调色板 |
| `src/investpilot/interface/logo.py` | 重写 | 半块渲染 API |
| `src/investpilot/interface/tui_app.py` | 修改 | 大 logo + 常驻小 mascot + 0.10s interval |
| `tests/test_logo.py` | 重写 | grid / 调色板 / 渲染单元测试 |
| `tests/test_tui_app.py` | 追加 | 启动大 logo + mascot 常驻 + 跨动画切换 |
| `docs/iterations/v0.2.2/preview/` | 新增（构建产物） | PNG 预览 |
| `pyproject.toml` | 修改 | dev 依赖 `pillow>=10.0.0`；版本号 0.2.1 → 0.2.2 |
| `src/investpilot/__init__.py` | 修改 | `__version__ = "0.2.2"` |
| `tests/test_smoke.py` | 修改 | 期望版本号 `0.2.2` |

---

### Task 1: 资产生成脚本 + 调色板 + 预览 PNG

**Files:**
- Create: `tools/build_logos.py`
- Create: `src/investpilot/interface/_logo_assets.py` (commit 产物)
- Create: `docs/iterations/v0.2.2/preview/big.png` (commit 产物)
- Create: `docs/iterations/v0.2.2/preview/small_{wave,ear,tail,blink,peek}_{0..3}.png` (commit 产物)
- Modify: `pyproject.toml`（dev 依赖）

**Interfaces:**
- `tools/build_logos.py` 命令：
  - `python tools/build_logos.py` 生成全部
  - `python tools/build_logos.py --preview` 只生成 preview PNG（不写 .py）
- 输出常量到 `_logo_assets.py`：
  - `PALETTE: tuple[str, ...]` 长度 6（hex 字符串 + 'None' 占透明）
  - `BIG_HEAD: tuple[tuple[int, ...], ...]` 32 cols × 36 行（量化后 cell 索引 0..5，0 = 透明）
  - `SMALL_FRAMES: dict[str, tuple[tuple[tuple[int, ...], ...], ...]]` 5 键 × 4 帧，每帧 16 cols × 18 行 cell 索引
- `BIG_HEAD` 与 `SMALL_FRAMES` 用 PIL dominant-color 采样：
  - 大图渲染时一次性采样 → 每对上下行取 2 种色作为 1 cell
  - 小图同理（不是逐像素，而是把网格当目标尺寸，分块渲染）

**Steps:**
- [ ] **Step 1**: 在 `pyproject.toml` dev deps 加入 `pillow>=10.0.0`，跑 `uv sync` 确认可用
- [ ] **Step 2**: 建 `tools/build_logos.py`：定义 `PALETTE`、`draw_canvas`、`draw_big_head()`、`draw_small_base()`、`apply_animation(name, frame_idx, base_img) -> Image`、量化函数 `quantize(img, target_cells)`、写入 `_logo_assets.py` 与 PNG
- [ ] **Step 3**: 程序化绘制大橙猫（半圆耳 + 内耳浅色 + 头顶 5 根乱毛 + 大圆眼 + 三角鼻 + "w" 嘴 + 两侧 3 胡须 + 底部基线）
- [ ] **Step 4**: 程序化绘制小橙猫基础姿态（去掉乱毛细节，保留眼/耳/嘴/胡须）
- [ ] **Step 5**: 程序化生成 5×4 动画帧：
  - wave: 右下爪 0/1/2/1 行
  - ear: 双耳内耳像素 0/向上 1/原位/向上 1
  - tail: 右下尾尖 x 位移 0/-1/0/+1
  - blink: 双眼睛行下移 0/1/2/1（线 → 闭 → 闭 → 线）
  - peek: 整图 y 偏移 0/-2/-4/-6（向上探头）
- [ ] **Step 6**: 量化到大 grid 32×18 cells、小 grid 16×9 cells，6 色调色板映射，0 = 透明
- [ ] **Step 7**: 写出 `_logo_assets.py` + 11 张 PNG（1 大 + 5×4 帧）；运行 `python tools/build_logos.py` 验证生成
- [ ] **Step 8**: 跑 `uv run python tools/build_logos.py && ls docs/iterations/v0.2.2/preview/` 确认 11 张 PNG 都存在
- [ ] **Step 9**: Commit: `feat(v0.2.2): add orange-cat half-block logo build script and assets`

---

### Task 2: logo.py 重写为半块字符渲染

**Files:**
- Modify: `src/investpilot/interface/logo.py`
- Create: `tests/test_logo.py`（完全重写）

**Interfaces:**
- 导入 `_logo_assets` 私有数据
- `PALETTE: tuple[str, ...]`（再导出便于测试用）
- `BIG_HEAD_CELLS_W = 32`、`BIG_HEAD_CELLS_H = 18`
- `SMALL_CELLS_W = 16`、`SMALL_CELLS_H = 9`
- `ANIMATIONS: tuple[str, ...] = ("wave", "ear", "tail", "blink", "peek")`
- `FRAMES_PER_ANIM = 4`
- `render_big_head() -> str`：大 logo 渲染为 Rich markup 字符串
- `render_small_frame(name: str, frame_index: int) -> str`：小 logo 单帧
- `render_small_static() -> str`：循环里给到的当前帧（基于 `itertools.cycle` 的全局 state，可测试时手动覆盖 index）
- `_cell_to_markup(up: int | None, down: int | None) -> str`：核心单 cell 单元

**Steps:**
- [ ] **Step 1**: 写失败测试 `tests/test_logo.py`：
  - 大 grid shape (32, 18)、小 grid 5×4 = 20 frame shape (16, 9)、调色板长度 6
  - `render_big_head()` 返回字符串包含 `#f2b675`/`#e89b4a`/`▀` 或 `▄`
  - `render_small_frame("wave", 0)`、`render_small_frame("peek", 3)` 输出非空且不全等于基础帧（说明动画确实改变）
- [ ] **Step 2**: 跑测确认失败
- [ ] **Step 3**: 实现 `_cell_to_markup`：
  - up & down 相等 → `[#hex]█[/]`（实心）
  - up is None, down present → `[#hex-d]▄[/]`
  - down is None, up present → `[#hex-u]▀[/]`
  - 都 None → `' '`
- [ ] **Step 4**: 实现 `render_big_head`：按 2 行配对 cell，遍历列、调色板查色、join + `\n`
- [ ] **Step 5**: 实现 `render_small_frame`：从 `SMALL_FRAMES[name][frame_index]` 取 16×18 cell grid；同上配对
- [ ] **Step 6**: `render_small_static()` 默认从 `_state` 取 `name, idx`；提供 `set_state(name, idx)` 测试用
- [ ] **Step 7**: 跑 `uv run pytest tests/test_logo.py -v` 与 `uv run ruff check .` 全绿
- [ ] **Step 8**: Commit: `feat(v0.2.2): half-block rendering for big and small cat logos`

---

### Task 3: tui_app.py 集成大 logo + 常驻小 mascot

**Files:**
- Modify: `src/investpilot/interface/tui_app.py`
- Modify: `tests/test_tui_app.py`（追加）

**Interfaces:**
- 移除 v0.2.1 的 `_start_thinking/_stop_thinking/_tick_thinking` 中跟跑狗动画有关的部分，保留 `#thinking` Static 但仅做"显示 thinking 文案"。
- 新增：
  - `__init__` 加字段 `self._mascot_phase = 0`、`self._mascot_frame = 0`、`self._mascot_timer = None`
  - `on_mount`：除挂大 logo 外，调用 `_start_mascot()`
  - `_start_mascot()`：`self.set_interval(0.10, self._tick_mascot)`；首帧 `mascot.update(logo.render_small_frame("wave", 0))`
  - `_tick_mascot()`：`phase = (self._mascot_phase) % 5`，`frame = self._mascot_frame`；调 `_stop_mascot_timer` 在 app exit 时清
- CSS：
  - 加 `#mascot { height: auto; width: auto; align: left top; white-space: pre; }`
  - 加 `#thinking { display: none; }` + `#thinking.active { display: block; }` 保持旧行为

**Steps:**
- [ ] **Step 1**: 跑 `uv run pytest tests/test_tui_helpers.py tests/test_tui_app.py -v` 确认基线绿
- [ ] **Step 2**: 在 `compose()` 内 `#input-dock` Container 加 `Static(id="mascot", markup=True)` 置于 `Static(id="thinking")` 之前
- [ ] **Step 3**: 实现 `_start_mascot` / `_tick_mascot` / 状态字段
- [ ] **Step 4**: 在 `on_mount` 调 `_start_mascot`
- [ ] **Step 5**: 写 `tests/test_tui_app.py` 追加用例：
  - 启动后 `#transcript` 至少含 markup=True 大 logo Static
  - 启动后 `#mascot` 内容非空，且 `_tick_mascot` 连续触发 ≥6 次后，出现的动画种类至少 2 种（不同 name 不同字符串）
  - 发送消息不影响 mascot（不消失）；多轮对话后 mascot 仍可见
- [ ] **Step 6**: 跑全量 `uv run pytest` + `uv run ruff check .` 确认全绿
- [ ] **Step 7**: 手工冒烟 `uv run invest-pilot chat` —— 启动后大橙猫 + 左下角小橙猫 + 5 类动画循环
- [ ] **Step 8**: Commit: `feat(v0.2.2): mount orange-cat big logo and resident mascot cycling 5 animations`

---

### Task 4: 版本号与文档同步

**Files:**
- Modify: `pyproject.toml`（version 0.2.1 → 0.2.2）
- Modify: `src/investpilot/__init__.py`
- Modify: `tests/test_smoke.py`
- Create: `docs/iterations/v0.2.2/RETRO.md`

**Steps:**
- [ ] **Step 1**: 改 `pyproject.toml` version 字段
- [ ] **Step 2**: 改 `src/investpilot/__init__.py` 的 `__version__`
- [ ] **Step 3**: 改 `tests/test_smoke.py` 中期望版本号
- [ ] **Step 4**: 写 `RETRO.md`，记录事实、偏差（如果）、已应用改进、剩余风险
- [ ] **Step 5**: 跑全量 `uv run pytest` + `uv run ruff check .` 确认绿
- [ ] **Step 6**: Commit: `chore(v0.2.2): bump version to 0.2.2 and write retro`

---

### Task 5: 独立 Verify

**Subagent:** `evidence-collector`（独立 verifier 实例）

**Inputs:** v0.2.2 SPEC §12 验收 8 条 + `tests/test_logo.py` + `tests/test_tui_app.py`

**Steps:**
- [ ] **Step 1**: 启动 verifier，附 SPEC 路径
- [ ] **Step 2**: verifier 真实跑：`uv run python tools/build_logos.py`、`uv run pytest`、`uv run ruff check .`
- [ ] **Step 3**: verifier 用 `invest-pilot chat` headless 启动 + `app.save_screenshot()` 或 `app.run_test()` 模拟，对 5 类动画各取至少 1 帧截图存 `docs/iterations/v0.2.2/verify/`
- [ ] **Step 4**: verifier 出 Envelope：Pass / 缺陷 list / Gate 建议
- [ ] **Step 5**: 主 Agent 根据 Envelope 决定 Advance 或 Refinement

---

## Spec coverage

| SPEC §12 验收 | Task |
|--------------|------|
| 1. 启动大橙猫 | 3 |
| 2. 对话可滚动 | 3 + 现有 `test_tui_app.py` |
| 3. 启动即常驻小橙猫 | 3 |
| 4. 5 类自动轮播 | 3（间隔 0.10s 测试覆盖） |
| 5. 连发多轮不受影响 | 3 |
| 6. pytest 全绿 | 1, 2, 3, 4 |
| 7. ruff 通过 | 1, 2, 3, 4 |
| 8. preview PNG 可见 | 1 |

## Placeholder scan

无 TBD；常量、文件名、帧索引、间隔、cells 尺寸均已固定。

## Type consistency

`PALETTE` 列表长度、`BIG_HEAD` 形状 32×18 cells、`SMALL_FRAMES` 5×4 帧 shape (16, 9) cells 在资产脚本、渲染层、测试三处一致。
