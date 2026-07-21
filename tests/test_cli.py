from typer.testing import CliRunner

from investpilot.cli.main import app

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
