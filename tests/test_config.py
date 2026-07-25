from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from investpilot.core.config import load_config
from investpilot.core.errors import ConfigError


def test_load_from_yaml_and_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        yaml.dump({"provider": "openai", "model": "MiniMax-M3", "max_tokens": 1024}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    cfg = load_config(cfg_path, environ=os.environ)
    assert cfg.provider == "openai"
    assert cfg.model == "MiniMax-M3"
    assert cfg.max_tokens == 1024
    assert cfg.api_key == "sk-test"
    assert cfg.base_url == "https://api.minimaxi.com/v1"


def test_anthropic_auth_token_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"provider": "anthropic"}), encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-test")
    cfg = load_config(cfg_path, environ=os.environ)
    assert cfg.api_key == "tok-test"
    assert cfg.base_url == "https://api.minimaxi.com/anthropic"


def test_missing_key_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"provider": "anthropic"}), encoding="utf-8")
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ConfigError, match="密钥"):
        load_config(cfg_path, environ=os.environ)


def test_invalid_provider_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"provider": "foo", "api_key": "x"}), encoding="utf-8")
    with pytest.raises(ConfigError, match="provider"):
        load_config(cfg_path, environ=os.environ)


def test_missing_file_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("INVESTPILOT_CONFIG", raising=False)
    with pytest.raises(ConfigError, match="config"):
        load_config(None, environ=os.environ)
