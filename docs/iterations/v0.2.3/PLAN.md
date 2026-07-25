# InvestPilot v0.2.3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 应用 v0.2.2 review 用户反馈，把大/小 Logo 收敛成一份 16×9 cells 像素艺术，把 5 类动态动画合并成单一 blink_ear 4 帧。

**Architecture:**
- `tools/build_logos.py` 重写：单 `draw_head()` + 单 `_blink_ear()` 动画。
- `tools/verify_logos.py` 简化：截图 head + 4 mascot 帧 + 3 zoom。
- 资产文件 `src/investpilot/interface/_logo_assets.py` 改名 `HEAD`（替代 `BIG_HEAD`），`SMALL_FRAMES` 仅含 `blink_ear`。
- 渲染层 `interface/logo.py`：`render_head()` 作为 `render_big_head` 的别名 + `render_small_frame("blink_ear", i)`。
- TUI 集成 `interface/tui_app.py.on_mount`：使用 `render_head`，mascot ticker 0.10s/帧循环 4 帧。
- 测试 + 版本号同步到 0.2.3。

**Tech Stack:** Python 3.12+、Textual、Rich markup、pytest、ruff、Pillow（仅 dev 依赖）。

**Spec:** `docs/iterations/v0.2.3/SPEC.md`

## Global Constraints

- 调色板 6 色与 v0.2.2 一致（透明 / `#F2B675` / `#E89B4A` / `#FCE3C8` / `#3B2A20` / `#221814`）
- 网格 16 cols × 9 cell-rows（half-block ⇒ 18 视觉行）
- 单动画 `blink_ear`，4 帧：open+upright → half+tilt0.7 → closed+tilt1.5 → half+tilt0.7
- interval 0.10s/帧 ⇒ 0.4s/loop
- 不破坏聊天/流式/多轮/错误恢复；既有测试保留通过

## File map

| 路径 | 状态 | 职责 |
|------|------|------|
| `tools/build_logos.py` | 重写 | PIL 绘制 + 6 色量化 |
| `src/investpilot/interface/_logo_assets.py` | 重新生成 | `PALETTE` + `HEAD` + `SMALL_FRAMES["blink_ear"]` |
| `src/investpilot/interface/logo.py` | 重写 | 半块字符渲染 API |
| `src/investpilot/interface/tui_app.py` | 修改 | boot 用 `render_head`，mascot 单动循环 |
| `tools/verify_logos.py` | 简化 | 截图 head + 4 mascot 帧 |
| `tests/test_logo.py` | 重写 | shape/帧/状态 |
| `tests/test_tui_app.py` | 调整 | mascot cycle 测试 |
| `tests/test_smoke.py` | 改 | version 期望 `0.2.3` |
| `pyproject.toml` | 改 | version `0.2.3` |
| `src/investpilot/__init__.py` | 改 | `__version__ = "0.2.3"` |
| `docs/iterations/v0.2.3/{SPEC,PLAN,RETRO}.md` | 新增 | 计划/复盘 |

---

### Task 1: 重写 `tools/build_logos.py`

- [ ] **Step 1**: 删除 `draw_big`/`draw_small_base`/`_wave`/`_ear`/`_tail`/`_blink`/`_peek`，保留帮助函数 `_cell_idx`、`quantize`、`_hex`、`PALETTE`、`PAL_RGB`、`PAL_HEX`
- [ ] **Step 2**: 写入新 `draw_head()`：face 用 `[px(1.5, 2.5), px(14.5, 8.0)]`，其它造型照搬（缩小了 face 1 cell 留呼吸空间）
- [ ] **Step 3**: 写入 `_blink_ear(img, frame)`：按 §3.2 表执行闭眼 / 外倾
- [ ] **Step 4**: `ANIMS = {"blink_ear": _blink_ear}`；`CELLS_W=16, CELLS_H=9`；`write_assets_py` 输出 `HEAD` 而非 `BIG_HEAD`
- [ ] **Step 5**: `uv run python tools/build_logos.py --preview` 检查 `preview/head.png`、`preview/blink_ear_{0..3}.png` 5 张
- [ ] **Step 6**: `git commit -m "feat(v0.2.3): unified 16x9 cat head + blink_ear animation"`

---

### Task 2: 重写 `src/investpilot/interface/logo.py`

- [ ] **Step 1**: 删 `render_big_head`、`FRAMES_PER_ANIM`/`ANIMATIONS` 旧常量的所有别名；改成 `render_head`、`ANIMATIONS=("blink_ear",)`、`FRAMES_PER_ANIM=4`
- [ ] **Step 2**: 把 `render_big_head = render_head` 作为别名，保留 back-compat
- [ ] **Step 3**: `advance_state` 仍然 `frame=(frame+1)%4`；`anim_idx` 在 4 帧环绕时 `(idx+1) % len(ANIMATIONS)`（最终依然 0 因为只有 1 anim）

---

### Task 3: `tui_app.py` 改 boot logo

- [ ] **Step 1**: `on_mount` 中调 `logo.render_head()` 替代 `render_big_head()`
- [ ] **Step 2**: 单 animation 循环逻辑本身没动（间隔 0.10s，调用 `advance_state` + `update`）

---

### Task 4: 重写 `tests/test_logo.py`

- [ ] **Step 1**: 验证 `ANIMATIONS == ("blink_ear",)`，FRAMES_PER_ANIM == 4
- [ ] **Step 2**: 验证 `HEAD` grid 18 行 × 16 列
- [ ] **Step 3**: 验证 `SMALL_FRAMES["blink_ear"]` 4 帧每帧 18 行 × 16 列
- [ ] **Step 4**: 验证 `render_head` 含半块字符和调色板色
- [ ] **Step 5**: 验证 `blink_ear` frame 0 与 frame 2（base vs closed）有 ≥ 10 个 cell 差异
- [ ] **Step 6**: 验证 `advance_state` 4 步循环回 0；`set_state` 拒绝未知 animation

---

### Task 5: 调整 `tests/test_tui_app.py`

- [ ] **Step 1**: 把 `test_mascot_cycles_through_animations` 改名为 `test_mascot_cycles_through_frames`
- [ ] **Step 2**: 内部循环 `advance_state + _tick_mascot` 8 次（2 个完整循环），断言 `seen_text ≥ 2`

---

### Task 6: 版本号同步

- [ ] **Step 1**: `pyproject.toml` → `version = "0.2.3"`
- [ ] **Step 2**: `src/investpilot/__init__.py` → `__version__ = "0.2.3"`
- [ ] **Step 3**: `tests/test_smoke.py` → 期望 `"0.2.3"`

---

### Task 7: 验证脚本 + 截图

- [ ] **Step 1**: `tools/verify_logos.py` 路径改到 `docs/iterations/v0.2.3/verify/`，循环简化为单 animation 4 帧
- [ ] **Step 2**: `uv run python tools/verify_logos.py` 检查 `verify/app_boot.png` + `mascot_blink_ear_{0..3}.png` + `mascot_zoom_{open,half,closed,decay}.png` 共 9 张
- [ ] **Step 3**: 全套测试：`uv run pytest && uv run ruff check .` 全绿

---

### Task 8: 复盘 + 提交

- [ ] **Step 1**: `docs/iterations/v0.2.3/RETRO.md` 写事实 / 偏差 / 验收对照 / 剩余风险
- [ ] **Step 2**: `git add -A && git commit -m "chore(v0.2.3): bump version to 0.2.3 and finalize docs"`

---

## Spec coverage

| SPEC §7 验收 | Task |
|--------------|------|
| 1. 启动 logo 16×9 cells | 1, 3 |
| 2. mascot 常驻 | 3, 5 |
| 3. blink_ear 循环 | 1, 4, 5 |
| 4. 多轮不影响 | 5（已有聊天测试） |
| 5. pytest 全绿 | 4, 5, 6 |
| 6. ruff 通过 | 4, 5, 6 |
| 7. 版本号同步 | 6 |
| 8. preview/verify PNG 可见 | 7 |

## Placeholder scan

无 TBD；规格中所有尺寸/颜色/帧序都已固定。

## Type consistency

`HEAD_CELLS_W/H`、`SMALL_CELLS_W/H`、`FRAMES_PER_ANIM` 在 build/asset/render/test 四处一致。
