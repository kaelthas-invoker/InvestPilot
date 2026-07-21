# InvestPilot v0.2 SPEC — TUI 多轮聊天

> 状态：设计已对齐用户确认，待实现计划  
> 日期：2026-07-21  
> 交付目标：可用全屏 TUI 进行连续多轮会话（流式输出）

## 1. 目标

把 InvestPilot 从 v0.1 脚手架推进为可本地运行的**聊天 AI 应用**：

- 以 Claude Code 风格的**全屏 TUI**交互
- 支持**连续多轮**对话（进程内记忆）
- 助手回复**流式**展示
- 通过 **OpenAI 兼容**与 **Anthropic 兼容**协议调用模型（默认对接 MiniMax）

输出定位仍为研究辅助，非财务建议；v0.2 **不**交付投研工具链。

## 2. 范围

### 2.1 In scope

| 项 | 说明 |
|----|------|
| 入口 | `fin-agent` / `fin-agent chat` 启动 TUI；保留 `fin-agent status` |
| TUI | Textual 全屏：可滚动 transcript + 底部输入 |
| 多轮 | 进程内 message history；第二轮起带上文 |
| 流式 | provider 流式增量写入 UI |
| 双协议 | `provider: anthropic \| openai` |
| 配置 | 仓库内 `config.example.yaml`；本地 `config.yaml`（gitignore） |
| 分层 | `interface` / `assistant` / `providers` / `core` |
| 质量 | pytest + ruff；provider/assistant 可单测 |

### 2.2 Out of scope（非目标）

- 工具调用 / Function Call / 投研数据源
- 磁盘会话持久化、命名会话、会话列表
- 读取 `~/.claude/env.d/minimax.env` 或 `active.env`
- 多模态输入、精修 thinking UI、自动重试、计费面板
- Web UI

## 3. 架构

采用方案 A：**薄 Textual 壳 + 可替换 provider 流式客户端**。

```
用户输入
  → interface (Textual)
  → assistant (system prompt + history + 编排一轮)
  → providers (openai | anthropic stream)
  → 增量 token 回 interface
  → 完成后 assistant 写入完整 assistant 消息
```

| 层 | 职责 | 不负责 |
|----|------|--------|
| `interface` | TUI 布局、输入、流式渲染、退出 | HTTP、协议细节 |
| `assistant` | system 提示、消息列表、`send` 编排 | UI 控件、原始 HTTP |
| `providers` | OpenAI/Anthropic 兼容流式调用，统一 chunk 抽象 | 业务提示词、TUI |
| `core` | 配置加载、错误类型、版本 | 对话逻辑 |

### 3.1 统一流式抽象

```text
StreamChunk:
  kind: "text" | "error" | "done"
  text: str   # text 增量；error 时为可读信息
```

v0.2 主 UI 只渲染 `text`；thinking 若出现可忽略或降级不展示（避免刷屏），不阻塞多轮主路径。

### 3.2 消息模型

内存中：

```text
Message: role in {system, user, assistant}, content: str
```

- `system` 仅用于请求，不在 transcript 重复刷屏（或仅启动时一条说明）
- 每轮：append user → stream assistant → append 完整 assistant content
- 下一轮请求携带完整 history（含 system）

## 4. TUI 交互

- **布局**：上方 `Scrollable` 对话区；底部输入框
- **发送**：Enter 发送；生成中锁定输入
- **流式**：assistant 气泡/块内追加 token
- **退出**：`Ctrl+C` / `Ctrl+D` / `/quit`
- **错误**：对话区展示错误，不清空 history，可继续输入
- **会话**：仅进程内；退出即新会话

## 5. 配置

### 5.1 文件

| 文件 | 用途 |
|------|------|
| `config.example.yaml` | 提交仓库，字段说明与示例值（无真实密钥） |
| `config.yaml` | 本地实际配置，**gitignore**，不提交 |

查找顺序（实现时固定一处文档化）：

1. 环境变量 `INVESTPILOT_CONFIG` 指向的路径（若设置）
2. 当前工作目录 `./config.yaml`
3. 否则仅 example/默认值不足以带 key 时启动失败并提示复制 example

### 5.2 示例字段

```yaml
# config.example.yaml
provider: anthropic          # anthropic | openai
model: MiniMax-M3
max_tokens: 4096
# base_url:                  # 可选；不填则用下方默认
# api_key:                   # 可选；更推荐用环境变量

# 环境变量（推荐）：
# Anthropic 兼容:
#   ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN
#   ANTHROPIC_BASE_URL（默认 https://api.minimaxi.com/anthropic）
# OpenAI 兼容:
#   OPENAI_API_KEY（可与 MiniMax 同一 key）
#   OPENAI_BASE_URL（默认 https://api.minimaxi.com/v1）
```

### 5.3 凭证与默认 endpoint（MiniMax）

依据 [MiniMax 前置准备](https://platform.minimaxi.com/docs/guides/quickstart-preparation)：

| provider | Key 来源 | Base URL 默认 |
|----------|----------|----------------|
| `anthropic` | `ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN`，或 config `api_key` | `ANTHROPIC_BASE_URL` 或 `https://api.minimaxi.com/anthropic` |
| `openai` | `OPENAI_API_KEY`，或 config `api_key`；若仍缺可用与 anthropic 相同的显式 `api_key` 字段 | `OPENAI_BASE_URL` 或 `https://api.minimaxi.com/v1` |

**明确不做**：读取 `~/.claude/env.d/minimax.env` / `active.env`。

**安全**：密钥不写日志、不进 git；example 中不放真实 key。

### 5.4 模型默认

- config `model` 优先
- 否则默认 `MiniMax-M3`

## 6. Provider 行为

### 6.1 Anthropic 兼容

- SDK：`anthropic`
- `messages.stream` / stream API
- `system` 走 API system 参数；history 为 user/assistant 交替
- 流式：消费 `text_delta` 作为 `StreamChunk(kind="text")`
- 参考：[Anthropic API 兼容](https://platform.minimaxi.com/docs/api-reference/text-anthropic-api)

### 6.2 OpenAI 兼容

- SDK：`openai`
- `chat.completions` `stream=True`
- messages 含 system + history
- 流式：`delta.content` → `StreamChunk(kind="text")`
- 参考：[OpenAI API 兼容](https://platform.minimaxi.com/docs/api-reference/text-openai-api)

### 6.3 系统提示（v0.2 最小）

固定短提示：InvestPilot 为投资**研究辅助**助手；回答简洁；**非**投资建议。不在本版扩展工具说明。

## 7. 错误处理

| 场景 | 行为 |
|------|------|
| 缺 config / 缺 key / 非法 provider | 启动失败，中文可操作提示（复制 example、设 key） |
| YAML 损坏 | 启动失败，指出路径 |
| 网络/API/流中断 | UI 显示错误；history 保留用户已发送内容；不自动重试 |
| 空输入 | 忽略，不发起请求 |

## 8. 包与依赖

- Python ≥ 3.12，`uv`
- 依赖：`typer`、`textual`、`openai`、`anthropic`、`pyyaml`（或等价）
- 入口：`fin-agent = investpilot.cli.main:app`（或等价，保持脚本名）
- 版本：实现时 bump 至 `0.2.0`（与交付切片一致）

建议目录（实现可微调，保持分层名）：

```text
src/investpilot/
  __init__.py
  cli/main.py
  interface/tui_app.py
  assistant/session.py
  providers/base.py
  providers/openai_provider.py
  providers/anthropic_provider.py
  core/config.py
  core/errors.py
config.example.yaml
config.yaml                 # gitignore
```

说明：当前仓库 `src/` 在 git 中为空，v0.2 需重建可安装包布局并通过现有/更新后的测试。

## 9. 验收标准

1. 复制 `config.example.yaml` → `config.yaml`，配置 provider/model，并用环境变量或 config 提供 key 后，`uv run fin-agent chat` 进入全屏 TUI。
2. 同一进程内连续 ≥2 轮对话；第 2 轮回复能利用第 1 轮上下文（可用“请重复我上句的关键词”类人工/集成验证）。
3. 助手回复以流式增量显示，而非仅结束后整段弹出。
4. `config.yaml` 中 `provider: openai` 与 `provider: anthropic` 均可完成至少一轮真实或契约级流式对话（自动化以 mock 为主；真实 key 可选手工）。
5. `uv run pytest`、`uv run ruff check .` 通过。
6. `config.yaml` 被 gitignore；`config.example.yaml` 在仓库中且无密钥。

## 10. 测试计划

| 测试 | 要点 |
|------|------|
| config | 解析 example；缺 key 报错；provider 枚举 |
| assistant | mock provider 两轮后 history 长度与角色正确 |
| openai provider | mock 流式 chunk 拼接 |
| anthropic provider | mock 流式 text_delta 拼接 |
| CLI | help 含 chat/status；status 仍可用 |
| 回归 | 覆盖率门槛保持项目既有策略（可随代码量上调，但不为凑数测 UI 像素） |

## 11. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Textual 异步与 SDK 流式线程/async 不匹配 | provider 统一 async 生成器或 `asyncio.to_thread` 桥接，单测锁协议 |
| MiniMax thinking 字段干扰展示 | v0.2 只抽 text；忽略 thinking |
| 原 smoke 测试依赖已缺失源码 | 重建包后更新/保留 status 与 version 断言 |
| 密钥误提交 | gitignore + example 分离 + review |

## 12. 开放问题

无阻塞开放问题。以下为已关闭决策摘要：

- 后端：OpenAI + Anthropic 兼容（非仅 mock）
- TUI：Textual 全屏
- 流式：是
- 会话：仅内存
- 配置：仓库 example + 本地 config.yaml；不读 `~/.claude/env.d`
- 沟通与文档：中文
