from __future__ import annotations

import sys
from datetime import datetime, timezone

import typer

from investpilot import __version__

app = typer.Typer(help="InvestPilot — 投资研究辅助 agent", no_args_is_help=True)


@app.command()
def status() -> None:
    """打印版本、UTC 时间、Python 版本。"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    py = f"Python {sys.version_info.major}.{sys.version_info.minor}"
    typer.echo(f"InvestPilot v{__version__}")
    typer.echo(now)
    typer.echo(py)


@app.command()
def chat() -> None:
    """启动 TUI 多轮聊天（Task 6 实现）。"""
    typer.echo("chat 尚未实现", err=True)
    raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
