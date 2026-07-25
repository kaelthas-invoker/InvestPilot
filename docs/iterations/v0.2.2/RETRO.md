# InvestPilot v0.2.2 RETRO — 橙猫 Logo 重做 + 5 类动态小 Logo

> 日期：2026-07-25

## 事实

- 重做 v0.2.1 的 ASCII 风格柴犬 Logo，换成 PIL 程序化绘制 + 6 色调色板量化 + 半块字符 `▀ ▄` 渲染。
- 引入 `tools/build_logos.py`（仅 dev 依赖 Pillow）作为唯一资产生成入口；产物 `_logo_assets.py` 随仓库提交，runtime 不需要 Pillow。
- 5 类动态小 Logo（wave / ear / tail / blink / peek）× 4 帧，自动常驻循环播；尚未映射到 lifecycle 事件，本轮纯 review 用。
- 版本号 0.2.1 → 0.2.2。
- 最终验证：`uv run pytest` 39 passed；`uv run ruff check .` 通过。

## 偏差与根因

| 偏差 | 根因 | 已应用改进 |
|------|------|-----------|
| 第一版 build 脚本生成的资产文件多 key 之间缺逗号 | writer 直接 join 没有 dict key 之间的逗号 | 改用 `enumerate` 显式补 `,`，下一个 key 修正 |
| `tuple[str, ...]` 推导式把 `None` 当二元组解包 | 未用 `enumerate`，直接对 PALETTE 解包 idx, c | 改成 `for idx, c in enumerate(PALETTE)` |
| tail/ear 动画首版变化被量化吞掉 | 半 cell 偏移过小，4-corner 采样不到 | 改成整 cell 偏移（dx=±1.2 cell），加大 arc 的 width |
| Textual CSS 不支持 `white-space` | 沿用了 v0.2.1 的 CSS，升级 v0.2.2 时发现 | 删除该属性，半块字符靠 Static `markup=True` 自动保留换行 |
| Static 没有 `renderable` 属性 | 旧测试代码沿用 v0.2.1 的 `widget.renderable` 写法 | 改为 `_static_text` 帮助函数，遍历 `render()` 返回的 Rich 对象，取 plain/markup 字段 |

## 验收对照（SPEC §12）

1. 启动大橙猫：`on_mount` 挂染色大 logo（含半块字符 + palette 色）—— `test_app_boot_and_send_smoke` 通过
2. 对话可滚动：现有 `_append_line` + `scroll_visible()` 保留 —— 通过
3. 启动即常驻小橙猫：`#mascot` 在 `on_mount` 后即有内容 —— 通过
4. 5 类自动轮播：`test_mascot_cycles_through_animations` 在 25 ticks 内观察到 ≥ 2 种不同帧 —— 通过
5. 连发多轮不受影响：smoke 完整跑通 —— 通过
6. `uv run pytest` 39 全绿 —— 通过
7. `uv run ruff check .` —— 通过
8. preview PNG 可见：`docs/iterations/v0.2.2/preview/{big.png, small_{wave,ear,tail,blink,peek}_{0..3}.png}` 共 21 张 —— 通过

## 剩余风险

- 小 Logo 5 类动画在 144px 画布下半块渲染后偏小：单细节（如 tail/ear 的 1-cell 偏移）可能肉眼看不出来，需要用户在终端实际跑 `invest-pilot chat` 评分；如觉得太静默，下一轮可加大偏移或加 outline 高对比
- 大 Logo 第一行为 5 根乱毛（visual 锚点里也有），但 palette 只有 6 色，没有更深的"轮廓"色，耳朵外侧的对比与原参考有差距；下一轮可考虑扩展 palette 到 8 色或加 outline
- 当前没有把动画映射到 lifecycle 事件，纯 review 轮播；下一轮要决定 wave=greeting / ear=thinking / tail=response-arriving / peek=idle / blink=状态切换 中选
- 终端宽度 < 32 cols 时大 logo 自动换行；用户可在小终端上看到截断，不算 break，只是个 edge case 提示

## 与 v0.2.1 的差异（迁移点）

- `logo.HEAD_ART` / `logo.RUN_FRAMES` / `logo.render_head_markup` / `logo.run_frame_text` 全部替换为 `_logo_assets.BIG_HEAD` / `_logo_assets.SMALL_FRAMES` / `logo.render_big_head` / `logo.render_small_frame` / `logo.render_small_static`
- `_start_thinking` / `_stop_thinking` 中跑狗相关逻辑删除；改为常驻 `_tick_mascot`
- `#input-dock` 容器布局新增 `#mascot`，位于 `#thinking` 之前

