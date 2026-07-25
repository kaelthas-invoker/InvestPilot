# InvestPilot v0.3.1 PLAN — 输入历史 / 状态行 / DB 路径下沉

> 日期：2026-07-25
> 对应 SPEC：`./SPEC.md`

## 1. Stage DAG

```
[Research] (已合 — 复用 v0.3.0 探索结果)
   │
   ↓
[Design]  SPEC + PLAN（本文件）
   │
   ↓
[Verify(Design)]  plan-reviewer
   │
   ↓
[Execute]  按依赖：A 与 C/D 并行；B 单做（不动 storage）
   │
   ├─ A.DB 路径 (backend-developer → code-reviewer)   改 storage/db.py + cli 路径断言
   ├─ B.状态行 (frontend-developer → code-reviewer)   tui_app.py 加 Static + binding
   ├─ C.历史  (frontend-developer → code-reviewer)   tui_app.py 加 Up/Down binding
   └─ D.收尾  (frontend-developer → code-reviewer)   移除 hint + 加 resume 导航测试
   │
   ↓
[Verify(Delivery)]  e2e-tester (V3) + reality-checker (V4)
   │
   ↓
[Reflection]  主 Agent 写 RETRO.md
```

注：A 不依赖 B/C/D；B/C/D 互相独立。

## 2. Runbook Todo

### Execute-A · DB 路径下沉 + 迁移

- **A1** — `src/investpilot/storage/db.py` 改 `open_default_db()`
  - 做什么：返回路径改为 `~/.invest-pilot/storage/sqlite/chat.db`；建两级目录（mode 0o700）；遍历 `chat.db` / `chat.db-wal` / `chat.db-shm` 三个文件做 `shutil.move`；迁移后 `assert not old.exists()`，否则 `RepoError`；迁移成功 stderr 一行 log
  - 目标：测试 `test_open_default_db_new_path`、`test_old_db_path_migrates`、`test_migration_includes_wal_shm` 全过
  - 边界：不删老目录；不处理用户自己放在 `~/.invest-pilot/` 下的其他 .db 文件

- **A2** — `tests/test_storage.py` 新增 / 调整
  - 做什么：新增 `test_open_default_db_new_path`（断言路径末两段是 `storage/sqlite/chat.db`，目录 mode 0o700）；`test_old_db_path_migrates`（预置老 DB 文件，调用 open_default_db，断言老 DB 不存在，新路径存在）；`test_migration_includes_wal_shm`（预置 chat.db + chat.db-wal + chat.db-shm，调用 open_default_db，断言三者都迁移到新路径，老路径三个都不存在）
  - 目标：覆盖 AC1 / AC2 / AC3 / AC18
  - 边界：不测试 cross-FS copy+delete 失败（属于 OSError 模拟，不在自动化覆盖范围）

- **A3** — `tests/test_cli.py` 改 AC1
  - 做什么：`test_chat_creates_db_on_first_run` 断言路径改为 `tmp_path / ".invest-pilot" / "storage" / "sqlite" / "chat.db"`
  - 目标：测试通过（覆盖 AC17）
  - 边界：不重构其他测试

### Execute-B · 状态行

- **B1** — `src/investpilot/interface/tui_app.py` 改
  - 做什么：`__init__` 新增 `self._provider_name` 与 `self._model` 参数（默认从 `title_suffix` 解析），与 `_title_suffix` 解耦；compose 加 `Static(id="status-line")` 在 Input 之后；CSS 加 `#status-line { height: 1; color: $text-muted; background: $boost; padding: 0 1; }`；`on_mount` 调用 `_refresh_status_line()`；新增 `_refresh_status_line(self) -> None`：拼接 `f"{self._provider_name} / {self._model}"`（带空格）更新到 `#status-line`；`_on_resume_dismissed` 在原更新 `self._title_suffix`/`self.title` 之后调 `_refresh_status_line(metadata)`（用被恢复 session 的 provider/model）
  - 目标：`test_status_line_shows_provider_model`、`test_status_line_updates_after_resume` 通过
  - 边界：不变 mascot / thinking；header 仍由 v0.3.0 的 `_title_suffix` 路径管

- **B2** — `tests/test_tui_app.py` 新增
  - 做什么：两个状态行测试
  - 目标：覆盖 AC12 / AC13
  - 边界：不引入新依赖

### Execute-C · 输入历史（bash 风格）

- **C1** — `src/investpilot/interface/tui_app.py` 改
  - 做什么：`__init__` 加 `self._history: list[str] = []` 与 `self._history_index: int | None = None`；`BINDINGS` 加 `Binding("up", "history_prev", ...)`、`Binding("down", "history_next", ...)`；新增 `action_history_prev()` 与 `action_history_next()` 实现 SPEC §6 表；`_handle_send` 在真正 send 后调 `self._record_history(text)`（空文本不入；斜杠命令不入）；`action_history_prev` 把 `input.value` 设为历史条目并 cursor 到末尾；`action_history_next` 同理；末尾清空且 `_history_index = None`；`_on_resume_dismissed` 把 `self._history = []`、`self._history_index = None`（避免与加载对话混淆）
  - 目标：测试覆盖 AC4–11
  - 边界：不持久化历史；不引入模糊搜索

- **C2** — `tests/test_tui_app.py` 新增
  - 做什么：`test_history_up_recalls_previous`、`test_history_down_advances_and_clears_at_end`、`test_history_capped_at_100`、`test_slash_commands_not_in_history`、`test_empty_text_not_in_history`、`test_history_mid_edit_keeps_index`、`test_resume_clears_history`（共 7 个）
  - 目标：覆盖 bash 风格完整流 + 边界
  - 边界：测试用 `_FakeSession`（无 repo）；不依赖真实时间

### Execute-D · `/resume` 验证 + 移除冗余

- **D1** — `src/investpilot/interface/tui_app.py` 收尾
  - 做什么：`_on_resume_dismissed` 删除 `self._append_line(f"已恢复会话 · ...")` 那行；保留 `self._title_suffix = ...` / `self.title = ...` 更新（v0.3.0 既有行为，header 显示被恢复 session 的 provider/model）；之后调 `_refresh_status_line(metadata)`
  - 目标：AC15 通过；旧测试不破坏
  - 边界：不动 `_handle_send` 流逻辑

- **D2** — `tests/test_tui_app.py` 新增 + 调整
  - 做什么：`test_resume_modal_arrow_keys_navigate_and_enter_selects`（3 条会话，up/down/enter 走通）；`test_no_restored_session_hint_after_resume`（断言 transcript 不含"已恢复会话"）
  - 目标：覆盖 AC14 / AC15
  - 边界：复用现有 _seed_session helper

### Verify(Delivery)

- **V1** — `uv run pytest`（主 Agent 跑）
- **V2** — `uv run ruff check .`（主 Agent 跑）
- **V3** — e2e-tester 走查：手工 验证 DB 在新位置 + 输入历史 + 状态行 + `/resume` 导航 + 无 hint
- **V4** — reality-checker 复核 AC1–14 全覆盖

### Reflection

- **R1** — `docs/iterations/v0.3.1/RETRO.md`

## 3. 文件边界

| 文件 | 归属 | 改动 |
|------|------|------|
| `src/investpilot/storage/db.py` | A | modify |
| `tests/test_storage.py` | A | modify（追加） |
| `tests/test_cli.py` | A | modify（路径断言） |
| `src/investpilot/interface/tui_app.py` | B/C/D | modify |
| `tests/test_tui_app.py` | B/C/D | modify（追加） |
| `docs/iterations/v0.3.1/{SPEC,PLAN,RETRO}.md` | Design + Reflection | new |

## 4. 验证路径

### 单元（自动）

- `tests/test_storage.py` — 路径、目录权限、迁移
- `tests/test_tui_app.py` — 历史（bash 风格 4 个测试）、状态行（2 个）、resume 导航（1 个）、无 hint（1 个）
- `tests/test_cli.py` — AC1 路径断言更新

### 手工

- `rm -rf ~/.invest-pilot`；`invest-pilot chat`；发 3 条不同消息；按 Up 几次；按 Down；按 Enter 提交；观察状态行
- `/resume`；按 Down 两次；按 Enter；观察 transcript 无"已恢复会话"字样

### 静态

- `uv run pytest -q`
- `uv run ruff check .`

## 5. 回滚 / 缓解

- **代码回滚**：单文件 revert 即可
- **DB 回滚**：v0.3.1 后老路径已被迁移；回滚代码到 v0.3.0 后 `open_default_db` 仍指向新路径（v0.3.0 旧代码逻辑会找不到 DB）。这是预期行为：DB 已经搬到新位置，新代码继续用即可。回滚到 v0.3.0 代码的用户需要手动 `mv ~/.invest-pilot/storage/sqlite/chat.db ~/.invest-pilot/chat.db`（含 WAL/SHM 边车）。README 标注此步骤
- **历史不持久化**：重启清空，符合 bash 行为

## 6. 与既有约束的对齐

| 既有约束 | 本迭代影响 |
|---------|-----------|
| 不做无重复证据的抽象 | 历史、状态行、迁移都是单文件改动 |
| 不为"以后可能"扩展架构 | 历史模糊搜索 / 持久化 / 多行编辑都不做 |
| 迭代文档按需放 `docs/iterations/<version>/` | SPEC / PLAN / RETRO 三件齐 |
| 每轮一个可验证闭环 | AC 14 条；自动 + 手工 |
| 不跨角色边界 | A 由 `backend-developer`；B/C/D 由 `frontend-developer` |