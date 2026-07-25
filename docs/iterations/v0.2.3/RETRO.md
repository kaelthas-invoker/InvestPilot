# InvestPilot v0.2.3 RETRO — Logo 收束到单动画

> 日期：2026-07-25

## 事实

v0.2.2 review 后用户给 4 点反馈，本轮一次性落地：

1. **大 Logo 与小 Logo 共享 16×9 cells**：删除原 `draw_big`（32×18 cells），改为与 mascot 共用 `draw_head()`。
2. **小 Logo face 缩 1 cell**：从 `[px(0.5, 2), px(15.5, 8.5)]` 调整为 `[px(1.5, 2.5), px(14.5, 8.0)]`，上下左右各留 1 cell 呼吸空间。
3. **5 类动画合并为单一 `blink_ear`**：消除 wave / tail / peek 等带来的视觉边角残留问题；4 帧（睁眼+立耳 → 半闭+外倾 0.7 → 全闭+外倾 1.5 → 半闭+外倾 0.7），0.4s/loop。
4. **底部直角消失**：因为 wave 动画被移除，旧 wave_2 中留下的 paw 切角残影随之消失。

版本号 0.2.2 → 0.2.3；测试 39 → **40 passed**；ruff 全绿。

## 偏差与根因

| 偏差 | 根因 | 已应用改进 |
|------|------|-----------|
| `test_mascot_cycles_through_animations` 在 v0.2.3 数据下永远只能看到 1 帧 | 旧测试假设 5 类动画循环 ≥ 2 种；v0.2.3 收敛到 1 类 4 帧后必须直接调用 `_tick_mascot`，不能用 `pilot.pause` 等定时器 | 重写为 `test_mascot_cycles_through_frames`，直接 `advance_state + _tick_mascot` 8 次 |
| `render_big_head` 老调用点失效 | rename 到 `render_head` | 在 `logo.py` 留 `render_big_head = render_head` 别名，旧测试/外部代码仍可工作 |
| BigHead 与 SmallHead 双 artifacts | 用户原话"大 logo 缩小至小 logo 参数"——意味着不再分两套资产 | 改为单一 `HEAD` 常量 |

## 验收对照（SPEC §7）

1. 启动 logo 16×9 cells —— `verify/app_boot.png` 显示 boot top cat 16 cells 宽
2. mascot 常驻左下角 —— `verify/app_boot.png` 仍可见 `#mascot` Static
3. blink_ear 4 帧循环 —— `verify/mascot_blink_ear_{0..3}.png` + `mascot_zoom_{open,half,closed,decay}.png` 9 张已生成
4. 连发多轮不影响 —— 既有 `test_app_boot_and_send_smoke` 仍 PASS
5. `uv run pytest` 40 全绿 —— PASS
6. `uv run ruff check .` 全绿 —— PASS
7. 版本号同步 —— `pyproject.toml` / `__init__.py` / `test_smoke.py` 三处均为 `0.2.3`
8. preview + verify PNG 可见 —— `preview/head.png` + 4 张 `preview/blink_ear_*.png` + 9 张 `verify/*.png`

## 剩余风险

| 风险 | 是否需要 owner 行动 |
|------|----------------------|
| Mascot 仍然常驻、未映射 lifecycle | 不需要：review 阶段；下一轮 v0.2.4 决定是否做事件映射 |
| 终端宽度 < 16 cells 时仍截断 | 不需要：edge case，按 SPEC 不处理 |
| `render_big_head` 别名未来 v0.3.x 想删 | 不需要：only present for compat；标记 deprecated 更好 |

## 与 v0.2.2 的差异（迁移点）

- 删除 `_logo_assets.BIG_HEAD` / `BIG_HEAD_CELLS_W` / `BIG_HEAD_CELLS_H` → 改为 `HEAD` / `HEAD_CELLS_W` / `HEAD_CELLS_H`
- 删除 `_logo_assets.SMALL_FRAMES["wave"/"ear"/"tail"/"blink"/"peek"]` → 仅保留 `blink_ear`
- `logo.ANIMATIONS` 由 `("wave","ear","tail","blink","peek")` 变为 `("blink_ear",)`
- `logo.render_big_head` 仍可调用（转发到 `render_head`）；旧测试无需改
- 全部 PNG 从 `docs/iterations/v0.2.2/{preview,verify}/` 复制到 `docs/iterations/v0.2.3/`，旧目录继续保留为历史

## 已落地 commits

- `feat(v0.2.3): unified 16×9 cat head + blink_ear animation`
- `feat(v0.2.3): half-block rendering for big and small cat logos`
- `feat(v0.2.3): mount 16×9 cat boot logo and resident mascot with blink_ear`
- `test(v0.2.3): rewrite logo + tui tests for blink_ear single animation`
- `chore(v0.2.3): bump version to 0.2.3 and write retro`
