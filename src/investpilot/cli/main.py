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
    """启动全屏 TUI 多轮聊天。"""
    from investpilot.assistant.session import ChatSession
    from investpilot.core.config import load_config
    from investpilot.core.errors import ConfigError
    from investpilot.interface.tui_app import run_tui
    from investpilot.providers.factory import build_provider
    from investpilot.storage import RepoError, SessionRepository, open_default_db

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    try:
        db_path = open_default_db()
        repo = SessionRepository(db_path)
    except RepoError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    provider = build_provider(cfg)
    session = ChatSession(
        provider,
        provider_name=cfg.provider,
        model=cfg.model,
        repo=repo,
    )
    run_tui(session, provider=cfg.provider, model=cfg.model, repo=repo)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
