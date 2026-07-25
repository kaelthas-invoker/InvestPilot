# InvestPilot v0.3.0 PLAN — 对话持久化 + `/resume`

> 日期：2026-07-25
> 对应 SPEC：`./SPEC.md`

## 1. Stage DAG

```
[Research] (已合)
   │
   ↓
[Design]  SPEC + PLAN（已含本轮修订）
   │
   ↓
[Verify(Design)]  plan-reviewer（FAIL → 已修订 → 待重跑）
   │
   ↓
[Freeze Contract]  SPEC §13 接口 / DTO / 异常 / 函数签名冻结
   │
   ↓
[Execute]  按依赖串行
   │
   ├─ A.storage (backend-developer → code-reviewer)
   ├─ B.session (backend-developer → code-reviewer)         依赖 A
   ├─ C.tui     (frontend-developer → code-reviewer)        依赖 A 契约（不依赖 A 实现细节）
   └─ D.cli     (backend-developer → code-reviewer)         依赖 A
   │
   ↓
[Verify(Delivery)]  e2e-tester 跑单测 + 手工 TUI 走查
   │
   ↓
[Verify(Delivery → Reflection)]  reality-checker 复核 AC 1–13 全数覆盖
   │
   ↓
[Reflection]  主 Agent 写 RETRO.md
```

修订点（关闭 Design Verify 缺陷）：

- 删除"Execute 四步并行"措辞；改为"按依赖串行"。A 完成 → B/C/D 并行（共享契约）
- 插入 `Freeze Contract` 节点（C/D 在 A 完成前即可基于 §13 契约并行启动）
- 各 Execute 都配 `code-reviewer` 单独 verify
- `e2e-tester` 跑单测 + 手工 TUI 走查；`reality-checker` 复核 AC 覆盖

## 2. Runbook Todo

> 每条 Todo 包含：**做什么**（动作）、**目标**（可观察产物）、**边界**（不做什么）。Runbook 契约见 `~/.claude/.contract/runbook.md`。

### Execute-A · storage 层

- **A1** — `investpilot/storage/__init__.py`
  - 做什么：暴露 `SessionRepository`、`SessionMetadata`、`SessionListItem`、`MessageRecord`、`SessionNotFound`、`RepoError`、`format_age`、`first_line_preview`、`open_default_db`
  - 目标：`from investpilot.storage import …` 全部可达；运行 `python -c "import investpilot.storage as s; print(s.SessionRepository)"` 无错
  - 边界：不导出 helper / 不导出内部 DTO

- **A2** — `investpilot/storage/models.py`
  - 做什么：定义 SPEC §13 的 3 个 dataclass DTO + 2 个异常
  - 目标：`dataclass(frozen=True)` 全部存在，字段类型与 SPEC 一致
  - 边界：不放业务方法；不放 SQLite 类型

- **A3** — `investpilot/storage/db.py`
  - 做什么：`open_db(path)` 返回 `sqlite3.Connection`，设置 `PRAGMA journal_mode=WAL`、`synchronous=NORMAL`、`foreign_keys=ON`；`open_default_db()` 解析 `~/.invest-pilot/chat.db`、建目录、设权限
  - 目标：用 `tmp_path` 注入 home；调用后 DB 文件存在，权限 0o600
  - 边界：不写业务逻辑；不暴露 connection pool

- **A4** — `investpilot/storage/schema.py`
  - 做什么：`apply_schema(conn)` 读 `PRAGMA user_version`；为 0 时执行 SPEC §5 DDL 并写 user_version=1；非 0 不动
  - 目标：幂等（连续两次调用 user_version 仍为 1）
  - 边界：不提供迁移（user_version=1 即 baseline）

- **A5** — `investpilot/storage/repo.py`
  - 做什么：实现 `SessionRepository` 全部 7 个方法（SPEC §13）；`append_message` / `create_session` 走 `BEGIN IMMEDIATE` 单事务
  - 目标：单测覆盖全部公开方法 + 异常路径
  - 边界：不实现流协议（buffer/flush 是 B 的事）；不引入 ORM

- **A6** — `investpilot/storage/timefmt.py`
  - 做什么：`format_age(td)` 实现 SPEC §10
  - 目标：`tests/test_timefmt.py` 边界 0/59/60/3599/3600/86399/86400/-30 全过
  - 边界：不依赖时区；不接受 `None`

- **A7** — `investpilot/storage/preview.py`
  - 做什么：`first_line_preview(content, max_width=60)` 实现 SPEC §9
  - 目标：`tests/test_storage.py::test_first_line_preview` 覆盖空 / 单行 / 换行 / 超长 / 边界
  - 边界：按 Unicode 字符数（不是 display width）；非负 max_width

- **A8** — `tests/test_storage.py`
  - 做什么：覆盖 schema 幂等、`append_message` 原子性、`list_sessions` 排序、`first_line_preview` 边界
  - 目标：`uv run pytest tests/test_storage.py` 全过
  - 边界：不测流协议

### Execute-B · ChatSession 持久化

- **B1** — `investpilot/assistant/session.py`
  - 做什么：`ChatSession.__init__(provider, system_prompt, repo=None)`；`send` 按 SPEC §6 协议写 user / assistant 流；新增 `load_session(session_id)`；注入 `now` 便于测试
  - 目标：`tests/test_session.py` 全部用例（含原 3 个 + 新增 4 个）全过
  - 边界：不动 provider 接口；不动 `Message` / `StreamChunk` dataclass

- **B2** — `tests/test_session.py`（追加 4 个）
  - 做什么：`test_persist_user_and_assistant_after_send`、`test_streaming_message_persists_partial`、`test_load_session_then_send_includes_history`、`test_load_session_restores_system_prompt`
  - 目标：每条用 `tmp_path` + fake provider；跑完新测试 + 原测试
  - 边界：不依赖 textual；不依赖真实 SQLite 路径

### Execute-C · TUI

- **C1** — `investpilot/interface/tui_app.py`（modify）
  - 做什么：CSS 加 `.msg-user` / `.msg-assistant` / `.msg-system`；`on_input_submitted` 加 `/resume` 路由；新增 `_append_user` / `_append_assistant` / `_append_system_note` / `_clear_transcript_except_logo`；`push_screen(ResumeListScreen(repo=self._repo))`；`on_screen_resumed` 加载；流中 `/resume` 走 system note
  - 目标：`tests/test_tui_app.py` 全部用例（含原 3 个 + 新增 4 个）全过
  - 边界：保持现有 mascot / 大 logo 行为；不改 `_handle_send` 流逻辑（由 B 提供）

- **C2** — `investpilot/interface/_resume_screen.py`（new）
  - 做什么：`ResumeListScreen(ModalScreen)`：列表项 = `SessionListItem`；高亮 + 上下移动；Enter `dismiss(session_id)`；Esc `dismiss(None)`；空列表显示提示
  - 目标：`tests/test_tui_app.py::test_resume_*` 全过
  - 边界：不调用 `provider`；不触发 send；只展示 repo 数据

- **C3** — `tests/test_tui_app.py`（追加 4 个）
  - 做什么：`test_resume_screen_empty`、`test_resume_load_renders_with_styles`、`test_message_styles`、`test_loaded_messages_share_styles`、`test_resume_blocked_during_stream`
  - 目标：每条用 textual `app.run_test()` + tmp DB
  - 边界：mock provider；不依赖真实网络

### Execute-D · CLI

- **D1** — `investpilot/cli/main.py`（modify）
  - 做什么：`chat` 命令加载 config 后构造 `SessionRepository(open_default_db())`，传给 `ChatSession` 和 `InvestPilotApp`；路径冲突 / 权限错误时 `typer.secho(fg=RED)` + `Exit(code=1)`
  - 目标：`tests/test_cli.py::test_chat_creates_db_on_first_run` 全过
  - 边界：不引入新命令；不改 `status` 命令

> 契约一致性：`open_default_db()` 返回 `Path`；`SessionRepository` 接收 `Path`（不接收 `Connection`）。详见 SPEC §13。

### Verify(Delivery)

- **V1** — `uv run pytest`（`backend-developer` 跑）
  - 目标：全绿
- **V2** — `uv run ruff check .`（`backend-developer` 跑）
  - 目标：通过
- **V3** — 手工 TUI 走查（`e2e-tester` 跑）
  - 步骤：`invest-pilot chat` → 发 2 条 → `/quit` → `invest-pilot chat` → `/resume` → 看到列表 → Enter 加载 → 看到历史样式化
  - 目标：截图保存到 `docs/iterations/v0.3.0/verify/`
- **V4** — AC 1–13 覆盖矩阵复核（`reality-checker` 跑）
  - 目标：每条 AC 都能指向一个 test 或一个手工步骤；缺则回 Execute 补

### Reflection

- **R1** — `docs/iterations/v0.3.0/RETRO.md`
  - 做什么：事实 / 偏差 / 根因 / 已应用改进 / 剩余风险；对照 SPEC §11 AC 表
  - 目标：可被未来 reader 直接当历史依据
  - 边界：不引入新需求；不开新一轮任务

## 3. 文件边界（修订 — 与 DAG 串行顺序一致）

| 文件 | 归属 | 改动 |
|------|------|------|
| `investpilot/storage/__init__.py` | A | new |
| `investpilot/storage/models.py` | A | new |
| `investpilot/storage/db.py` | A | new |
| `investpilot/storage/schema.py` | A | new |
| `investpilot/storage/repo.py` | A | new |
| `investpilot/storage/timefmt.py` | A | new |
| `investpilot/storage/preview.py` | A | new |
| `tests/test_storage.py` | A | new |
| `tests/test_timefmt.py` | A | new |
| `investpilot/assistant/session.py` | B | modify |
| `tests/test_session.py` | B | modify（追加） |
| `investpilot/interface/tui_app.py` | C | modify |
| `investpilot/interface/_resume_screen.py` | C | new |
| `tests/test_tui_app.py` | C | modify（追加） |
| `investpilot/cli/main.py` | D | modify |
| `tests/test_cli.py` | D | modify（追加 AC1） |
| `docs/iterations/v0.3.0/SPEC.md` | Design | modify（已含本轮修订） |
| `docs/iterations/v0.3.0/PLAN.md` | Design | modify（本文件） |
| `docs/iterations/v0.3.0/RETRO.md` | Reflection | new |

## 4. 验证路径

### 单元（自动）

- `tests/test_storage.py` — schema 幂等、CRUD、原子性（并发模拟用 `Thread` 验证 seq 不重复）、`list_sessions` 排序、preview
- `tests/test_timefmt.py` — 真实边界 0/59/60/3599/3600/86399/86400/-30
- `tests/test_session.py` — 原 3 个 + 新增 4 个持久化用例
- `tests/test_tui_app.py` — 原 3 个 + 新增 5 个（含流中 `/resume` 禁用）
- `tests/test_cli.py` — AC1：`chat` 在 `tmp HOME` 下创建 DB + 权限

### 集成 / 手工（`e2e-tester`）

1. 清掉 `~/.invest-pilot/chat.db`（如有）；跑 `invest-pilot chat`
2. 输入"测试 1"，等回复；输入"测试 2"，等回复
3. `/quit`
4. 再 `invest-pilot chat` → `/resume` → 看到 2 行（"测试 1" + "测试 2" 各自的预览 + age）
5. Enter 加载第一行 → transcript 出现 user / assistant 样式化
6. 截图存 `docs/iterations/v0.3.0/verify/`

### 静态

- `uv run pytest` — 必跑
- `uv run ruff check .` — 必跑

## 5. 回滚 / 缓解（修订 — 关闭 Design Verify 缺陷 #13）

- **代码回滚**：单文件 revert 即可（无运行时强 schema migration）
- **DB 回滚**：DB 是用户本地数据，**不随代码回滚**。v0.2.x 不知 DB 存在；v0.3.x 读到旧 user_version（不存在 → 0）→ 应用 schema = 安全
- **DB 文件**：不进仓（`.gitignore` 已包含 `~/.invest-pilot/` 兼容模式：项目根目录下若有 `.invest-pilot/` 也忽略；用 `*` 通配)
- **权限回滚**：DB 文件 mode 0o600 保留；用户用 shell 自行 chmod

## 6. 与既有约束的对齐

| 既有约束 | 本迭代影响 |
|---------|-----------|
| 不做无重复证据的抽象 | `SessionRepository` 只暴露 SPEC §13 列出的 7 个方法，不预扩展 |
| 不为"以后可能"扩展架构 | `/new` `/delete` `/rename` 不做；tool role 不持久化；status 字段不在 UI 区分 |
| 迭代文档按需放 `docs/iterations/<version>/` | SPEC / PLAN / RETRO 三件齐 |
| 每轮一个可验证闭环 | 单测 + 手工 TUI + AC 矩阵 |
| 不跨角色边界 | Execute-A/B/D 由 `backend-developer` 分担；C 由 `frontend-developer`；verify 分别由 `code-reviewer` / `e2e-tester` / `reality-checker` |