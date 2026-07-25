# InvestPilot v0.2.2 SPEC — 重做大小 Logo + 5 类动态小 Logo

> 状态：方案待用户最终确认（澄清已对齐：橙猫 + 半块字符 + 全自动循环 + 4 帧/动画）
> 日期：2026-07-25
> 依赖：v0.2.1 像素 Logo 已落地；TUI 多轮聊天、流式、错误恢复可用

## 1. 目标

替换 v0.2.1 的"像素柴犬 + 跑狗"实现，给 TUI 注入更鲜明、更有性格的品牌形象，并准备好 v0.2.3 选定映射事件的素材库。

- **新大 Logo**：橙猫半块字符渲染，启动时显示在对话区最上方，分辨率接近 Claude Code 启动 logo 的视觉体量（参考而非照搬）
- **新小 Logo**：尺寸约为大 Logo 的一半，**一直可见**、固定在对话框（Input）上方、左下角；不再做"从左往右跑动"。常驻设计便于 review 全部 5 类动画，下一轮再考虑事件映射/闲时静默
- **5 类动态效果**：挥手 / 动耳朵 / 摇尾巴 / 眨眼睛 / 从下往上探头，**全部 4 帧自动循环播完**；每类播完 4 帧再切下一类（`wave→ear→tail→blink→peek→wave...`），便于用户 review 后再做事件映射
- **实现方式**：全部使用 Unicode 半块字符 `▀` `▄` 渲染，不再用纯 ASCII（v0.2.1 的 `█▄▀▓░` 也归类为 ASCII 风格的旧实现，本次升级为彩色像素块）
- **测试与回归**：v0.2.1 全部测试保留通过，新增资产与渲染单元测试；现有 TUI 行为（聊天/流式/多轮/错误）不受影响

## 2. 范围

### 2.1 In scope

| 项 | 说明 |
|----|------|
| 资产生成脚本 | `tools/build_logos.py`：PIL 绘制橙猫 + 5 类动画各 4 帧，输出 PNG 中间产物 + 校验图 + Python 常量文件 |
| 资产数据 | `src/investpilot/interface/_logo_assets.py`（自动生成、随仓库提交）：大 logo 网格、5×4 小 logo 帧网格、palette 颜色 |
| 渲染模块 | `src/investpilot/interface/logo.py`：把 grid 数据用 `▀`/`▄` + Rich markup 转为可绘制到 `Static` 的字符串 |
| TUI 集成 | `tui_app.py`：启动挂大 logo；输入框上方新增左对齐小 logo 容器（不再做横向滚动），**常驻可见**；启动时即循环播 5 类动画各 4 帧，共 20 帧一轮 |
| 测试 | `tests/test_logo.py`：大/小 logo 网格尺寸、5×4 帧形状、调色板无重复；`tests/test_tui_app.py` 增补：启动消息无小 logo 残留、thinking 期内可观察到帧切换、停止后清空 |
| 依赖 | `pyproject.toml` dev 组新增 `pillow>=10.0.0`（仅构建/测试用，不进运行时依赖） |

### 2.2 Out of scope

- PNG/SVG 真实位图直接通过终端图像协议展示（旧实现 + 大量终端不可用）
- 5 类动画具体事件映射（v0.2.3 根据 review 决定 wave=打招呼、tail=thinking、peek=idle 等）
- 大 logo 之外的 splash / welcome 文本优化
- 颜色主题切换、关闭 Logo 开关

## 3. 视觉锚点

用户提供 3 张视觉参考（`~/Downloads/wechat_2026-07-25_*`）：

1. 黑色剪影猫从基线探头 + 大圆眼 + 卷尾（戏剧化、对比强）
2. **橙色小猫正面**：三角耳、内耳浅色、深色圆眼、三根胡须、"w" 形嘴、头顶 5 根乱毛、底部基线 ← **本次参考主体**
3. 橙色 + 白色 Shiba 双爪合抱姿态（友好、拥抱感）

造型选取为参考图 2（橙猫正面）+ 半块像素化；保留胡须和"w"嘴特征。颜色梯度（24-bit ANSI）：

- 主体橙：`#F2B675`（暖橙）
- 边缘橙：`#E89B4A`（稍深橙，用于耳外侧/底部）
- 内耳/脸颊高光：`#FCE3C8`（浅杏色）
- 鼻 / 嘴 / 胡须：`#3B2A20`（深棕黑）
- 眼睛 / 瞳孔：`#221814`（近黑）
- 背景 / 基线：`transparent`（无背景色，跟随终端底色）

## 4. 大 Logo 规格

| 属性 | 值 |
|------|-----|
| 网格宽 | 32 cells |
| 网格高 | 18 cells（半块字符 = 36 视觉行） |
| 锚定位置 | 启动 `on_mount`，写入 transcript 第一条 `Static(markup=True)` |
| 视觉风格 | 整只猫头正面：双耳 + 头顶乱毛 + 圆眼 + "w"嘴 + 两侧三根胡须 + 底部基线 |
| 颜色 | 上述 6 色调色板 + 透明度 fallback |
| 居中策略 | `Static(width=100%)` 内 Rich 自动居中；右空白用半块字符与底色对齐 |

参考 Claude Code 启动 logo 的"在 24 行终端高度内、约 1/2 屏宽"体量：32×18 cells ≈ 在 80 列终端占据中心 40%、纵向 36 行（终端容得下）。

## 5. 小 Logo 规格（基础姿态）

| 属性 | 值 |
|------|-----|
| 网格宽 | 16 cells（大 logo 的一半） |
| 网格高 | 9 cells（大 logo 的一半 → 18 视觉行） |
| 锚定位置 | 固定在 `#input-dock` 内、`Input` 上方、左对齐（不再 padding 滚动） |
| 视觉风格 | 与大 logo 同一只猫的简化版，保留眼/耳/嘴/胡须，去掉头顶乱毛细节 |
| 动静边界 | 大小 logo 的胡须、耳朵外侧保持一致；只在"出现差异"的区域用动画 grid 覆盖基础帧 |

## 6. 5 类动态小 Logo 规格

每类动画 **4 帧**；启动后即按下表序帧号 0→1→2→3→0 循环；5 类动画依次串接：`wave → ear → tail → blink → peek → wave → ...`；每类播完一个 4 帧循环再切下一类，保证 review 时能看完整循环。**常驻可见**，不依赖 thinking 状态。

| 动画 | 帧 0 | 帧 1 | 帧 2 | 帧 3 | 触发差异区域 |
|------|------|------|------|------|--------------|
| **wave（挥手）** | 静止 | 右手（画面右侧爪）上抬 1 格 | 右手上抬 2 格（顶位） | 右手回落到 1 格 | 右下爪 |
| **ear（动耳）** | 双耳正常 | 双耳同时向后倾 1 格 | 双耳竖直（回弹到正向） | 双耳向后倾 1 格 | 双耳内侧像素 |
| **tail（摇尾）** | 尾尖下垂 | 尾尖左摆 1 格 | 尾尖下垂（回弹） | 尾尖右摆 1 格 | 右下方尾像素 |
| **blink（眨眼）** | 双眼圆睁 | 上眼睑下落 1/3 | 闭眼（一条线） | 上眼睑下落 1/3 | 双眼睛 |
| **peek（探头）** | 头顶在第 0 行 | 头顶降至第 2 行 | 头顶降至第 4 行 | 头顶降至第 6 行 | 整图平移 |

> 所有动画都是在基础姿态的 cell grid 上覆盖：仅"差异区域"复用基础帧原值；其余 cell 与基础帧一致。这样保证 5×4 帧共 20 张图，每张 ≈ 16×9 cells（≈ 144 cells）。

## 7. 渲染管线（半块字符 `▀ ▄`）

每个 cell 占两个视觉行（终端字符高 ≈ 宽的两倍），通过 `▀`（上块 + 下色）与 `▄`（下块 + 上色）控制上下两像素：

```
cell[r, c] 上色 = grid[2r][c]
cell[r, c] 下色 = grid[2r + 1][c]
若上色 == 下色：            输出 full-block (full) + 颜色 c
若只有上色（无下色 = 透明）：输出 '▀' + 上色
若只有下色（无上色）：       输出 '▄' + 下色
若都为空：                   输出 ' '
```

颜色用 Rich markup `[#RRGGBB]...[/]` 包裹；透明格完全跳过字符，整张图与终端底色融为一体。

颜色决策按调色板 ID 索引 → 24-bit hex；调色板顺序固定，渲染层无 if 分支。

## 8. 资产生成脚本（`tools/build_logos.py`）

只在开发机/CI 一次性产出，**运行时不需要 PIL**：

1. 用 PIL 在 256×144 画布上画大 logo（程序化绘制圆/三角/胡须，无外部图像）；
2. 在 128×72 画布上画小 logo 基础姿态；
3. 基于基础姿态，对 5 类动画的差异区域做帧微调（位移、覆盖）→ 输出 20 张 128×72 PNG；
4. 把每张图缩到目标 cell 网格（32×18 大、16×9 小），按"dominant color"采样到 6 色调色板；
5. 写出 `src/investpilot/interface/_logo_assets.py`：常量 `BIG_LOGO_GRID`、`SMALL_BASE_GRID`、`SMALL_ANIMATIONS: dict[str, list[grid]]`、`PALETTE: list[str]`；
6. 同时写出 `docs/iterations/v0.2.2/preview/*.png`，给用户线下 review 用。

构建可通过 `uv run python tools/build_logos.py` 触发；CI 不需要该脚本（生成产物随仓库提交）。

## 9. TUI 集成

### 9.1 大 Logo 路径

`on_mount` 内：

```
self.query_one("#transcript", VerticalScroll).mount(
    Static(logo.render_big_head(), classes="msg", markup=True)
)
```

`render_big_head()` 返回拼好 markup 的字符串，宽 32 cells；`Static` 父容器自适应居中。已保留 transcript 后续消息可滚动。

### 9.2 小 Logo 路径

替换 v0.2.1 的 `#thinking` 跑狗逻辑：

- 在 `#input-dock` Container 内新增 `Static(id="mascot", markup=True)`，定位左对齐、高度 18 视觉行、`width: auto`；放在 Input 上方；
- 删掉旧的横向 padding 偏移逻辑；保留 `#thinking` 仅作为状态文案（不需要与 run-dog 视觉绑定）
- **`on_mount` 启动即挂 interval** 0.10s（4 帧 × 5 类 = 20 帧一轮，2.0s 大循环），从 `wave-0` 开始；
- `_tick_mascot`：根据全局 `_tick_phase = (phase_index, frame_index)` 选帧 → `mascot.update(logo.render_small_frame(name, frame))`；
- 常驻显示、停止条件仅在 app 退出时生效；发收消息不触发隐藏。

CSS：

```css
#mascot {
    height: auto;
    width: auto;
    align: left top;
    white-space: pre;
}
```

### 9.3 输入响应

`on_input_submitted` 不变；`_handle_send` 内 `_start_thinking()` → 收到首个 text chunk / 异常 → `_stop_thinking()`，与 v0.2.1 保持一致。

## 10. 文件清单

| 路径 | 状态 | 职责 |
|------|------|------|
| `tools/build_logos.py` | 新增 | PIL 绘制 + 量化 → PNG + Python 数据 |
| `src/investpilot/interface/_logo_assets.py` | 新增（生成产物） | grid 数据 + 调色板 |
| `src/investpilot/interface/logo.py` | 重写 | 渲染函数，不再持有 ASCII art |
| `src/investpilot/interface/tui_app.py` | 修改 | 大 logo + 小 mascot 容器 + interval |
| `tests/test_logo.py` | 重写 | grid 尺寸、调色板、render 输出 |
| `tests/test_tui_app.py` | 追加 | 启动大 logo、thinking frame 切换、停止清空 |
| `docs/iterations/v0.2.2/preview/*.png` | 新增 | 用户 review 用的预览 |
| `pyproject.toml` | 修改 | dev 依赖加 `pillow>=10.0.0` |
| `src/investpilot/__init__.py` | 修改 | 版本号 `0.2.1` → `0.2.2` |
| `tests/test_smoke.py` | 修改 | 版本号同步 |

## 11. 错误处理

- `render_*` 任何 grid 形状异常 → 抛 `ValueError`（fail-fast，由测试覆盖）
- interval 内 widget 已 detached → 静默 stop（保留 v0.2.1 行为）
- 非 TTY 场景：`#mascot` 自然不显示，不影响聊天

## 12. 验收标准

1. `invest-pilot chat` 启动后，transcript 首条可见 32×18 cells 的橙猫大 Logo（半块字符 + 多色），并居中
2. 对话区可继续滚动，不被大 Logo 干扰
3. **启动后 input 上方立即出现 16×9 cells 左对齐小橙猫**（常驻，不依赖 thinking 状态）
4. 小橙猫自动按 `wave→ear→tail→blink→peek→wave...` 循环；每类播放完 4 帧再切下一类；流式、错误、空闲均不影响显示
5. 连发多轮对话功能完全不受影响
6. `uv run pytest` 全绿（包含新增的 grid/帧/调色板测试与 TUI 帧切换冒烟）
7. `uv run ruff check .` 通过
8. 5 类动画每个至少出现一帧，运行 `tools/build_logos.py --preview` 后 `preview/` 下产出对应 PNG，用户能用 Finder 看到

## 13. 测试计划

| 测试 | 要点 |
|------|------|
| `test_logo.py` | 大 grid shape (32, 18)；5 类动画 × 4 帧 = 20 帧 shape (16, 9)；调色板 6 色调色一致性；`render_big_head` 含半块字符 `▀`/`▄`；`render_small_frame(name, i)` 含 5×4 frame name 与 frame_index |
| `test_tui_app.py` 追加 | `run_test` 启动后 transcript 含 markup=True 大 logo Static；`#mascot` 在 on_mount 后非空；`_tick` ≥ 6 次后内容至少有过一次跨动画变化；发送消息后多轮不受影响，mascot 持续显示 |

## 14. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 半块字符在某些终端错位 | 用标准 `▀`/`▄`（U+2580/U+2584），不依赖终端图形协议；fallback 终端宽度 < 32 cells 时居中自然换行 |
| 5 类动画拼接后总帧数 20、循环节奏过慢 | 已确认 0.10s/帧 × 20 = 2.0s 完整 loop，节奏匹配"小动作"语义 |
| PIL 仅 dev 依赖，仓库贡献者缺依赖 | 构建产物 `_logo_assets.py` 提交到仓库，运行时无需 PIL；CI 默认安装 dev 依赖 |
| 颜色量化损失细节 | 6 色固定调色板 + dominant-color 采样；cat 主面部纯色，仅背景/胡须/嘴需要像素细节 |
| v0.2.1 ASCII 测试需要清理 | `test_logo.py` 全面重写，旧 ASCII 形状断言不再适用；保留 `_pixel_walk` 等概念性测试名沿用 |
