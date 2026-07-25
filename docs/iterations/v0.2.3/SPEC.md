# InvestPilot v0.2.3 SPEC — Logo 收束 + 闪烁-动耳单动画

> 状态：方案已对齐（用户在 v0.2.2 review 后拍板）
> 日期：2026-07-25
> 依赖：v0.2.2 像素 Logo 系统已落地

## 1. 目标

收束 v0.2.2 留下的 4 个体验问题：

- **大 Logo 不再重复造轮子**：与 mascot 共享同一份 16×9 cells 像素艺术
- **小 Logo 留呼吸空间**：face 内缩 1 cell，上下左右各留出 1 cell padding
- **动画收敛到一处**：原本 5 类（挥手 / 动耳 / 摇尾 / 眨眼 / 探头）合并为单一 4 帧 `blink_ear`（闭眼与外倾双耳同步）
- **消除右下角直角残影**：移除 wave 等动画残留的像素帧

## 2. 范围

### 2.1 In scope

| 项 | 说明 |
|----|------|
| 资产 | `tools/build_logos.py` 重写：单 `draw_head()`（16×9 cells）+ 单一 `_blink_ear()` 动画 |
| 资产数据 | `_logo_assets.py` 改名为 `HEAD`（替代 `BIG_HEAD`/`SMALL_HEAD`）+ `SMALL_FRAMES["blink_ear"]`（4 帧） |
| 渲染层 | `interface/logo.py`：`render_head()`（替代 `render_big_head`）+ `render_small_frame("blink_ear", n)` + `render_small_static()` |
| TUI 集成 | `tui_app.py.on_mount`：大 boot logo 调 `render_head()`；mascot ticker 0.10s/帧循环 4 帧 |
| 测试 | `tests/test_logo.py` 重写：shape/帧/状态机；`tests/test_tui_app.py` 调整 mascot cycle 测试 |
| 版本号 | 0.2.2 → 0.2.3 |
| Preview / Verify | `docs/iterations/v0.2.3/preview/*.png`、`docs/iterations/v0.2.3/verify/*.png` |

### 2.2 Out of scope

- ASCII 风格资产回归
- 终端调色板自定义
- mascot 与 lifecycle 事件映射（仍纯 review 阶段循环）

## 3. 视觉规格

### 3.1 Cat 基础造型（16 cells × 9 cell-rows）

- 双耳：左右三角，DARK_O 外侧 + ORANGE 内侧 + LIGHT 内耳
- Face：rounded_rect `[px(1.5, 2.5), px(14.5, 8.0)]` ← 比 v0.2.2 缩 1 cell（之前 `[px(0.5, 2), px(15.5, 8.5)]`）
- 双眼：椭圆，row 3.6-5.6，col 4-6 与 10-12
- 鼻：三角 row 5.2-5.9
- 嘴：wigzag "w"
- 胡须：每侧 2 根
- 基线：row 8.4-9 黑条

### 3.2 `blink_ear` 4 帧序列

| Frame | Eye | Ear tilt | 描述 |
|-------|-----|----------|-----|
| 0 | open（圆） | 0 | 正常姿态 |
| 1 | half（弧） | 0.7 cell 外倾 | 半闭半倾 |
| 2 | closed（线） | 1.5 cell 外倾 | 全闭+外倾 peak |
| 3 | half（弧） | 0.7 cell 外倾 | 回落 |

循环时长：4 帧 × 0.10s/帧 = **0.4s/loop**

## 4. 调色板（与 v0.2.2 相同）

| Index | Hex | 用途 |
|-------|-----|------|
| 0 | transparent | 透明（底色） |
| 1 | `#F2B675` | 主体橙 |
| 2 | `#E89B4A` | 深橙（耳外、轮廓） |
| 3 | `#FCE3C8` | 浅杏（内耳、脸颊高光） |
| 4 | `#3B2A20` | 深棕（嘴、胡须、ear 描边） |
| 5 | `#221814` | 近黑（眼/瞳孔） |

## 5. 文件清单

| 路径 | 状态 | 职责 |
|------|------|------|
| `tools/build_logos.py` | 重写 | PIL 绘制 + 量化 |
| `src/investpilot/interface/_logo_assets.py` | 重新生成 | grid 数据（`HEAD` + `SMALL_FRAMES["blink_ear"]`） |
| `src/investpilot/interface/logo.py` | 重写 | 半块字符渲染 API |
| `src/investpilot/interface/tui_app.py` | 改 | boot 用 `render_head`，mascot 单动循环 |
| `tools/verify_logos.py` | 简化 | 截 4 帧 + zoom 截图 |
| `tests/test_logo.py` | 重写 | shape/渲染/状态 |
| `tests/test_tui_app.py` | 调整 | mascot cycle 测试 |
| `tests/test_smoke.py` | 改 | 版本号期望 `0.2.3` |
| `pyproject.toml` | 改 | version `0.2.3` |
| `src/investpilot/__init__.py` | 改 | `__version__ = "0.2.3"` |
| `docs/iterations/v0.2.3/{PLAN,RETRO}.md` | 新增 | 计划 + 复盘 |
| `docs/iterations/v0.2.3/preview/*.png` | 新增 | 5 张 PIL 源预览 |
| `docs/iterations/v0.2.3/verify/*.png` | 新增 | headless 截图 |

## 6. 错误处理

- `render_*` 检查 grid shape 异常 → 测试覆盖
- interval tick 内 widget detached → 静默 stop（保留 v0.2.1/2.2 行为）

## 7. 验收

1. `invest-pilot chat` 启动后 transcript 首条是 16×9 cells 橙猫（与 mascot 同尺寸）
2. mascot 启动即显示在 input 上方左对齐；常驻不依赖 thinking 状态
3. mascot 自动循环 `blink_ear`：睁眼立耳 → 半闭半斜 → 全闭+外倾 → 半闭半斜 → ...
4. 连发多轮不影响 mascot 显示；chat 功能完全保留
5. `uv run pytest` 全绿（含新增的 `blink_ear` 帧差异测试）
6. `uv run ruff check .` 通过
7. `pyproject.toml` / `__init__.py` / `tests/test_smoke.py` 版本号同步到 `0.2.3`
8. `docs/iterations/v0.2.3/preview/head.png` 可见；`verify/mascot_blink_ear_*.png` 4 帧截图可见

## 8. 测试计划

| 测试 | 要点 |
|------|------|
| `test_logo.py` | PALETTE=6；ANIMATIONS=("blink_ear",)；HEAD 18×16；SMALL_FRAMES 单键 4 帧 shape；`render_head` 含半块字符；`render_small_frame("blink_ear", 0..3)` 有差异；state 切换 + advance 循环正确 |
| `test_tui_app.py` | 启动后 transcript 含 markup=True 大 logo；`_tick_mascot` 8 次后 ≥ 2 个不同渲染 |
| `test_smoke.py` | 版本号 = `0.2.3` |

## 9. 风险

| 风险 | 缓解 |
|------|------|
| 用户再次 review 后还要求微调 | 由 v0.2.3 SPEC 列出关键约束（cat face padding / 单动画 / 共享 head），后续微调只改 `draw_head` 或帧表 |
| 终端宽度 < 16 列截断 | 仍是边缘 case，靠终端自然换行，不算 break |
| 单动画无事件映射 | 短期内仍纯 review 阶段循环；下一轮 v0.2.4 按需映射 lifecycle |
