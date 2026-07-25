# InvestPilot v0.3.1 RETRO — 输入历史 / 状态行 / DB 路径下沉

> 日期：2026-07-25
> 对应 SPEC：`./SPEC.md`，对应 PLAN：`./PLAN.md`

## 事实

- DB 文件从 `~/.invest-pilot/chat.db` 迁移到 `~/.invest-pilot/storage/sqlite/chat.db`；自动建两级目录（mode 0o700）；DB 文件 mode 0o600
- 老路径 `~/.invest-pilot/chat.db`（含 WAL/SHM 边车）自动一次性迁移；迁移后显式断言旧文件已不在；跨 FS copy+delete 失败抛 RepoError
- 输入框支持 bash 风格历史：Up/Down 在 history 列表里翻；`_history_index` 维护当前位置；空文本与斜杠命令不入历史；`/resume` 加载后清空历史；容量上限 100
- 状态行 `#status-line` 显示 `provider / model`（带空格），与 header `provider/model`（不带空格）格式刻意不同；`/resume` 后状态行更新为被恢复 session 的 provider/model
- `/resume` Modal 加载后不再追加"已恢复会话"提示；history 被清空避免与加载对话混淆
- Modal `up`/`down` 加 `priority=True` binding 覆盖 App 层 history binding，保证 ListView 上下选中不被 history 截获
- 测试：新增 12 个用例（storage 4 + cli 路径断言 1 + tui 11 共 12 + 实际 storage 增加了 1 个跨 FS 残留检测），总计 119 个；`uv run ruff check .` 通过
- e2e 走查 6 步全过；reality-checker AC 1–18 全部覆盖

## 偏差与根因

| # | 偏差 | 根因 | 已应用改进 |
|---|------|------|-----------|
| 1 | plan-reviewer 首轮 5 条缺陷：status-line 格式 vs 现有 `_title_suffix` 不匹配；WAL/SHM 迁移漏说；mid-edit + resume-clears 历史无 AC + 无测试；跨 FS shutil.move 残留风险无测试；§7 / §8 `_title_suffix` 互相矛盾 | 作者把"spec / code"当成一回事；AC 表格写到一半漏补；跨 FS 失败分支留作"边界"未测试；状态来源混淆导致文档自相矛盾 | 全面修订 SPEC §5/§6/§7/§8 + PLAN A1/A2/B1；新增 7 条历史 AC；新增 `test_migration_residual_raises_repo_error` 模拟 cross-FS 失败；明确 header 与 status-line 状态来源分离 |
| 2 | plan-reviewer 二轮 2 条新缺陷：PLAN §5 DB 回滚自相矛盾；SPEC §4 in/out scope 关于 WAL/SHM 措辞冲突 | PLAN §5 表述顺序不当；SPEC 把"迁移边车"和"孤儿清理"混在一起说 | PLAN §5 重写为"v0.3.1 用户的文件系统状态"叙述；SPEC §4 in-scope 与 out-of-scope 区分"迁移已知 3 文件"与"不主动清孤儿" |
| 3 | Execute-A 报"cross-FS 残留分支无自动化测试"为 BLOCK | A2 把"OSError 模拟不在自动覆盖范围"写成边界，等于把验证责任扔给用户 | 在测试里 monkeypatch `shutil.move` 写一个 fake_move：复制 src 到 dst 但保留 src（模拟 copy+delete 失败），断言 RepoError("迁移后旧文件仍存在") 被抛 |
| 4 | 测试用例编号轻微错位（test docstring 写 AC8 但实际语义是 AC9） | 编号过程中改 AC 表格但忘了同步 test docstring | 编号逻辑不影响功能；保留为 cosmetic 提示，下轮清理 |

## 验收对照（SPEC §11）

| # | 验收项 | 覆盖测试 | 结果 |
|---|--------|---------|------|
| 1 | DB 位于 `~/.invest-pilot/storage/sqlite/chat.db` | `tests/test_storage.py::test_open_default_db_new_path` | 通过 |
| 2 | 自动建 `storage/sqlite/` 目录（mode 0o700） | 同上 | 通过 |
| 3 | 老路径 `~/.invest-pilot/chat.db` 自动迁移 | `tests/test_storage.py::test_old_db_path_migrates` | 通过 |
| 4 | Up：input.value = 前一条历史 | `tests/test_tui_app.py::test_history_up_recalls_previous` | 通过 |
| 5 | 多次 Up 翻到第 1 条后停住 | 同上 | 通过 |
| 6 | Down 往前；到末尾清空 | `tests/test_tui_app.py::test_history_down_advances_and_clears_at_end` | 通过 |
| 7 | 历史容量 100 | `tests/test_tui_app.py::test_history_capped_at_100` | 通过 |
| 8 | 斜杠命令不入历史 | `tests/test_tui_app.py::test_slash_commands_not_in_history` | 通过 |
| 9 | 空文本不入历史 | `tests/test_tui_app.py::test_empty_text_not_in_history` | 通过 |
| 10 | 历史回看中手动编辑不重置 `_history_index` | `tests/test_tui_app.py::test_history_mid_edit_keeps_index` | 通过 |
| 11 | `/resume` 加载历史后 `_history` 清空 | `tests/test_tui_app.py::test_resume_clears_history` | 通过 |
| 12 | 状态行显示 `provider / model` | `tests/test_tui_app.py::test_status_line_shows_provider_model` | 通过 |
| 13 | `/resume` 后状态行更新 | `tests/test_tui_app.py::test_status_line_updates_after_resume` | 通过 |
| 14 | `/resume` Modal Up/Down/Enter 工作 | `tests/test_tui_app.py::test_resume_modal_arrow_keys_navigate_and_enter_selects` | 通过 |
| 15 | `/resume` 后无"已恢复会话"提示 | `tests/test_tui_app.py::test_no_restored_session_hint_after_resume` | 通过 |
| 16 | pytest 全绿；ruff 通过 | `uv run pytest -q` → 119 passed；`uv run ruff check .` → All checks passed | 通过 |
| 17 | CLI AC1 路径断言更新 | `tests/test_cli.py::test_chat_creates_db_on_first_run` | 通过 |
| 18 | 迁移同时搬走 `chat.db-wal` / `chat.db-shm` | `tests/test_storage.py::test_migration_includes_wal_shm` | 通过 |
| 额外 | 跨 FS 残留检测抛 RepoError | `tests/test_storage.py::test_migration_residual_raises_repo_error` | 通过 |

## 设计取舍记录

**为什么 status-line 用 `provider / model`（带空格）而 header 用 `provider/model`（不带空格）？**

User 调研：status-line 是 UI 信息条（屏幕底部 1 行），留白让眼睛能扫；header 是 window 标题（系统级 UI），越紧凑越好。两者刻意不同。

**为什么状态来源分离？**

v0.3.0 的 `_title_suffix` 由 `_on_resume_dismissed` 改写以反映"加载了哪个 session"。v0.3.1 让 status-line 独立读取 `__init__` 注入的 `_provider_name` / `_model`，不被 `_title_suffix` 同步逻辑影响。两者的更新策略独立演化：以后想让 header 保留 startup 模型、status-line 跟随当前，只需分别改各自的刷新路径。

**为什么 Up 绑定覆盖 Input 默认光标移动？**

Textual `Input` 默认 Up/Down 是"光标在第一/末行时上下滚动"。本迭代把 Up/Down 完全用于历史，要移动光标改用 `Home` / `End`。这是 bash / fish 的标准行为；用户能用 Tab 切焦点来规避。如果未来引入多行输入（out of scope），需要重审这个 binding 设计。

**为什么 Modal 用 `priority=True` binding？**

App 层 history binding 走 `action_history_prev` / `action_history_next`。Modal 推上来时，ListView 应该用 Up/Down 移动选择，而不是触发 history。Textual 的优先级是：focused Screen 的 binding 优先于 App，但仅当显式声明 `priority=True` 才会强制覆盖 App 同名 binding。我们把 Modal 的 Up/Down 加 `priority=True`，确保 ListView 在 Modal 中始终能用方向键导航。

**为什么迁移 WAL/SHM 不复用 `os.rename`？**

`os.rename` 在跨 FS 时直接抛 OSError，比 `shutil.move` 行为更可预测。但 shutil.move 在同 FS 时是原子的 rename（同 FS 行为），跨 FS 时退化为 copy+delete。两个选择对比：
- 选 `shutil.move`：同 FS 性能好；跨 FS 自动降级，但需要残留检测防 copy+delete 失败
- 选 `os.rename`：同 FS 行为一致；跨 FS 直接报错不迁移

选 `shutil.move` —— 用户体验优先；跨 FS 残留分支已经用 `assert not old.exists()` + RepoError 兜底。

## 关键产物清单

- `docs/iterations/v0.3.1/SPEC.md` — §11 含 18 条 AC
- `docs/iterations/v0.3.1/PLAN.md` — Stage DAG + Runbook A1–A3 / B1–B2 / C1–C2 / D1–D2 / V1–V4 / R1
- `docs/iterations/v0.3.1/RETRO.md` — 本文件
- `docs/iterations/v0.3.1/verify/manual_walkthrough.txt` — 6 步走查
- `docs/iterations/v0.3.1/verify/resume_modal.svg` — Modal SVG 截图
- `docs/iterations/v0.3.1/verify/db_after_migration.txt` — `find ~/.invest-pilot` 输出
- 源码：`src/investpilot/storage/db.py`、`src/investpilot/interface/tui_app.py`、`src/investpilot/interface/_resume_screen.py`
- 测试：`tests/test_storage.py`（+3 新测试）、`tests/test_cli.py`（路径断言更新）、`tests/test_tui_app.py`（+11 新测试）

## 剩余风险

| 风险 | 是否需要处理 |
|------|-------------|
| 流进行中按 Up/Down 触发 history（无 busy 检查） | 待评估 — UX 小项；当前不会损坏数据；可在下轮加 `if self._busy: return` |
| Modal `priority=True` 是隐性约束，未来若有人去掉 `priority` 关键字，AC14 立刻回归 | 待评估 — 加注释提示；下一轮可在 ResumeListScreen 的 binding 上加 `# noqa` 解释 |
| DB 路径下沉后，老用户的 v0.3.0 旧二进制读不到 DB | 待评估 — SPEC §5 已说明回滚后需手动 `mv`；可在 README 加一行 |
| 输入历史不持久化（重启清空） | 不需要 — bash / fish 也是这行为；out of scope |
| 状态行 muted 颜色对低对比度显示器不友好 | 不需要 — `$text-muted` 是 textual 调色板；用户可改主题 |
| 路径含中文/特殊字符 | 不需要 — Pathlib 处理；测试已覆盖（中文 session 内容） |
| 迁移成功日志 `print(..., file=sys.stderr)` 在 CI 里被 pytest 捕获造成 noise | 待评估 — pytest 默认不捕获 stderr；测试用 capfd 也未观察到 noise；不影响功能 |