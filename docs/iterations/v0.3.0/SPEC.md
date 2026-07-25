# InvestPilot v0.3.0 SPEC — 小 logo 以大 logo 为锚点重绘

> 日期：2026-07-25
> 需求来源：用户口述 + 采访确认（四问四答）

## 1. 背景

v0.2.6 ~ v0.2.11 期间小 logo 反复返工，根因有两个：

1. **另画**：早期变体在小网格上重新摆坐标，出来的猫和大 logo 不是同一只（用户："完全不相似"）。
2. **重采样**：v0.2.10/v0.2.11 改用 `PIL.Image.resize(LANCZOS)` 把大 logo 缩小。身份保住了，但重采样把线条糊掉，量化后细节发散。

用户结论：小 logo 要**以大 logo 为锚点缩小重绘**，且换一个实现路径重做。

## 2. 采访确认结果

| 问题 | 用户回答 |
|------|---------|
| 小 logo 尺寸 | 最长边不超过 12，**效果最重要** |
| 摆耳朵 + 眨眼睛怎么组合 | **交替**：先摆耳，再眨眼 |
| 眨眼频率 | **偶尔眨（自然）**，不要一直眨 |
| 缩小后细节取舍 | **去掉胡须**；额头弧视效果决定 |

## 3. 目标

- 小 logo 与大 logo 是**同一份几何**，不是两套画法，也不是位图重采样
- 大 logo 视觉**零变化**（用户已签收的造型，不允许漂移）
- 动画为"摆耳朵 + 眨眼睛"，两段交替，眨眼为偶发
- 动画在 12×7 终端网格上**实际可见**（可量化验证，不靠肉眼主观判断）

## 4. 范围

### In scope

| 项 | 说明 |
|----|------|
| `tools/build_logos.py` | 猫的几何抽成单一 `draw_cat(cells_w, cells_h, *, ear_tilt, eye_state, whiskers, forehead_arc)`；坐标按 `sx=cells_w/16, sy=cells_h/9` 缩放后用 PIL 重新光栅化 |
| 姿态数据模型 | 资产从"4 帧位图"改为 **poses + schedule** 两级：5 个唯一位图 + 24 帧姿态名序列 |
| `_logo_assets.py` | 输出 `HEAD`、`SMALL_POSES`、`SMALL_SCHEDULE`、`SMALL_CELLS_W/H` |
| `interface/logo.py` | 按 schedule 索引渲染；`render_big_head` / `render_pose` / `render_small_frame` / 帧游标 |
| `interface/tui_app.py` | tick 走 `advance_frame()` |
| 测试 | 大 logo sha256 钉死；动画可见度阈值断言；schedule 结构断言 |
| 版本号 | 0.2.3 → 0.3.0（`logo.py` 公开 API 有破坏性变更） |

### Out of scope

- 大 logo 造型任何改动
- 动画映射到 assistant lifecycle 事件（仍是常驻自动循环）
- 终端图像协议 / 调色板自定义

## 5. 几何与尺寸

| 项 | 值 |
|----|----|
| 参考网格 | 16×9 cells（几何坐标的书写基准） |
| 大 logo | 16×9 cells，`whiskers=True`，`forehead_arc=True` |
| 小 logo | **12×7 cells**（最长边 12，满足约束），`whiskers=False`，`forehead_arc=True` |
| 缩放系数 | `sx = 12/16 = 0.75`，`sy = 7/9 ≈ 0.778` |
| 描边宽度 | `max(1, round(w * min(sx, sy)))`，保证 1px 下限 |

额头弧保留：在 12×7 量化后仍造成 6 cells 差异，是大 logo 的标志性特征之一，且未变成噪点。

## 6. 姿态与帧表

5 个唯一姿态，只变化两个参数：

| 姿态 | ear_tilt | eye_state |
|------|----------|-----------|
| `idle` | 0.0 | open |
| `ear1` | 0.7 | open |
| `ear2` | 1.4 | open |
| `blink1` | 0.0 | half |
| `blink2` | 0.0 | closed |

24 帧 schedule（0.10s/帧 = 2.4s 一轮）：

```
帧 0-7    idle ear1 ear2 ear1 idle ear1 ear2 ear1   摆耳朵两次   0.8s
帧 8-19   idle × 12                                  静止        1.2s
帧 20-23  blink1 blink2 blink1 idle                  眨眼一次     0.4s
```

眨眼占比 2/24 ≈ 8%，满足"偶尔眨"。

## 7. 眼睛闭合几何的特别说明

闭眼眼睑**比睁眼更宽更低**，不是等宽收缩。原因：12×7 下单眼只占约 1.5 cells 宽，等宽眼睑量化后只翻转 2/168 个 cell，终端里完全看不出在眨眼。

几何由**实测量化差异**确定（`/tmp/tune_eyes.py` 网格搜索），不靠肉眼：

| 姿态 | vs idle 的 cell 差异 |
|------|---------------------|
| `ear1` | 10 |
| `ear2` | 16 |
| `blink1` | 2（0.1s 过渡帧，不要求单独可读） |
| `blink2` | 8 |

## 8. 验收标准

1. `draw_cat(16, 9)` 与改动前的大 logo **像素级完全一致**
2. `HEAD` 网格 sha256 等于钉死值 `f8367d21…`
3. 小 logo 最长边 ≤ 12
4. 5 个姿态位图互不相同
5. `ear2` vs `idle` ≥ 10 cells；`blink2` vs `idle` ≥ 8 cells
6. schedule 含 `ear1/ear2` 与 `blink1/blink2`；闭眼帧占比 ≤ 20%；循环 ≥ 2.0s
7. 走完一轮 schedule 渲染出的不同画面数 == 唯一姿态数
8. 发送消息后 mascot 仍在渲染合法姿态
9. `uv run pytest` 全绿；`uv run ruff check .` 通过
10. TUI 截图覆盖 5 个姿态 + 启动态

## 9. 风险

| 风险 | 处理 |
|------|------|
| 大 logo 几何被后续改动误伤 | sha256 钉死测试；改动必须显式更新 digest |
| 动画可见度回退 | cell 差异阈值写成断言，不是注释 |
| `logo.py` API 破坏性变更 | 主版本号从 0.2 升到 0.3；旧别名（`render_head`/`ANIMATIONS`/`advance_state`）全部移除，不留兼容层 |
| 更小尺寸（10×6 / 8×5）未接入 runtime | 仅作为 preview 变体保留，供后续按需切换 |
