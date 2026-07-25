# InvestPilot v0.3.1 SPEC — 输入历史 / 状态行 / DB 路径下沉

> 日期：2026-07-25
> 需求来源：用户口述 + 采访确认（3 轮澄清）
> 基础：v0.3.0 已合并（chat 持久化 + `/resume`）

## 1. 背景

v0.3.0 解决了"对话能否被恢复"。v0.3.1 处理三类反复出现的体验问题：

1. **重复输入**：同一段 prompt 要重发时，得重新打字或翻聊天记录
2. **看不清当前模型**：模型名只在 header / `/resume` 标题里，且 `/resume` 后还会被改写
3. **DB 路径扁平**：旧路径 `~/.invest-pilot/chat.db` 与未来的"项目本地状态 / 用户配置"在同层，不利于将来按子系统分类

外加两个 v0.3.0 收尾：

4. **"已恢复会话"提示冗余**：选中 session 后用户已经看到 transcript 内容，再贴一行 hint 反而打断节奏
5. **`/resume` 列表上下键导航需要被验证**：v0.3.0 实现了 ListView，理论上原生支持 Up/Down/Enter；本迭代补一条回归测试锁住

## 2. 采访确认结果（Clarification Gate）

| 问题 | 用户回答 |
|------|---------|
| 上下箭头回顾历史输入的语义 | bash 风格：Up 替换输入为前一条；Down 往后翻；到底清空。中途编辑不重置历史指针 |
| status-line 内容 | `provider / model`（如 `anthropic / MiniMax-M3`） |
| DB 路径 | `~/.invest-pilot/storage/sqlite/chat.db`（最终修正版，`storage/sqlite/` 是新的应用数据子目录） |

## 3. 目标

- 输入框支持 bash 风格历史回顾（Up / Down）
- 模型名以 `provider / model` 形式固定显示在输入框下方
- `/resume` Modal 的上下箭头 + Enter 选中被测试覆盖
- 加载历史后不再追加"已恢复会话"提示
- DB 文件下沉到 `~/.invest-pilot/storage/sqlite/chat.db`，老路径自动迁移一次

## 4. 范围

### In scope

| 项 | 说明 |
|----|------|
| `investpilot/storage/db.py` | `open_default_db()` 返回 `~/.invest-pilot/storage/sqlite/chat.db`；自动建 `~/.invest-pilot/` 与 `~/.invest-pilot/storage/sqlite/` 两个目录；目录权限 0o700；DB 文件 0o600 |
| 老路径迁移 | 启动时若 `~/.invest-pilot/chat.db` 存在而新路径不存在，把主 DB + WAL/SHM 边车 rename 到新位置；迁移后显式断言旧文件已不在；失败时 RepoError |
| `investpilot/interface/tui_app.py` | Input 绑定 Up/Down 回顾历史；新增 Static 状态行显示 `provider / model`（带空格）；`/resume` 加载后更新状态行；移除"已恢复会话"系统提示；`/resume` 加载历史后清空 `self._history` |
| `tests/test_tui_app.py` | 新增：bash 风格历史（含末尾清空 / 中途编辑不重置指针 / 空文本不入 / 斜杠命令不入 / 加载后清空）；状态行存在且 `/resume` 后更新；resume Modal Up/Down/Enter；加载后不出现"已恢复会话" |
| `tests/test_storage.py` | 新增：open_default_db 返回的路径是 `storage/sqlite/chat.db`；目录创建与权限；老路径迁移；迁移包含 WAL/SHM；迁移残留检测 |
| `tests/test_cli.py` | 更新：AC1 的 chat.db 路径断言改为新路径 |
| 文档 | `docs/iterations/v0.3.1/{SPEC,PLAN,RETRO}.md` |

### Out of scope

- 历史持久化（重启后历史还在）
- 历史模糊搜索（Ctrl-R）
- 多行输入编辑
- 状态行的复制 / 点击交互
- 路径里加日期 / 项目名以隔离多个 repo
- **孤儿 WAL/SHM 清理**：迁移时搬走老 DB 边的 WAL/SHM 是一部分；若用户自己手动在 `~/.invest-pilot/` 下放其他 `.db-wal` / `.db-shm` 文件，不主动清

## 5. DB 路径与迁移（关闭细节）

### 路径

```
~/.invest-pilot/                     0o700  存在则保留原 mode
~/.invest-pilot/storage/             0o700  不存在则建
~/.invest-pilot/storage/sqlite/      0o700  不存在则建
~/.invest-pilot/storage/sqlite/chat.db  0o600
```

### 迁移规则（一次性）

`open_default_db()` 在返回新路径之前：

```
new = ~/.invest-pilot/storage/sqlite/chat.db
old = ~/.invest-pilot/chat.db
if new does not exist AND old exists AND old is a regular file:
    try:
        shutil.move(str(old), str(new))
    except OSError as e:
        raise RepoError(f"无法把旧 DB {old} 迁移到 {new}: {e}; 请手动处理后重试")
```

迁移后老 `~/.invest-pilot/chat.db` 不再存在；用户 `~/.invest-pilot/` 目录保留（里面有 storage/ 子目录）。

迁移**只迁移主 DB 文件与 WAL/SHM 边车**：v0.3.0 的 `db.py` 设置了 `PRAGMA journal_mode=WAL`，每次打开连接都会写 `.db-wal` 与 `.db-shm`（即使正常关闭也可能残留）。迁移时同时搬走这三个文件：

```python
for src_name in ("chat.db", "chat.db-wal", "chat.db-shm"):
    src = old_dir / src_name
    if src.exists():
        target = new_dir / src_name
        if target.exists():
            raise RepoError(f"目标已存在 {target}; 无法覆盖")
        try:
            shutil.move(str(src), str(target))
        except OSError as e:
            raise RepoError(f"迁移 {src} 失败: {e}; 请手动处理后重试")
```

迁移后用 `assert not old.exists()` 显式核对：若旧文件仍存在（跨 FS copy+delete 失败），抛 `RepoError`。

迁移日志：迁移成功时用 stderr 提示一行 `已迁移 v0.3.0 历史库 {old} → {new}`，便于用户感知。CLI 不展示（不影响 TUI）；测试时可注入 logger 或 stdout/stderr 捕获。

## 6. 输入历史（bash 风格）

### 数据结构

`InvestPilotApp.__init__` 新增：

```python
self._history: list[str] = []              # 仅 user 消息（不含 /quit / /resume 等斜杠命令）
self._history_index: int | None = None     # None 表示"未在历史回看中"
```

### 行为

| 触发 | 行为 |
|------|------|
| `_handle_send` 真正发送 user 文本 | `self._history.append(text)`；`self._history_index = None` |
| 用户按 Up | 若 `self._history_index is None`：`index = len(history) - 1`；否则 `index = max(0, index - 1)`。设置 `input.value = history[index]`，光标移到末尾；`self._history_index = index` |
| 用户按 Down | 若 `self._history_index is None`：忽略（不在回看）。否则：`index = index + 1`；若 `index >= len(history)`：`input.value = ""`；`self._history_index = None`；否则 `input.value = history[index]`；`self._history_index = index` |
| 用户在回看中**手动编辑** input.value | 不重置 `_history_index`（bash 风格：未提交前用户可继续修改，提交时仍然写入新条目而非覆写历史） |
| 空文本 submit | 不入历史 |
| `/quit` `/exit` `/resume` 等斜杠命令 | 不入历史 |

### 边界

- 历史容量：保留最近 100 条（`self._history = self._history[-100:]` 在 append 后）
- 重复条目：保留（bash 不去重）
- `/resume` 加载历史后：`self._history = []`（从零开始，避免混淆"加载的对话"和"本次会话输入"）

## 7. 状态行

### DOM 结构

```
#input-dock (Container, dock: bottom)
  Static #mascot        (常驻 mascot)
  Static #thinking       (流中提示)
  Input #chat-input
  Static #status-line    (新) — 显示 'provider / model'
```

CSS：

```css
#status-line {
    height: 1;
    color: $text-muted;
    background: $boost;
    padding: 0 1;
}
```

### 行为

| 触发 | 状态行内容 |
|------|-----------|
| 启动 | `f"{self._provider_name} / {self._model}"`（来自 run_tui 传入） |
| `/resume` 选中 session | `f"{metadata.provider} / {metadata.model}"`（覆盖之前的 startup 模型） |
| 状态行更新调用 | `self.query_one("#status-line", Static).update(text)` |

注：v0.3.1 状态行使用 `provider / model`（带空格），与 v0.3.0 header 用的 `provider/model`（不带空格）刻意不同。Status-line 是 UI 信息条，header 是 window 标题。两者格式独立。

**Header 与 Status-line 的状态来源（消除 §7/§8 矛盾）**：

- **Header (`self.title`)**：v0.3.0 行为不变。`_on_resume_dismissed` **更新** `self._title_suffix = f"{provider}/{model}"` 与 `self.title`，反映被恢复 session 的 provider/model
- **Status-line (`#status-line`)**：v0.3.1 新增。`_refresh_status_line()` 直接读 `_provider_name` / `_model`（`__init__` 注入），不依赖 `_title_suffix`
- 两条互不影响；以后若要切换"header 保留 startup / status-line 跟随当前"也可以独立改

`__init__` 新增：

```python
def __init__(self, session, *, title_suffix="", repo=None, provider_name=None, model=None):
    ...
    self._provider_name = provider_name or (title_suffix.split("/", 1)[0] if title_suffix else "")
    self._model = model or (title_suffix.split("/", 1)[1] if "/" in title_suffix else title_suffix)
    ...
```

## 8. `/resume` Modal 导航（验证 + 移除冗余）

### 验证

现有 `ResumeListScreen` 用 `ListView`；ListView 原生处理：

- `up` / `down`：移动选择
- `enter`：触发 `ListView.Selected` → `dismiss(item_id)`

新增回归测试 `test_resume_modal_arrow_keys_navigate_and_enter_selects`：

1. 预置 3 条会话
2. 触发 `/resume` 进入 Modal
3. 按 `down` 两次，`ListView.index == 2`
4. 按 `up` 一次，`ListView.index == 1`
5. 按 `enter`，断言 callback 被调用，session 被加载

### 移除

`_on_resume_dismissed` 删除：

```python
self._append_line(f"已恢复会话 · {metadata.provider}/{metadata.model}")
```

保留 `self._title_suffix = ...` 与 `self.title = ...` 更新（v0.3.0 既有行为，header 显示被恢复 session 的 provider/model）；状态行由 `_refresh_status_line()` 独立管理，调用 `self._refresh_status_line()` 一次性更新到被恢复 session 的 `provider / model`。

**`self._history` 在 `/resume` 之后清零**（避免与加载对话混淆）。

## 9. 验收标准

| # | 项 | 验证方式 |
|---|----|---------|
| 1 | DB 文件位于 `~/.invest-pilot/storage/sqlite/chat.db` | `tests/test_storage.py::test_open_default_db_new_path` |
| 2 | 启动自动建 `~/.invest-pilot/storage/sqlite/` 目录（mode 0o700） | 同上 |
| 3 | 老路径 `~/.invest-pilot/chat.db` 自动迁移到新路径 | `tests/test_storage.py::test_old_db_path_migrates` |
| 4 | 输入 Up：input.value 变为前一条历史 | `tests/test_tui_app.py::test_history_up_recalls_previous` |
| 5 | 多次 Up 翻到第 1 条后停住 | 同上 |
| 6 | Down 在历史中往前；到末尾清空 | `tests/test_tui_app.py::test_history_down_advances_and_clears_at_end` |
| 7 | 历史容量 100 | `tests/test_tui_app.py::test_history_capped_at_100` |
| 8 | 斜杠命令不入历史 | `tests/test_tui_app.py::test_slash_commands_not_in_history` |
| 9 | 空文本不入历史 | `tests/test_tui_app.py::test_empty_text_not_in_history` |
| 10 | 历史回看中手动编辑不重置 `_history_index` | `tests/test_tui_app.py::test_history_mid_edit_keeps_index` |
| 11 | `/resume` 加载历史后 `_history` 清空 | `tests/test_tui_app.py::test_resume_clears_history` |
| 12 | 状态行显示 `provider / model` | `tests/test_tui_app.py::test_status_line_shows_provider_model` |
| 13 | `/resume` 后状态行更新为被恢复 session 的 provider/model | `tests/test_tui_app.py::test_status_line_updates_after_resume` |
| 14 | `/resume` Modal Up/Down/Enter 工作 | `tests/test_tui_app.py::test_resume_modal_arrow_keys_navigate_and_enter_selects` |
| 15 | `/resume` 后 transcript 不含"已恢复会话" | `tests/test_tui_app.py::test_no_restored_session_hint_after_resume` |
| 16 | `uv run pytest` 全绿；`uv run ruff check .` 通过 | CI / 主 Agent 跑 |
| 17 | CLI `chat` 命令 AC1 路径断言改为新路径 | `tests/test_cli.py::test_chat_creates_db_on_first_run` 更新 |
| 18 | 迁移同时搬走 `chat.db-wal` / `chat.db-shm` | `tests/test_storage.py::test_migration_includes_wal_shm` |

## 10. 风险与处理

| 风险 | 处理 |
|------|------|
| 迁移期间用户机器异常断电 | `shutil.move` 在同文件系统内是原子的；若跨文件系统退化为 copy + delete，删除失败会留两份，RepoError 让用户处理 |
| 老路径文件被用户手动改了名 | RepoError 提示 |
| 历史无限增长 | 100 条上限 |
| 状态行被用户误以为可点击 | Static 不绑定事件；颜色 muted 暗示"信息条" |
| `/resume` 加载历史后状态行有"瞬时不同步"窗口 | `_on_resume_dismissed` 在同函数内更新 `self.title_suffix` + `#status-line.update()`，无窗口 |
| Up 键在 Input 上与 Textual 默认行为冲突 | Textual `Input` 默认 Up/Down 是"光标上下移动"；binding 优先覆盖会破坏光标移动。我们方案：仅当 `Input.value == ""` 或光标在第一/末行时才让 Up/Down 走历史；否则保留光标移动。**见 §6 修订**：第一版 SPEC 此处过于宽松，bash 风格实际是"任何时候 Up 都替换文本"，光标移动改用 `Home`/`End` 即可 |
| 测试隔离：每个测试不污染 `~/.invest-pilot/` | 现有测试用 `monkeypatch.setattr(Path, "home", lambda: tmp_path)`；新增测试沿用同一模式 |

## 11. §6 修订（关闭内部风险"Up 键冲突"）

最终采用 bash 风格：**任何时候按 Up 都将 input 替换为历史条目**，光标移到末尾；Down 同理。Input 的默认 Up/Down（光标移动）在本 App 被 binding 覆盖；要移动光标用 `Home` / `End` 键。

测试覆盖：
- 空 input 按 Up → 历史第 1 条
- 非空 input 按 Up → 历史前一条（旧值被替换；不与光标移动冲突测试单独覆盖：测试只验证 value 替换，不验证光标位置）

## 12. 接口契约（变更部分）

```python
# investpilot/storage/db.py
def open_default_db() -> Path:
    """返回 ~/.invest-pilot/storage/sqlite/chat.db
    自动建 ~/.invest-pilot/ 与 ~/.invest-pilot/storage/sqlite/
    从 ~/.invest-pilot/chat.db 一次性迁移（如存在）
    """
```

```python
# investpilot/interface/tui_app.py
class InvestPilotApp:
    BINDINGS = [..., Binding("up", "history_prev", ...), Binding("down", "history_next", ...)]
    
    def action_history_prev(self) -> None: ...
    def action_history_next(self) -> None: ...
    def _refresh_status_line(self) -> None: ...
```

不引入新模块；不破坏 v0.3.0 公开 API。