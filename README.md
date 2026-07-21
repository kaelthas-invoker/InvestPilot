# InvestPilot

> A+H 双重市场投研顾问 agent。当前阶段：**v0.1 脚手架**（最小可跑）。
> 完整产品目标见 `CLAUDE.md` §0；版本迭代流程见 `.claude/skills/version-iteration/SKILL.md`。

## 项目简介

InvestPilot 是一个单用户、本机优先、Mac mini 后承接 24×7 的 A+H 双重市场投研顾问 agent。
MVP 包含三件事：对话式 CLI（带来源答案）、每日早报、周报。

## 安装

```bash
uv sync --all-extras
```

需要 Python ≥ 3.12；本机如未装，uv 会自动下载。

## 运行

```bash
uv run fin-agent status
```

输出三行：

```
InvestPilot v0.1.0
2026-07-15T10:44:47.890555Z
Python 3.13
```

查看帮助：

```bash
uv run fin-agent --help
```

## 测试

```bash
uv run pytest tests/
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