# InvestPilot

> A+H 双重市场投研顾问 agent。当前阶段：**v0.2 多轮 TUI 聊天**。
> 完整产品目标见 `CLAUDE.md`；版本迭代流程见 `.claude/skills/version-iteration/SKILL.md`。

## 项目简介

InvestPilot 是一个面向投资研究和交易研究的个人 AI 助手。
输出定位为研究辅助，帮助用户围绕市场、公司、组合、策略和研究流程提问，不是财务建议。

## 安装与配置

```bash
uv sync
cp config.example.yaml config.yaml
# 编辑 config.yaml；export ANTHROPIC_AUTH_TOKEN=... 或 OPENAI_API_KEY=...
```

需要 Python ≥ 3.12；本机如未装，uv 会自动下载。

## 运行

多轮聊天（全屏 TUI）：

```bash
uv run invest-pilot chat
```

状态：

```bash
uv run invest-pilot status
```

输出三行：

```
InvestPilot v0.2.0
2026-07-15T10:44:47.890555Z
Python 3.13
```

查看帮助：

```bash
uv run invest-pilot --help
```

## 测试

```bash
uv run pytest
```

覆盖率报告（门槛 20%）：

```bash
uv run pytest --cov=investpilot --cov-report=term-missing --cov-fail-under=20
```

## Lint

```bash
uv run ruff check .
```

## License

见 [LICENSE](LICENSE)。
