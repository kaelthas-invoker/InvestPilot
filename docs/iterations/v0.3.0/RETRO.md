# InvestPilot v0.3.0 RETRO — 对话持久化 + `/resume`

> 日期：2026-07-25
> 对应 SPEC：`./SPEC.md`，对应 PLAN：`./PLAN.md`

## 事实

- 新增 `investpilot/storage/` 模块（7 个源文件）：`db.py`（PRAGMA + 连接管理）、`schema.py`（DDL + user_version=1）、`repo.py`（SessionRepository 7 方法）、`models.py`（3 个 DTO + 2 异常）、`timefmt.py`、`preview.py`、`__init__.py`
- `investpilot/assistant/session.py` 增 `repo` / `provider_name` / `model` / `clock` 关键字参数；新增 `load_session(session_id)`；`send()` 走 SPEC §6 写入协议（user 立即写 + assistant streaming 行 + 首 chunk 立即 flush + 0.5s 节流 + finalize）
- 新增 `investpilot/interface/_resume_screen.py`：`ResumeListScreen(ModalScreen[str|None])` 用 `push_screen(widget, callback)` 注册回调，空列表显示提示，j/k 绑定驱动 ListView
- `investpilot/interface/tui_app.py` 增 CSS 三种消息样式 + 三个 helper + `_on_resume_dismissed` 回调；`/resume` 在流中走 system note 屏蔽
- `investpilot/cli/main.py` `chat` 命令构造 `SessionRepository(open_default_db())`，RepoError 走 typer Exit(1)
- 测试：新增 50 个测试用例（test_storage 23 + test_timefmt 8 + test_session 7 + test_tui_app 8 + test_cli 4），总计 104 个；uv run ruff check . 通过
- e2e-tester 走通：清干净状态 → 持久化两层消息 → format_age 7 边界 → preview 边界 → ResumeListScreen 渲染 → SVG 截图
- reality-checker：13 个 AC 全部对应到测试函数 + 行号

## 偏差与根因

| # | 偏差 | 根因 | 已应用改进 |
|---|------|------|-----------|
| 1 | plan-reviewer 首轮发现 14 条设计缺陷（partial flush 数据模型自相矛盾、seq/count/updated_at 无原子、恢复入口有 3 个、provider/model 恢复语义未定义、流中 /resume 无规则、Execute-A/C 不能并行、Runbook 缺少"做什么/目标/边界"、preview 规则模糊、age 边界样例错误、DB 初始化无验收、回滚声明错误、AC 缺测试映射） | 第一版 SPEC 边想边写，未按 SPEC 模板逐项检查 | 全面修订 SPEC §5/§6/§7/§8/§13 + PLAN §2 Runbook；plan-reviewer 二轮发现 3 条新缺陷（首 chunk 不立即 flush 导致 AC11 不可重现；`on_screen_resumed` 不是 Textual 真实 API；`open_default_db` 返回类型与 `SessionRepository.__init__` 矛盾） |
| 2 | 二轮 plan-reviewer 3 条新缺陷 | N2：首 chunk 等 0.5s 才 flush 让"进程崩在第一个 chunk 后"的恢复不可重现；N4：作者假设了 `App.on_screen_resumed` 这个不存在的钩子；N5：作者把 `open_default_db` 写成返回 `Connection` 但 `SessionRepository.__init__` 接收 `Path`，调用 `SessionRepository(open_default_db())` 类型不一致 | 写入协议改为"首 chunk 立即 flush + 后续 0.5s 节流"；改用 `push_screen(widget, callback)` API + `_on_resume_dismissed`；`open_default_db() -> Path`，`SessionRepository(db_path: Path)` |
| 3 | code-reviewer Execute-C 复测发现：Modal 结果未传到回调，测试直接调 `on_screen_resumed` 绕过了真实 push_screen 流程 | 作者在初版用了 `on_screen_resumed` 这个虚构 API 名；测试为了让现有实现"过"，直接调用了那个不存在的回调 | 改用 Textual 真实 API `push_screen(widget, callback)`；删除 `on_screen_resumed`；新增 `test_resume_modal_e2e_dismiss_delivers_to_callback` 用 `ListView.Selected` 事件触发真实 dismiss 路径；新增 `test_resume_screen_jk_navigation` 验证 j/k 绑定；加强 `test_message_styles` 解析 CSS 字符串校验 `heavy cyan` / `heavy orange` |

## 验收对照（SPEC §11）

| # | 验收项 | 覆盖测试 | 结果 |
|---|--------|---------|------|
| 1 | 首次 `chat` 自动建 DB（~/.invest-pilot/chat.db） | `tests/test_cli.py::test_chat_creates_db_on_first_run` | 通过 |
| 2 | 1 user + 1 assistant 后 DB 完整 | `tests/test_session.py::test_persist_user_and_assistant_after_send` | 通过 |
| 3 | 退出重启 `/resume` 能看到上次会话 | `tests/test_session.py::test_resume_roundtrip` + e2e 走查 | 通过 |
| 4 | 列表首行预览 + k8s age + updated_at DESC | `tests/test_storage.py::test_list_sessions_preview_and_age` | 通过 |
| 5 | 空列表显示"暂无历史会话" | `tests/test_tui_app.py::test_resume_screen_empty` | 通过 |
| 6 | Enter 加载并按样式渲染 | `tests/test_tui_app.py::test_resume_load_renders_with_styles` + `test_resume_modal_e2e_dismiss_delivers_to_callback` | 通过 |
| 7 | 加载后 send：provider 收到完整历史 | `tests/test_session.py::test_load_session_then_send_includes_history` | 通过 |
| 8 | `format_age` 真实边界 | `tests/test_timefmt.py`（0/59/60/3599/3600/86399/86400/-30） | 通过 |
| 9 | user 样式：heavy cyan + `你:`；assistant：heavy orange + `助手:` | `tests/test_tui_app.py::test_message_styles`（class + CSS 双校验） | 通过 |
| 10 | 加载历史样式与新建一致 | `tests/test_tui_app.py::test_loaded_messages_share_styles` | 通过 |
| 11 | 流中断在 0.5s 窗口：partial 文本保留 | `tests/test_session.py::test_streaming_message_persists_partial` + 首 chunk 立即 flush 协议 | 通过 |
| 12 | 流中 `/resume` 禁用 | `tests/test_tui_app.py::test_resume_blocked_during_stream` | 通过 |
| 13 | pytest 全绿；ruff 通过 | e2e-tester 复跑 `uv run pytest -q` → 104 passed；`uv run ruff check .` → All checks passed | 通过 |

## 设计取舍记录

**为什么用 `BEGIN IMMEDIATE` 单事务而不是 ORM？**

`append_message` 必须保证：(1) seq 单调无重复，(2) message 插入与 session.message_count / updated_at 同步。两个写并发场景下，单纯 `SELECT MAX(seq) + 1` 会让两个 writer 读到相同值。`BEGIN IMMEDIATE` 获取 RESERVED 锁是 SQLite 推荐的并发写策略；ORM 反而要绕一圈才能拿到等价的语义。验证：2 线程 × 50 条并发 append 测试通过，无重复 seq，message_count=100。

**为什么 streaming 行用 `status` 字段而不是单独的 draft 表？**

崩溃恢复的"未完成 assistant 行"在表结构上有两种表达：
- 独立 `message_draft` 表（更直观，但要和 message 双写）
- 在 `message` 上加 `status` 字段（更紧凑，复用索引）

选第二种：`status='streaming'` 表示流未结束，`status='final'` 表示已收尾。`/resume` 加载时不做 UI 区分（v0.3.0），但 schema 已经为下轮的"显示流中断标记"留好出口。代价是 `update_message_content` / `finalize_message` 必须明确不改 seq/created_at/message_count/updated_at —— 已用单测守住。

**为什么 `open_default_db()` 返回 `Path` 而 `SessionRepository` 内部开连接？**

两种 API 边界：
- `open_default_db()` 返回 `Connection`：调用方少一行 `SessionRepository(...)`，但 `Connection` 在调用方手里，repo 怎么复用就管不到
- `open_default_db()` 返回 `Path`，`SessionRepository(path)`：repo 自主管连接，按方法短连接复用

选第二种。理由：`SessionRepository` 是连接生命周期的唯一所有者；将来要换连接池、加 health check，只改 `repo.py` 即可，不影响 CLI 调用站点。

**为什么不切换 provider/model 在 resume 时？**

SPEC §7 选择"恢复时仍用启动时的 provider/model"。三个原因：

1. 用户配置文件是唯一可信的 provider 切换入口；运行时切换会让"为什么我 resume 后突然走错模型"成为难以调试的问题
2. system_prompt 是 session 级别的语义契约（一旦写入即固定），与 provider/model 配置维度不同，必须保留
3. 元数据仍然持久化，UI 上展示，让用户知道"我正在继续一个用 X 模型开的对话"，但实际调用走当前配置

未来要做 provider 切换面板或 per-session 配置时，元数据已经在表里，无需 schema migration。

## 关键产物清单

- `docs/iterations/v0.3.0/SPEC.md` — 13 节，§11 含 13 条 AC
- `docs/iterations/v0.3.0/PLAN.md` — Stage DAG + Runbook A1–A8 / B1–B2 / C1–C3 / D1 / V1–V4 / R1
- `docs/iterations/v0.3.0/RETRO.md` — 本文件
- `docs/iterations/v0.3.0/verify/manual_walkthrough.txt` — e2e 走查 transcript
- `docs/iterations/v0.3.0/verify/resume_screen.svg` — ResumeListScreen 截图
- `docs/iterations/v0.3.0/verify/db_after_two_sends.txt` — sqlite3 .dump 输出
- 源码：src/investpilot/storage/ (7 文件)、src/investpilot/assistant/session.py、src/investpilot/interface/tui_app.py、src/investpilot/interface/_resume_screen.py、src/investpilot/cli/main.py
- 测试：tests/test_storage.py、tests/test_timefmt.py、tests/test_session.py（追加 7）、tests/test_tui_app.py（追加 8）、tests/test_cli.py（追加 2）

## 剩余风险

| 风险 | 是否需要处理 |
|------|-------------|
| `~/.invest-pilot/chat.db` 用户手动删了后会丢所有历史 | 不需要 — 这是用户行为，无 schema 副作用 |
| 进程崩在 user message 写完但 streaming 行未创建前 → 该 user 行孤立（无对应 assistant） | 不需要 — 罕见；下次 `/resume` 看到孤立 user，UI 不区分；下次 send 自动接续 |
| assistant 行 `status='streaming'` 在 `/resume` 上与 `status='final'` 显示完全一样 | 不需要 — v0.3.0 spec 明示不区分；下轮可加"显示中断标记" |
| DB 在网络盘上时 WAL 性能可能差 | 不需要 — 单用户本地 DB；如未来要多客户端同步，那是别的迭代 |
| 用户改了 `config.yaml` 但想继续旧 session | 不需要 — 已在 SPEC §7 明确：恢复时仍用启动配置；system_prompt 从 DB 取 |
| 测试 `test_resume_modal_e2e_dismiss_delivers_to_callback` 用 `post_message` 触发 `ListView.Selected`，不是真键盘事件 | 待评估 — 当前能覆盖"dismiss → callback"链路；如未来 ListView API 变化需更新 |
| chat 命令启动时若 `~/.invest-pilot/` 是普通文件，RepoError 提示文案无解释"应该删除还是改名" | 待评估 — ux 小项，不阻塞 |