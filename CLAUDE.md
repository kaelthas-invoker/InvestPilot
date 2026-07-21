# InvestPilot 项目说明

> 本文件描述项目方向、业务分层、技术选型、文档管理和迭代要求。具体执行流程见 `.claude/skills/version-iteration/SKILL.md`。

## 项目描述

InvestPilot 是一个面向投资研究和交易研究的个人 AI 助手。
输出定位为研究辅助，帮助用户围绕市场、公司、组合、策略和研究流程提问，不是财务建议。

## 项目架构

业务先按最小分层演进：

- `interface`：TUI / CLI 入口，负责输入、输出、会话体验和错误展示。
- `assistant`：对话编排，负责系统提示词、上下文组织、工具调用边界和响应整理。
- `research`：投资研究能力，逐步承接市场、公司、组合、策略等研究任务。
- `providers`：外部模型和数据源适配，保持可替换，不把供应商细节扩散到业务层。
- `core`：共享类型、配置、错误、日志和基础工具。

## 技术选型

- 语言：Python 3.12+。
- 包管理与运行：`uv`。
- CLI/TUI：以 `invest-pilot` 为入口；TUI 库按 MVP 需要选择，优先简单可维护。
- AI 调用：先封装小模型客户端边界，再接具体 provider。
- 质量工具：`pytest`、`ruff`；依赖变化必须同步 `uv.lock`。

常用命令：`uv sync`、`uv run invest-pilot --help`、`uv run invest-pilot chat`、`uv run pytest`、`uv run ruff check .`。

## 文档管理

- README 面向用户和本地运行。
- `CLAUDE.md` 只放稳定项目规则，保持短小。
- 迭代文档按需放在 `docs/iterations/<version>/`，优先 `SPEC.md`、`PLAN.md`、`RETRO.md`。
- 不为未来想法创建长 reference 或占位目录；需要时由迭代产出。

## 迭代要求

- 项目变更使用 `version-iteration` skill。
- 每轮只做一个可验证、可完整闭环的切片，优先交付可运行体验。
- 先明确目标、范围、非目标和验收检查，再实现。
- 不做无重复证据的抽象；不为“以后可能”扩展架构。
- 结束时报告改动、验证命令、结果和剩余风险。
