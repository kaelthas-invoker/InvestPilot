# InvestPilot v0.3.0 SPEC — 对话持久化 + `/resume`

> 日期：2026-07-25
> 需求来源：用户口述 + 采访确认（5 轮澄清）+ Design Verify 反馈（14 条缺陷已关闭）

## 1. 背景

v0.2.x 期间的对话完全在内存里，`ChatSession.send()` 把 user / assistant 消息只 append 到 `self._messages: list[Message]`。退出 TUI 后历史就丢；用户多次研究同一只股票或同一段策略时要重新发上下文，体验差。

本迭代把"会话"和"消息"落到 SQLite，提供 `/resume` 命令回到任意历史会话。

## 2. 采访确认结果（Clarification Gate）

| 问题 | 用户回答 |
|------|---------|
| SQLite 路径 | `~/.invest-pilot/chat.db`（`~/.invest-pilot/` 目录是新的应用数据根） |
| 写入时机 | user 消息：发出后立即写 session 行 + user message；assistant 流：内存 buffer 定时 flush + 流结束 flush |
| `/resume` 列表范围 | 所有有 message 的 session，按 `updated_at DESC` |
| 会话管理命令范围 | 只做 `/resume`；`/new` `/delete` `/rename` 留待下轮 |
| user / assistant 区分渲染 | user 消息：加粗青色边框 + `You:` 标签；assistant 消息：橙色边框 + `Assistant:` 标签 |
| 首行预览 | 首条 user 消息第一行（遇换行截断），超长裁断 + `…` |
| age 格式 | k8s 紧凑格式：`5d` / `3h` / `12m` / `45s` |
| 元数据范围 | provider / model / system_prompt / created_at / updated_at / message_count 全存 |

## 3. 目标

- 对话持久化到 SQLite，关 TUI 后下次启动仍可恢复
- `/resume` 命令列出所有有消息的历史会话，支持上下选 + Enter 加载
- user / assistant 消息用边框颜色 + 角色标签视觉区分
- 第一行预览 + k8s age 让用户一眼定位最近会话
- 进程崩在流中段，已 flush 的部分不丢

## 4. 范围

### In scope

| 项 | 说明 |
|----|------|
| `investpilot/storage/` | 新模块：`db.py`（engine + 连接管理 + PRAGMA）、`schema.py`（DDL + 迁移 + version）、`repo.py`（SessionRepository）、`timefmt.py`（k8s age）、`models.py`（DTO） |
| `investpilot/storage/__init__.py` | 暴露 `SessionRepository`、`open_default_db`、`format_age` 等公开 API |
| `investpilot/assistant/session.py` | `ChatSession` 接收可选 `SessionRepository`；send 路径走严格写入协议；暴露 `load_session(session_id)` 把历史灌进当前 session 并覆盖 `_system_prompt` |
| `investpilot/interface/tui_app.py` | `_append_user()` / `_append_assistant()` 样式化；slash 命令 router 识别 `/resume`；`ResumeListScreen` Modal；流进行中禁止 `/resume` |
| `investpilot/interface/_resume_screen.py` | 提取 `ResumeListScreen`（ModalScreen） |
| `investpilot/cli/main.py` | `chat` 命令构造 `SessionRepository`（默认 `~/.invest-pilot/chat.db`） |
| 测试 | repo CRUD / timefmt 边界 / session-message 关联 / 写入协议 / TUI 列表渲染 / 加载历史样式一致 / 流中禁用 `/resume` |
| 文档 | `docs/iterations/v0.3.0/{SPEC,PLAN,RETRO}.md` |

### Out of scope

- `/new` `/delete` `/rename` 会话管理命令
- 全文搜索会话 / 导出 / 导入 / 跨机器同步 / 多用户 / 鉴权
- 工具调用消息（tool 角色）持久化（provider 当前未发 tool 块）
- 删除空 session 的 GC（数据库可长期保留空 session）
- assistant 行 `status` 字段在 UI 上的特殊标记（v0.3.0 一律按完成渲染）

## 5. 数据模型

### 表 `session`

```sql
CREATE TABLE session (
  id            TEXT PRIMARY KEY,            -- uuid4 hex
  provider      TEXT NOT NULL,               -- anthropic / openai
  model         TEXT NOT NULL,
  system_prompt TEXT NOT NULL,
  created_at    TEXT NOT NULL,               -- ISO8601 UTC
  updated_at    TEXT NOT NULL,
  message_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_session_updated_at ON session(updated_at DESC);
```

### 表 `message`

```sql
CREATE TABLE message (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES session(id) ON DELETE CASCADE,
  role       TEXT NOT NULL,                  -- user | assistant（system 不入表）
  content    TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'final',  -- 'final' | 'streaming'
  created_at TEXT NOT NULL,                  -- ISO8601 UTC
  seq        INTEGER NOT NULL,
  UNIQUE(session_id, seq)
);

CREATE INDEX idx_message_session_seq ON message(session_id, seq);
```

`status` 字段语义：
- `streaming`：assistant 行处于流中（已被创建但流未结束）。崩溃后此值能告诉 /resume 哪些行"未结束"，但 v0.3.0 UI 不区分（按 `final` 渲染）
- `final`：行已收尾（流正常完成 / 错误 / 空）

### 文件位置 / 权限

- 目录：`Path.home() / ".invest-pilot"`，mode 0o700（不存在则建，已存在则保留原 mode）
- DB：`~/.invest-pilot/chat.db`，mode 0o600（如已存在且权限更宽，记录 warning 但不强制收紧）
- WAL 模式：`PRAGMA journal_mode=WAL`、`synchronous=NORMAL`
- Schema 版本：`PRAGMA user_version = 1`

## 6. 写入协议（修订 — 关闭 Design Verify 缺陷 #1/#2/#3）

`SessionRepository.append_message` 是唯一写入口，封装在**单事务**中：

```python
def append_message(self, *, session_id, role, content, status="final", now=None):
    """插入一条 message 并原子地更新 session.updated_at / message_count。
    返回新行的 seq。"""
```

事务步骤（必须全部成功或全部回滚）：

```
BEGIN IMMEDIATE
  seq = SELECT COALESCE(MAX(seq), 0) + 1 FROM message WHERE session_id = ?
  INSERT INTO message(session_id, role, content, status, created_at, seq)
    VALUES(?, ?, ?, ?, ?, ?)
  UPDATE session SET updated_at = ?, message_count = message_count + 1
    WHERE id = ?
COMMIT
```

`BEGIN IMMEDIATE` 在 SQLite 中获取 RESERVED 锁，杜绝两个 writer 读到相同 `MAX(seq)`。

### 流写入协议（修订 — 关闭 N2）

```
ChatSession.send(text):
  text = text.strip()
  if not text: return
  if self._session_id is None:
    self._session_id = repo.create_session(provider, model, system_prompt, now=now)
  user_seq = repo.append_message(
    session_id=self._session_id,
    role="user", content=text, status="final", now=now,
  )
  # 创建 assistant 行占位：status='streaming', content=''
  assistant_seq = repo.append_message(
    session_id=self._session_id,
    role="assistant", content="", status="streaming", now=now,
  )

  parts, buffer, last_flush, first_chunk_seen = [], [], now(), False
  errored = False
  try:
    async for chunk in provider.stream_chat(self._messages):
      if chunk.kind == "text" and chunk.text:
        parts.append(chunk.text); buffer.append(chunk.text)
        # 关键：第一个 text chunk 立即 flush，确保崩溃时不丢首个 chunk
        if not first_chunk_seen or (now() - last_flush).total_seconds() >= 0.5:
          repo.update_message_content(self._session_id, assistant_seq, "".join(buffer))
          last_flush = now()
          first_chunk_seen = True
        yield chunk
      elif chunk.kind == "error":
        errored = True
        yield chunk
  except Exception:
    errored = True

  final_text = "".join(parts) if parts and not errored else (
    "".join(parts) if parts else "[错误：生成失败]"
  )
  repo.finalize_message(self._session_id, assistant_seq, final_text, now=now())
```

要点：
1. **崩溃恢复**：进程崩在 `streaming` 阶段 → `message` 行已存在（status=streaming + 部分 content），`/resume` 按其内容渲染（v0.3.0 UI 不区分 streaming/final）
2. **不创建"草稿"表**：复用 `message` 行 + `status` 字段
3. **唯一 assistant 行 / send**：每次 send 只产生一个 assistant 行；`status='streaming'` 表示未结束
4. **首 chunk 立即 flush + 后续 0.5s flush**：`update_message_content` 不动 seq/created_at/message_count/updated_at。首 chunk 立即写保证 AC11 测试可重现（关闭 N2）
5. **finalize = UPDATE content + status='final'**，不动 seq/created_at/message_count/updated_at（流期间这些不变；append 时已 +1）
6. **流中错误**：errored 时 final_text 仍是 buffer 内容，不强行加 "[错误：生成失败]"；仅当完全没有 part 才用占位。这与现状 `ChatSession.send` 行为保持一致

`/resume` 排序：`ORDER BY updated_at DESC, id DESC`。`id DESC` 是稳定 tie-breaker（同 `updated_at` 时按 session id 倒序）。

## 7. 加载 / 恢复

### 唯一 API：`ChatSession.load_session(session_id)`

```
ChatSession.load_session(session_id):
  metadata = repo.get_session(session_id)
  if metadata is None: raise SessionNotFound(session_id)
  self._provider = ...  # 见下
  self._system_prompt = metadata.system_prompt
  self._messages = [Message("system", metadata.system_prompt)] + [
    Message(m.role, m.content)
    for m in repo.load_messages(session_id)
  ]
  self._session_id = session_id
```

### provider / model 在恢复时的行为（关闭 Design Verify 缺陷 #5）

恢复会话时**继续使用启动时的 `provider` 和 `model`**（即 `config.yaml` 当前值），但 `system_prompt` 用 DB 中存的版本。

理由：
- provider/model 切换由用户配置文件管理，运行时切换会让用户困惑（"为什么我 resume 后请求走的是旧模型"）
- system_prompt 一旦写入 session，是该 session 的语义契约，跨配置必须保持一致

`get_session` 返回的 metadata 在 UI 上**展示**（标题栏 / `/resume` 列表），不切换实际调用。

### 流中 `/resume`（关闭 Design Verify 缺陷 #6）

流进行中（`self._busy == True`）输入 `/resume`：

- 在输入框旁显示 toast：`"助手还在生成，请稍候"`（或类似文案）
- 不切到 `ResumeListScreen`
- 输入框内容清空（与正常命令行为一致）

测试：发一条 user，模拟 provider 慢流，0.5s 内输入 `/resume`，断言仍停在原 transcript 上，没有 modal 被 push。

## 8. TUI 行为

### 输入框识别 `/resume`

```
on_input_submitted(event):
  text = event.value.strip()
  event.input.value = ""
  if is_quit_command(text): self.exit(); return
  if text == "/resume":
    if self._busy:
      self._append_system_note("助手还在生成，请稍候")
      return
    self.push_screen(ResumeListScreen(repo=self._repo))
    return
  self.run_worker(self._handle_send(text), exclusive=True)
```

### `ResumeListScreen`（`investpilot/interface/_resume_screen.py`）

- 接收 `repo: SessionRepository`
- `ListView` 行数据：`SessionListItem(session_id, preview_text, age_text)`
- `preview_text` = 首条 user 消息首行（按换行截断），按下面规则截断
- `age_text` = `format_age(now - session.updated_at)`
- 高亮当前行
- Up/Down + `j`/`k` 移动；Enter `dismiss(session_id)`；Esc `dismiss(None)`
- 空列表：单行居中"暂无历史会话，按 Esc 返回"
- 加载中：单行"加载中…"

### 选中后行为

```
on_screen_resumed(session_id):
  if session_id is None: return
  metadata = repo.get_session(session_id)
  messages = repo.load_messages(session_id)
  self._session.load_session(session_id)  # 覆盖 system_prompt, self._messages, self._session_id
  # 重渲染 transcript
  self._clear_transcript_except_logo()
  for m in messages:
    if m.role == "user": self._append_user(m.content)
    elif m.role == "assistant": self._append_assistant(m.content)
  # boot 提示
  self._append_line(f"已恢复会话 · {metadata.provider}/{metadata.model}")
  self._title_suffix = f"{metadata.provider}/{metadata.model}"
  self.title = f"InvestPilot · {self._title_suffix}"
```

> 注：Textual 中 ModalScreen 返回值通过 `on_screen_resumed`（App 钩子）或在回调注册处接 `dismiss` 结果。实现层任选其一（§13 由 Execute-C 决定具体 API），但**回调中传入的非空值必然是 `session_id: str`**。

### 样式

```
.msg-user       { border: heavy cyan;   ... }
.msg-assistant  { border: heavy orange; ... }
.msg-system     { color: $text-muted;   ... }   /* boot 提示 / 错误占位 */
```

`_append_user(text)` → mount `Static(f"You: {text}", classes="msg msg-user")`
`_append_assistant(text)` → mount `Static(f"Assistant: {text}", classes="msg msg-assistant")`
`_append_system_note(text)` → mount `Static(text, classes="msg msg-system")`

## 9. 预览截断规则（关闭 Design Verify 缺陷 #10）

输入：`first_user_message.content`

```
def first_line_preview(content: str, *, max_width: int = 60) -> str:
    line = content.split("\n", 1)[0].rstrip()  # 第一行
    # 按字符数（不是显示宽度，UI 自行处理宽字符）
    if len(line) <= max_width:
        return line
    return line[: max_width - 1] + "…"
```

| 输入 | 输出（max=60） |
|------|---------------|
| `"hi"` | `"hi"` |
| `""`（空 content） | `""` |
| `"\n下一行"` | `""`（首行为空） |
| `"a" * 60` | 60 个 a |
| `"a" * 61` | 59 个 a + `…` |
| `"第一行\n第二行"` | `"第一行"` |

边界样例进入 `tests/test_storage.py`。

## 10. 时间格式（k8s 紧凑 — 修订，关闭 Design Verify 缺陷 #11）

```python
def format_age(delta: timedelta) -> str:
    s = max(0, int(delta.total_seconds()))  # 防御未来时间
    if s < 60:    return f"{s}s"
    if s < 3600:  return f"{s // 60}m"
    if s < 86400: return f"{s // 3600}h"
    return f"{s // 86400}d"
```

真实边界（修复 SPEC/PLAN 的错误样例）：0s, 59s, 60s, 3599s, 3600s, 86399s, 86400s, -30s（未来时间 → 0s）。

## 11. 验收标准

| # | 项 | 验证方式 |
|---|----|---------|
| 1 | 首次 `chat` 自动建 `~/.invest-pilot/chat.db` | `tests/test_cli.py::test_chat_creates_db_on_first_run`：用 `tmp HOME` 注入；运行 `chat`；断言文件存在、mode 0o600 |
| 2 | 1 条 user + 1 条 assistant 后 DB 有 1 session 行 + 2 message 行 | `tests/test_session.py::test_persist_user_and_assistant_after_send`：fake provider + tmp DB |
| 3 | 退出 TUI 后重启 `/resume` 能看到上次会话 | `tests/test_session.py::test_resume_roundtrip`：建库 → 写 → 重新 open → list_sessions 包含 |
| 4 | 列表首行预览 = user 消息首行；age = k8s 紧凑；按 updated_at DESC | `tests/test_storage.py::test_list_sessions_preview_and_age` |
| 5 | 列表为空 Enter 不报错，显示"暂无历史会话" | `tests/test_tui_app.py::test_resume_screen_empty` |
| 6 | Enter 加载并按样式渲染历史 | `tests/test_tui_app.py::test_resume_load_renders_with_styles` |
| 7 | 加载后 send：provider 收到完整历史 | `tests/test_session.py::test_load_session_then_send_includes_history` |
| 8 | `format_age` 真实边界正确 | `tests/test_timefmt.py`：0/59/60/3599/3600/86399/86400/-30 |
| 9 | user 样式：heavy cyan + `You:`；assistant 样式：heavy orange + `Assistant:` | `tests/test_tui_app.py::test_message_styles`：断言 classes 与 CSS |
| 10 | 加载历史按原顺序渲染，样式与新建时一致 | `tests/test_tui_app.py::test_loaded_messages_share_styles` |
| 11 | 流中断在 0.5s 窗口：DB 中有 streaming 行；重启 `/resume` 看到 partial 文本 | `tests/test_session.py::test_streaming_message_persists_partial`：模拟 provider 在 chunk 后抛异常 |
| 12 | 流中输入 `/resume`：禁止，显示提示 | `tests/test_tui_app.py::test_resume_blocked_during_stream` |
| 13 | `uv run pytest` 全绿；`uv run ruff check .` 通过 | CI / 主 Agent 跑 |

## 12. 风险与处理

| 风险 | 处理 |
|------|------|
| 用户已有 `~/.invest-pilot/` 但不是我们的目录（同名文件） | 启动时 `Path.home()/.invest-pilot`；若同名是文件，给出 ConfigError 退出，不覆盖 |
| DB 锁阻塞 | WAL 模式 + 流用独立 short-lived 连接（每次 append_message 内部 new connection） |
| 加载会话后 system_prompt 与原 session 不一致 | `load_session` 强制覆盖 `_system_prompt` |
| 时钟跳变导致 age 显示未来值 | `format_age` 内部 `max(0, …)` |
| 测试污染用户家目录 | `SessionRepository` 接收 `path`；测试用 `tmp_path` |
| 进程崩在 streaming 阶段 | assistant 行已落表，`/resume` 看到的是 last-flushed content（关闭缺陷 #1） |
| 回滚后 DB 文件遗留 | 代码回滚即可；DB schema 是 user_version=1，向后兼容旧代码（v0.2.x 不知道 DB，忽略即可）；新代码读到未知 user_version 不报错 |
| repo `message_count` 与 `MAX(seq)` 漂移 | 唯一事务约束；事务失败整体回滚 |

## 13. Schema 与接口契约（冻结 — Execute 必须基于此实现）

### `open_default_db()` 与 `SessionRepository` 的契约边界（关闭 N5）

- `open_default_db() -> Path`：返回默认 DB 路径（已确保 `~/.invest-pilot/` 目录存在 + 权限），**不**打开连接
- `SessionRepository(db_path: Path)`：内部按方法短连接（`append_message` 在事务内持锁；读方法用新连接），**不**接收 `sqlite3.Connection`

调用方写法：`SessionRepository(open_default_db())`。

### `SessionRepository` 接口

```python
class SessionRepository:
    def __init__(self, db_path: Path) -> None: ...

    # 元数据
    def create_session(
        self, *, provider: str, model: str, system_prompt: str,
        now: datetime | None = None,
    ) -> str: ...   # 返回 session_id

    def get_session(self, session_id: str) -> SessionMetadata | None: ...

    def list_sessions(self) -> list[SessionListItem]: ...

    # 消息
    def append_message(
        self, *, session_id: str, role: str, content: str,
        status: str = "final", now: datetime | None = None,
    ) -> int: ...   # 返回 seq

    def load_messages(self, session_id: str) -> list[MessageRecord]: ...

    def update_message_content(
        self, session_id: str, seq: int, content: str,
    ) -> None: ...

    def finalize_message(
        self, session_id: str, seq: int, content: str,
        *, now: datetime | None = None,
    ) -> None: ...
```

### DTO

```python
@dataclass(frozen=True)
class SessionMetadata:
    id: str
    provider: str
    model: str
    system_prompt: str
    created_at: datetime
    updated_at: datetime
    message_count: int

@dataclass(frozen=True)
class SessionListItem:
    id: str
    preview: str
    updated_at: datetime
    message_count: int

@dataclass(frozen=True)
class MessageRecord:
    role: str
    content: str
    status: str
    created_at: datetime
    seq: int
```

异常：

```python
class SessionNotFound(LookupError): ...
class RepoError(RuntimeError): ...
```

### `format_age(delta: timedelta) -> str`（见 §10）

### `first_line_preview(content: str, *, max_width: int = 60) -> str`（见 §9）

`investpilot.storage` 包内全部 import 不依赖 `investpilot.assistant` / `investpilot.interface`，避免循环依赖。