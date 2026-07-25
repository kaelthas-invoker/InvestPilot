from pathlib import Path

from typer.testing import CliRunner

from investpilot import storage as storage_pkg
from investpilot.cli.main import app
from investpilot.interface import tui_app
from investpilot.providers import factory as provider_factory
from investpilot.storage import RepoError
from investpilot.storage import db as storage_db

runner = CliRunner()


def test_help_lists_chat_and_status():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "chat" in r.output
    assert "status" in r.output


def test_chat_missing_config_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("INVESTPILOT_CONFIG", raising=False)
    r = runner.invoke(app, ["chat"])
    assert r.exit_code != 0
    assert "config" in (r.output + str(r.exception)).lower() or "配置" in r.output


def _stub_config(tmp_path, monkeypatch):
    """写一份最小的合法 config，供 load_config 通过。"""
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "provider: anthropic\nmodel: stub-model\napi_key: stub-key\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INVESTPILOT_CONFIG", str(config_yaml))


def test_chat_creates_db_on_first_run(tmp_path, monkeypatch):
    """首次 chat 在 HOME 下创建 ~/.invest-pilot/storage/sqlite/chat.db。

    注入 tmp_path 为 HOME；在 chat() 中 ``from … import …`` 的源模块上 stub
    build_provider / run_tui，避免真实模型请求与真实 TUI 启动。
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _stub_config(tmp_path, monkeypatch)

    fake_provider = object()

    def fake_build_provider(cfg):
        return fake_provider

    def fake_run_tui(session, *, provider, model, repo):
        return None

    # chat() 内部的 `from … import …` 会重新绑定本地名字；直接 patch 源模块。
    monkeypatch.setattr(provider_factory, "build_provider", fake_build_provider)
    monkeypatch.setattr(tui_app, "run_tui", fake_run_tui)

    r = runner.invoke(app, ["chat"])

    data_dir = tmp_path / ".invest-pilot"
    sqlite_dir = data_dir / "storage" / "sqlite"
    db_file = sqlite_dir / "chat.db"
    assert data_dir.exists(), f"data dir not created; output={r.output!r}"
    assert data_dir.is_dir()
    assert sqlite_dir.is_dir(), f"sqlite dir not created; output={r.output!r}"
    assert db_file.exists(), f"db file not created; output={r.output!r}"
    # SPEC §5：HOME 下数据目录 mode 0o700
    dir_mode = data_dir.stat().st_mode & 0o777
    assert dir_mode == 0o700, f"data dir mode {oct(dir_mode)} != 0o700"
    if r.exception is not None:
        raise r.exception


def test_chat_repo_error_prints_and_exits_1(tmp_path, monkeypatch, capsys):
    """当 open_default_db 抛 RepoError 时，chat 命令必须以 exit code 1 退出并打印错误。"""
    _stub_config(tmp_path, monkeypatch)

    monkeypatch.setattr(provider_factory, "build_provider", lambda cfg: object())
    monkeypatch.setattr(tui_app, "run_tui", lambda *a, **kw: None)

    def boom():
        raise RepoError("simulated storage failure")

    # `cli.main` 通过 `from investpilot.storage import open_default_db` 拿名字；
    # storage 包又把名字从 storage.db 拉过来作为独立绑定。两处都打补丁。
    monkeypatch.setattr(storage_db, "open_default_db", boom)
    monkeypatch.setattr(storage_pkg, "open_default_db", boom)

    r = runner.invoke(app, ["chat"])

    assert r.exit_code == 1, (
        f"expected exit 1, got {r.exit_code}; output={r.output!r}"
    )
    out = (r.output or "") + (r.stderr or "") + capsys.readouterr().err
    assert "simulated storage failure" in out
