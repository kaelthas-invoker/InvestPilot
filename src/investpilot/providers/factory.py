from __future__ import annotations

from investpilot.core.config import AppConfig
from investpilot.core.errors import ConfigError
from investpilot.providers.anthropic_provider import AnthropicProvider
from investpilot.providers.base import ChatProvider
from investpilot.providers.openai_provider import OpenAIProvider


def build_provider(config: AppConfig) -> ChatProvider:
    if config.provider == "openai":
        return OpenAIProvider(
            config.api_key, config.base_url, config.model, config.max_tokens
        )
    if config.provider == "anthropic":
        return AnthropicProvider(
            config.api_key, config.base_url, config.model, config.max_tokens
        )
    raise ConfigError(f"不支持的 provider: {config.provider}")
