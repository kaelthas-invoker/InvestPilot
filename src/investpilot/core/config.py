from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from investpilot.core.errors import ConfigError

DEFAULT_MODEL = "MiniMax-M3"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_ANTHROPIC_BASE = "https://api.minimaxi.com/anthropic"
DEFAULT_OPENAI_BASE = "https://api.minimaxi.com/v1"


@dataclass(frozen=True)
class AppConfig:
    provider: str
    model: str
    max_tokens: int
    api_key: str
    base_url: str


def load_config(
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    env = dict(environ) if environ is not None else dict(__import__("os").environ)
    cfg_path = _resolve_path(path, env)
    raw = _read_yaml(cfg_path)
    provider = str(raw.get("provider", "anthropic")).strip().lower()
    if provider not in {"anthropic", "openai"}:
        raise ConfigError(f"不支持的 provider: {provider!r}，请使用 anthropic 或 openai")
    model = str(raw.get("model") or DEFAULT_MODEL)
    max_tokens = int(raw.get("max_tokens") or DEFAULT_MAX_TOKENS)
    api_key = _resolve_api_key(provider, raw, env)
    base_url = _resolve_base_url(provider, raw, env)
    return AppConfig(
        provider=provider,
        model=model,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
    )


def _resolve_path(path: Path | None, env: Mapping[str, str]) -> Path:
    if path is not None:
        return Path(path)
    if env.get("INVESTPILOT_CONFIG"):
        return Path(env["INVESTPILOT_CONFIG"])
    return Path.cwd() / "config.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(
            f"未找到配置文件: {path}。请复制 config.example.yaml 为 config.yaml 并填写。"
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"配置文件 YAML 无效: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件根节点必须是映射: {path}")
    return data


def _resolve_api_key(provider: str, raw: dict[str, Any], env: Mapping[str, str]) -> str:
    if raw.get("api_key"):
        return str(raw["api_key"])
    if provider == "anthropic":
        key = env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN") or ""
    else:
        key = env.get("OPENAI_API_KEY") or ""
    if not key:
        raise ConfigError(
            "缺少 API 密钥。请设置环境变量或在 config.yaml 中配置 api_key。"
        )
    return key


def _resolve_base_url(provider: str, raw: dict[str, Any], env: Mapping[str, str]) -> str:
    if raw.get("base_url"):
        return str(raw["base_url"]).rstrip("/")
    if provider == "anthropic":
        return (env.get("ANTHROPIC_BASE_URL") or DEFAULT_ANTHROPIC_BASE).rstrip("/")
    return (env.get("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE).rstrip("/")
