# InvestPilot v0.3.0 RETRO — 小 logo 重绘

> 日期：2026-07-25

## 事实

- 猫的几何从 `draw_head()` 抽成参数化的 `draw_cat(cells_w, cells_h, *, ear_tilt, eye_state, whiskers, forehead_arc)`。坐标写在 16×9 参考网格上，渲染到别的网格时乘 `sx/sy` 再用 PIL 重新光栅化。
- 大 logo 改为 `draw_cat(16, 9)`，与改动前**像素级零差异**（`ImageChops.difference(...).getbbox() is None`）。
- 小 logo 定为 12×7，去胡须、保留额头弧，走同一份几何。
- 资产数据模型从"animation → 4 帧位图"改为"**poses + schedule**"：5 个唯一位图 + 24 帧姿态名序列。24 帧里有 12 帧是同一个 `idle`，两级结构让这些保持帧不占额外体积。
- 动画为交替式：摆耳朵 0.8s → 静止 1.2s → 眨眼 0.4s，一轮 2.4s。
- 删除上一轮遗留的 `_make_small_variant`（另画路径）与 `tools/verify_variants.py`。
- 版本号 0.2.3 → 0.3.0。
- 最终验证：`uv run pytest` **50 passed**；`uv run ruff check .` 通过。

## 偏差与根因

| 偏差 | 根因 | 已应用改进 |
|------|------|-----------|
| 眨眼在 12×7 下量化后只翻转 2/168 cells，终端里看不出来 | 闭眼眼睑做成"等宽收缩"，而单眼在小网格上只有约 1.5 cells 宽，收缩后落不进新的采样块 | 闭眼改为**比睁眼更宽更低**的眼睑条；几何用网格搜索按实测 cell 差异挑选，差异从 2 提到 8 |
| 首版闭眼条宽 3.4 cells，读起来像"怒眉"不像闭眼 | 只按可见度指标调，没看视觉语义 | 收窄到 2.2 cells（接近睁眼宽度），可见度仍有 8 cells，语义正确 |
| 前几轮小 logo 反复被判"不相似" | 两种错误路径：小网格上另画（身份不一致）、位图 LANCZOS 重采样（线条糊） | 改为同一份几何 + 矢量重光栅化，二者都避开 |
| 版本号 bump 后 2 个 smoke 测试红 | 测试硬编码 `"InvestPilot v0.2"` 前缀 | 改为从 `investpilot.__version__` 拼断言，之后 bump 不再需要改测试 |

## 验收对照（SPEC §8）

| # | 验收项 | 结果 |
|---|--------|------|
| 1 | 大 logo 像素级不变 | 通过 — diff bbox 为 `None` |
| 2 | `HEAD` sha256 钉死 | 通过 — `test_big_logo_geometry_unchanged` |
| 3 | 最长边 ≤ 12 | 通过 — `test_mascot_longest_side_within_cap` |
| 4 | 5 姿态互不相同 | 通过 — `test_every_pose_is_distinct` |
| 5 | 动作可见度阈值 | 通过 — `test_ear_wobble_is_visible`（ear2 = 16）、`test_blink_is_visible`（blink2 = 8） |
| 6 | schedule 结构与节奏 | 通过 — `test_schedule_covers_both_motions`、`test_blink_is_occasional_not_constant`（8%）、`test_loop_is_long_enough_to_feel_natural`（2.4s） |
| 7 | 一轮渲染出的画面数 == 唯一姿态数 | 通过 — `test_rendered_frames_change_across_the_loop`、`test_mascot_walks_its_whole_pose_schedule` |
| 8 | 发消息后 mascot 完好 | 通过 — `test_mascot_survives_a_chat_round` |
| 9 | pytest / ruff | 通过 — 50 passed、All checks passed |
| 10 | TUI 截图覆盖 | 通过 — `verify/` 下 `app_boot` + 5 个姿态 |

## 设计取舍记录

**为什么用"同一份几何 + 缩放重绘"而不是两套画法或位图缩放？**

三条路径的对比：

| 路径 | 身份一致性 | 线条清晰度 | 维护成本 |
|------|-----------|-----------|---------|
| 小网格上另画（v0.2.9 及更早） | 差 — 两只不同的猫 | 好 | 高 — 改一处要改两处 |
| 位图 LANCZOS 缩放（v0.2.10/11） | 好 | 差 — 抗锯齿糊边，量化后发散 | 低 |
| **同一份几何 + 矢量重光栅化（本轮）** | **好** | **好** | **低 — 单一坐标表** |

代价是 `draw_cat` 的坐标表要能承受非整数缩放（`sy = 7/9` 不是整数比），所以描边宽度、圆角半径都要跟着缩放并设 1px 下限。

**为什么闭眼眼睑要比睁眼宽？**

这不是美术偏好，是终端网格的分辨率约束。12×7 下单眼约 1.5 cells 宽、0.8 cells 高，等宽眼睑落在同一批采样块里，量化后几乎没有 cell 改变颜色。眼睑加宽让它溢出到相邻 cell，才在终端里形成可见的变化。这类"因为渲染介质的量化特性而必须偏离写实几何"的决定，已写进 `draw_cat` 的注释，避免后来者按写实逻辑改回去。

## 剩余风险

| 风险 | 是否需要处理 |
|------|-------------|
| `blink1` 过渡帧只有 2 cells 差异 | 不需要 — 它是 0.1s 过渡帧，作用是平滑 open→closed 的跳变，不要求单独可读 |
| 10×6 / 8×5 变体只在 preview 里，未接 runtime | 不需要 — 用户已选 12×7；变体保留供后续切换，切换只需改 `MASCOT_CELLS_W/H` |
| 终端宽度 < 16 cells 时大 logo 换行 | 不需要 — 既有 edge case，本轮未引入 |
| 动画未映射 lifecycle 事件 | 待定 — 下一轮若要做，schedule 模型已能直接支持按状态切换不同 schedule |
