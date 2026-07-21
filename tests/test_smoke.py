"""InvestPilot smoke test: 验证 invest-pilot CLI 真实可跑."""

from __future__ import annotations

import subprocess
import sys

import pytest
from typer.testing import CliRunner

from investpilot.cli.main import app


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


def test_invest_pilot_status_runs_via_subprocess() -> None:
    """invest-pilot status 通过子进程跑应退出码 0 且输出含 InvestPilot v0.2."""
    result = subprocess.run(
        [sys.executable, "-m", "investpilot", "status"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"非零退出码 {result.returncode}\nstderr={result.stderr}"
    lines = result.stdout.strip().splitlines()
    assert len(lines) >= 3, f"应至少 3 行输出，实际 {len(lines)} 行: {result.stdout!r}"
    assert "InvestPilot v0.2" in lines[0], f"第 1 行缺少版本: {lines[0]!r}"
    assert lines[1].startswith("20"), f"第 2 行应为 UTC ISO 时间: {lines[1]!r}"
    assert lines[2].startswith("Python 3."), f"第 3 行应为 Python 版本: {lines[2]!r}"


def test_invest_pilot_status_via_cli_runner(runner: CliRunner) -> None:
    """通过 CliRunner 调用 status 子命令，验证 Typer 内部逻辑覆盖."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, f"非零退出码 {result.exit_code}\noutput={result.output}"
    lines = result.output.strip().splitlines()
    assert len(lines) >= 3, f"应至少 3 行输出，实际 {len(lines)} 行: {result.output!r}"
    assert "InvestPilot v0.2" in lines[0]
    assert lines[1].startswith("20")
    assert lines[2].startswith("Python 3.")


def test_invest_pilot_help_via_cli_runner(runner: CliRunner) -> None:
    """无参数时 Typer 应显示帮助（含 chat 与 status 子命令）."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "chat" in result.output
    assert "status" in result.output


def test_package_version() -> None:
    """investpilot.__version__ 应等于 '0.2.0'."""
    import investpilot

    assert investpilot.__version__ == "0.2.0"
