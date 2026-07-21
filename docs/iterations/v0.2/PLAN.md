# InvestPilot v0.2 TUI 多轮聊天 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付全屏 Textual TUI，支持进程内多轮会话与 OpenAI/Anthropic 兼容流式回复。

**Architecture:** `interface`（Textual）→ `assistant`（history + 编排）→ `providers`（openai/anthropic 流）→ `core`（config/errors）。密钥与 endpoint 来自仓库本地 `config.yaml` + 环境变量；不读 `~/.claude/env.d`。

**Tech Stack:** Python 3.12+、uv、typer、textual、openai、anthropic、PyYAML、pytest、ruff

**Spec:** `docs/iterations/v0.2/SPEC.md`

## Global Constraints

- 入口脚本名：`invest-pilot`（不再使用 `fin-agent`）
- 版本 bump 至 `0.2.0`
- `config.example.yaml` 入库；`config.yaml` 必须 gitignore
- 禁止读取 `~/.claude/env.d/minimax.env` 与 `active.env`
- provider 仅 `anthropic` | `openai`；默认 model `MiniMax-M3`
- Anthropic 默认 base：`https://api.minimaxi.com/anthropic`；OpenAI 默认：`https://api.minimaxi.com/v1`
- Anthropic key：`ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN` 或 config `api_key`
- OpenAI key：`OPENAI_API_KEY` 或 config `api_key`
- 流式统一为 async 迭代 `StreamChunk(kind, text)`
- 中文错误提示；密钥不写日志
- 每任务 TDD：先测后码；每任务结束 commit
- 沟通与用户可见文案：中文

## File map

| 路径 | 职责 |
|------|------|
| `src/investpilot/__init__.py` | `__version__ = "0.2.0"` |
| `src/investpilot/__main__.py` | `python -m investpilot` → CLI |
| `src/investpilot/core/errors.py` | `ConfigError`, `ProviderError` |
| `src/investpilot/core/config.py` | 加载 YAML + env 解析 `AppConfig` |
| `src/investpilot/providers/base.py` | `Message`, `StreamChunk`, `ChatProvider` |
| `src/investpilot/providers/openai_provider.py` | OpenAI 兼容流 |
| `src/investpilot/providers/anthropic_provider.py` | Anthropic 兼容流 |
| `src/investpilot/providers/factory.py` | `build_provider(config) -> ChatProvider` |
| `src/investpilot/assistant/session.py` | 多轮 session + system prompt |
| `src/investpilot/interface/tui_app.py` | Textual App |
| `src/investpilot/cli/main.py` | typer：`status`, `chat` |
| `config.example.yaml` | 示例配置 |
| `.gitignore` | 忽略 `config.yaml` |
| `pyproject.toml` | 依赖与 entry |
| `tests/test_config.py` | 配置 |
| `tests/test_session.py` | 多轮 |
| `tests/test_providers.py` | 双 provider mock 流 |
| `tests/test_cli.py` | CLI |
| `tests/test_smoke.py` | 更新 version 断言 |
| `README.md` | 运行说明 |

---

### Task 1: 包骨架 + 版本 + gitignore + example 配置

**Files:**
- Create: `src/investpilot/__init__.py`
- Create: `src/investpilot/__main__.py`
- Create: `src/investpilot/cli/__init__.py`
- Create: `src/investpilot/cli/main.py`（最小 status + 占位 app）
- Create: `src/investpilot/core/__init__.py`
- Create: `src/investpilot/core/errors.py`
- Create: `config.example.yaml`
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Modify: `tests/test_smoke.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Produces: `investpilot.__version__ == "0.2.0"`；`invest-pilot status` 打印三行；`ConfigError`/`ProviderError` 异常类

- [ ] **Step 1: 写/更新失败测试（version + status 文案）**

将 `tests/test_smoke.py` 中 `0.1` / `0.1.0` 改为期望 `0.2` / `0.2.0`：

```python
assert investpilot.__version__ == "0.2.0"
assert "InvestPilot v0.2" in lines[0]
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/test_smoke.py -v`  
Expected: FAIL（无包或 version 不对）

- [ ] **Step 3: 最小实现**

`src/investpilot/__init__.py`:
```python
__version__ = "0.2.0"
```

`src/investpilot/core/errors.py`:
```python
class ConfigError(Exception):
    """配置或凭证错误。"""


class ProviderError(Exception):
    """模型调用错误。"""
```

`src/investpilot/cli/main.py`:
```python
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
```

`src/investpilot/__main__.py`:
```python
from investpilot.cli.main import main

main()
```

`config.example.yaml`:
```yaml
# 复制为 config.yaml 后填写。不要提交 config.yaml。
provider: anthropic          # anthropic | openai
model: MiniMax-M3
max_tokens: 4096
# base_url:                  # 可选
# api_key:                   # 可选；推荐用环境变量

# Anthropic 兼容环境变量:
#   ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN
#   ANTHROPIC_BASE_URL  # 默认 https://api.minimaxi.com/anthropic
# OpenAI 兼容环境变量:
#   OPENAI_API_KEY
#   OPENAI_BASE_URL     # 默认 https://api.minimaxi.com/v1
```

`.gitignore` 追加:
```
# InvestPilot local secrets
config.yaml
```

`pyproject.toml` 更新:
```toml
version = "0.2.0"
# [project.scripts]
# invest-pilot = "investpilot.cli.main:app"
dependencies = [
    "typer>=0.12.0",
    "textual>=1.0.0",
    "openai>=1.40.0",
    "anthropic>=0.34.0",
    "pyyaml>=6.0",
]
```

- [ ] **Step 4: 同步依赖并跑测**

Run:
```bash
uv sync
uv run pytest tests/test_smoke.py -v
uv run ruff check src tests
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investpilot config.example.yaml pyproject.toml uv.lock .gitignore tests/test_smoke.py
git commit -m "feat: restore package skeleton for v0.2"
```

---

### Task 2: 配置加载

**Files:**
- Create: `src/investpilot/core/config.py`
- Create: `tests/test_config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `ConfigError`
- Produces:
  - `@dataclass AppConfig`: `provider: str`, `model: str`, `max_tokens: int`, `api_key: str`, `base_url: str`
  - `load_config(path: Path | None = None, environ: Mapping[str, str] | None = None) -> AppConfig`
  - 查找：`INVESTPILOT_CONFIG` → 显式 path → `./config.yaml`
  - 不存在配置文件且无法从 env 得到完整必要项时：`ConfigError`（中文）
  - provider 必须是 `anthropic` 或 `openai`
  - 默认 model `MiniMax-M3`，默认 max_tokens `4096`
  - anthropic base 默认 `https://api.minimaxi.com/anthropic`
  - openai base 默认 `https://api.minimaxi.com/v1`
  - key 解析见 Global Constraints；**禁止**读 `~/.claude/env.d`

- [ ] **Step 1: 写失败测试**

`tests/test_config.py`:
```python
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
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/test_config.py -v`  
Expected: FAIL import or missing `load_config`

- [ ] **Step 3: 实现 `load_config`**

实现要点（完整写入 `src/investpilot/core/config.py`）：

```python
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
```

- [ ] **Step 4: 跑测通过**

Run: `uv run pytest tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investpilot/core/config.py tests/test_config.py
git commit -m "feat: add AppConfig loader for v0.2"
```

---

### Task 3: Provider 抽象 + OpenAI/Anthropic 流式（mock 测）

**Files:**
- Create: `src/investpilot/providers/__init__.py`
- Create: `src/investpilot/providers/base.py`
- Create: `src/investpilot/providers/openai_provider.py`
- Create: `src/investpilot/providers/anthropic_provider.py`
- Create: `src/investpilot/providers/factory.py`
- Create: `tests/test_providers.py`
- Test: `tests/test_providers.py`

**Interfaces:**
- Produces:
```python
@dataclass(frozen=True)
class Message:
    role: str  # system | user | assistant
    content: str

@dataclass(frozen=True)
class StreamChunk:
    kind: str  # text | error | done
    text: str = ""

class ChatProvider(Protocol):
    async def stream_chat(self, messages: list[Message]) -> AsyncIterator[StreamChunk]:
        ...

class OpenAIProvider:
    def __init__(self, api_key: str, base_url: str, model: str, max_tokens: int) -> None: ...
    async def stream_chat(self, messages: list[Message]) -> AsyncIterator[StreamChunk]: ...

class AnthropicProvider:
    def __init__(self, api_key: str, base_url: str, model: str, max_tokens: int) -> None: ...
    async def stream_chat(self, messages: list[Message]) -> AsyncIterator[StreamChunk]: ...

def build_provider(config: AppConfig) -> ChatProvider: ...
```
- OpenAI：仅转发 `delta.content` 文本；异常 → yield `StreamChunk("error", msg)` 再 `done`
- Anthropic：仅转发 `text_delta`；忽略 thinking
- `build_provider` 按 `config.provider` 构造

- [ ] **Step 1: 写失败测试（用假 client 注入，避免真网）**

设计 provider 构造函数支持可选 `client=` 注入以便测试。

`tests/test_providers.py`:
```python
from __future__ import annotations

import pytest

from investpilot.core.config import AppConfig
from investpilot.providers.anthropic_provider import AnthropicProvider
from investpilot.providers.base import Message
from investpilot.providers.factory import build_provider
from investpilot.providers.openai_provider import OpenAIProvider


class _FakeOpenAIStream:
    def __init__(self, pieces: list[str]):
        self._pieces = pieces

    def __iter__(self):
        for p in self._pieces:
            delta = type("D", (), {"content": p})()
            choice = type("C", (), {"delta": delta})()
            yield type("Chunk", (), {"choices": [choice]})()


class _FakeOpenAIClient:
    def __init__(self, pieces: list[str]):
        self.pieces = pieces
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        assert kwargs.get("stream") is True
        return _FakeOpenAIStream(self.pieces)


@pytest.mark.asyncio
async def test_openai_provider_streams_text() -> None:
    client = _FakeOpenAIClient(["你", "好"])
    p = OpenAIProvider("k", "https://example.com/v1", "m", 100, client=client)
    out: list[str] = []
    kinds: list[str] = []
    async for ch in p.stream_chat([Message("user", "hi")]):
        kinds.append(ch.kind)
        if ch.kind == "text":
            out.append(ch.text)
    assert "".join(out) == "你好"
    assert kinds[-1] == "done"


class _FakeAnthropicStream:
    def __init__(self, pieces: list[str]):
        self._pieces = pieces

    def __iter__(self):
        for p in self._pieces:
            delta = type("D", (), {"type": "text_delta", "text": p})()
            yield type("Ev", (), {"type": "content_block_delta", "delta": delta})()


class _FakeAnthropicMessages:
    def __init__(self, pieces: list[str]):
        self.pieces = pieces

    def create(self, **kwargs):
        assert kwargs.get("stream") is True
        return _FakeAnthropicStream(self.pieces)


class _FakeAnthropicClient:
    def __init__(self, pieces: list[str]):
        self.messages = _FakeAnthropicMessages(pieces)


@pytest.mark.asyncio
async def test_anthropic_provider_streams_text() -> None:
    client = _FakeAnthropicClient(["A", "B"])
    p = AnthropicProvider("k", "https://example.com/anthropic", "m", 100, client=client)
    out: list[str] = []
    async for ch in p.stream_chat(
        [Message("system", "sys"), Message("user", "hi")]
    ):
        if ch.kind == "text":
            out.append(ch.text)
    assert "".join(out) == "AB"


def test_build_provider_openai() -> None:
    cfg = AppConfig("openai", "m", 1, "k", "https://example.com/v1")
    assert isinstance(build_provider(cfg), OpenAIProvider)


def test_build_provider_anthropic() -> None:
    cfg = AppConfig("anthropic", "m", 1, "k", "https://example.com/anthropic")
    assert isinstance(build_provider(cfg), AnthropicProvider)
```

`pyproject.toml` dev 依赖增加 `pytest-asyncio`：
```toml
"pytest-asyncio>=0.23.0",
```
并在 `[tool.pytest.ini_options]` 加：
```toml
asyncio_mode = "auto"
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv sync && uv run pytest tests/test_providers.py -v`  
Expected: FAIL

- [ ] **Step 3: 实现 providers**

`base.py`：定义 `Message`, `StreamChunk`, `ChatProvider` Protocol。

`openai_provider.py` 要点：
```python
# 使用 openai.OpenAI(api_key=..., base_url=...)
# stream = client.chat.completions.create(model=..., messages=..., max_tokens=..., stream=True)
# 在 async def stream_chat 内用 asyncio.to_thread 迭代同步 stream，或逐 chunk to_thread
# for chunk in stream:
#   text = chunk.choices[0].delta.content
#   if text: yield StreamChunk("text", text)
# yield StreamChunk("done")
# except Exception as exc: yield StreamChunk("error", f"OpenAI 调用失败: {exc}"); yield StreamChunk("done")
```

`anthropic_provider.py` 要点：
```python
# anthropic.Anthropic(api_key=..., base_url=...)
# system = 拼接 messages 中 role==system 的 content（单字符串）
# user_assistant = [m for m in messages if m.role != "system"]
# stream = client.messages.create(model=..., max_tokens=..., system=system or NOT_GIVEN, messages=[...], stream=True)
# 仅当 event.type == content_block_delta and delta.type == text_delta 时 yield text
```

`factory.py`:
```python
def build_provider(config: AppConfig) -> ChatProvider:
    if config.provider == "openai":
        return OpenAIProvider(config.api_key, config.base_url, config.model, config.max_tokens)
    if config.provider == "anthropic":
        return AnthropicProvider(config.api_key, config.base_url, config.model, config.max_tokens)
    raise ConfigError(f"不支持的 provider: {config.provider}")
```

- [ ] **Step 4: 跑测通过**

Run: `uv run pytest tests/test_providers.py tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investpilot/providers tests/test_providers.py pyproject.toml uv.lock
git commit -m "feat: add OpenAI and Anthropic streaming providers"
```

---

### Task 4: Assistant 多轮 Session

**Files:**
- Create: `src/investpilot/assistant/__init__.py`
- Create: `src/investpilot/assistant/session.py`
- Create: `tests/test_session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `ChatProvider.stream_chat`, `Message`, `StreamChunk`
- Produces:
```python
SYSTEM_PROMPT: str  # 研究辅助、非投资建议，中文短提示

class ChatSession:
    def __init__(self, provider: ChatProvider, system_prompt: str = SYSTEM_PROMPT) -> None: ...
    @property
    def messages(self) -> list[Message]: ...  # 含 system，只读副本
    async def send(self, user_text: str) -> AsyncIterator[StreamChunk]:
        """append user；stream；成功则 append assistant 全文；error chunk 不追加 assistant。"""
```

- [ ] **Step 1: 写失败测试**

```python
from __future__ import annotations

import pytest

from investpilot.assistant.session import ChatSession
from investpilot.providers.base import Message, StreamChunk


class _ScriptedProvider:
    def __init__(self) -> None:
        self.calls: list[list[Message]] = []

    async def stream_chat(self, messages: list[Message]):
        self.calls.append(list(messages))
        n = len(self.calls)
        yield StreamChunk("text", f"reply-{n}")
        yield StreamChunk("done")


@pytest.mark.asyncio
async def test_two_turns_keep_history() -> None:
    p = _ScriptedProvider()
    s = ChatSession(p)
    chunks1 = [c async for c in s.send("第一轮")]
    assert any(c.text == "reply-1" for c in chunks1 if c.kind == "text")
    chunks2 = [c async for c in s.send("第二轮")]
    assert any(c.text == "reply-2" for c in chunks2 if c.kind == "text")
    roles = [m.role for m in s.messages]
    assert roles[0] == "system"
    assert roles[1:] == ["user", "assistant", "user", "assistant"]
    assert s.messages[1].content == "第一轮"
    assert s.messages[3].content == "第二轮"
    # 第二轮请求应包含第一轮 assistant
    assert any(m.role == "assistant" and m.content == "reply-1" for m in p.calls[1])


@pytest.mark.asyncio
async def test_error_does_not_append_assistant() -> None:
    class ErrP:
        async def stream_chat(self, messages):
            yield StreamChunk("error", "boom")
            yield StreamChunk("done")

    s = ChatSession(ErrP())
    _ = [c async for c in s.send("x")]
    assert [m.role for m in s.messages] == ["system", "user"]
```

- [ ] **Step 2: 跑测失败**

Run: `uv run pytest tests/test_session.py -v`  
Expected: FAIL

- [ ] **Step 3: 实现 ChatSession**

```python
SYSTEM_PROMPT = (
    "你是 InvestPilot，面向投资研究的个人助手。"
    "回答简洁、有条理。你提供研究辅助信息，不构成投资建议。"
)

class ChatSession:
    def __init__(self, provider: ChatProvider, system_prompt: str = SYSTEM_PROMPT) -> None:
        self._provider = provider
        self._messages: list[Message] = [Message("system", system_prompt)]

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    async def send(self, user_text: str):
        text = user_text.strip()
        if not text:
            return
            yield  # pragma: no cover
        self._messages.append(Message("user", text))
        parts: list[str] = []
        errored = False
        async for chunk in self._provider.stream_chat(self._messages):
            if chunk.kind == "text" and chunk.text:
                parts.append(chunk.text)
            if chunk.kind == "error":
                errored = True
            yield chunk
        if not errored and parts:
            self._messages.append(Message("assistant", "".join(parts)))
```

注意：空输入应直接 return（async generator 可用 `if not text: return` 而不 yield）。

- [ ] **Step 4: 跑测通过**

Run: `uv run pytest tests/test_session.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investpilot/assistant tests/test_session.py
git commit -m "feat: add in-memory multi-turn ChatSession"
```

---

### Task 5: Textual TUI

**Files:**
- Create: `src/investpilot/interface/__init__.py`
- Create: `src/investpilot/interface/tui_app.py`
- Create: `tests/test_tui_helpers.py`（测纯函数：格式化行，不启全屏）
- Modify: 如需从 session 导出小工具函数可放 `tui_app.py`

**Interfaces:**
- Consumes: `ChatSession.send`, `AppConfig` 仅用于标题展示 model/provider（可选）
- Produces:
```python
class InvestPilotApp(App[None]):
    def __init__(self, session: ChatSession, title_suffix: str = "") -> None: ...

def run_tui(session: ChatSession, *, provider: str, model: str) -> None:
    """阻塞运行 Textual app。"""
```
- UI：`Header`、`RichLog` 或 `VerticalScroll`+`Static` 作 transcript、底部 `Input`
- Enter 提交 → `asyncio` worker 调 `session.send`，逐 chunk 写 transcript
- 生成中 `Input.disabled = True`
- `/quit` 退出
- 错误 chunk 用醒目前缀（如 `错误: ...`）

- [ ] **Step 1: 写失败测试（格式化/命令）**

```python
from investpilot.interface.tui_app import is_quit_command, format_user_line, format_assistant_prefix

def test_quit_commands() -> None:
    assert is_quit_command("/quit")
    assert is_quit_command("/exit")
    assert not is_quit_command("hello")

def test_format_lines() -> None:
    assert "你" in format_user_line("hi")
    assert format_assistant_prefix()
```

- [ ] **Step 2: 跑测失败**

Run: `uv run pytest tests/test_tui_helpers.py -v`  
Expected: FAIL

- [ ] **Step 3: 实现 TUI**

实现 `is_quit_command`, `format_user_line`, `format_assistant_prefix`, `InvestPilotApp`, `run_tui`。

最小结构：
- CSS：input dock bottom
- `on_input_submitted`：读 value、清空、若 quit 则 `self.exit()`、否则挂 worker
- worker 内：`async for chunk in session.send(text)` 更新 log

绑定 `ctrl+c` / `ctrl+d` → exit（Textual 默认或显式 BINDINGS）。

- [ ] **Step 4: 跑测通过 + ruff**

Run:
```bash
uv run pytest tests/test_tui_helpers.py tests/test_session.py -v
uv run ruff check src tests
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investpilot/interface tests/test_tui_helpers.py
git commit -m "feat: add Textual chat TUI shell"
```

---

### Task 6: CLI 接通 chat + README

**Files:**
- Modify: `src/investpilot/cli/main.py`
- Create: `tests/test_cli.py`
- Modify: `tests/test_smoke.py`（help 含 chat）
- Modify: `README.md`

**Interfaces:**
- `invest-pilot chat`：`load_config()` → `build_provider` → `ChatSession` → `run_tui`
- `ConfigError` → stderr 中文 + exit 1
- 无 args 时 help 含 `chat` 与 `status`

- [ ] **Step 1: 写 CLI 测试**

```python
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
```

- [ ] **Step 2: 跑测失败（chat 仍占位）**

Run: `uv run pytest tests/test_cli.py -v`  
Expected: FAIL 或 chat 文案不符

- [ ] **Step 3: 实现 chat 命令**

```python
@app.command()
def chat() -> None:
    """启动全屏 TUI 多轮聊天。"""
    from investpilot.assistant.session import ChatSession
    from investpilot.core.config import load_config
    from investpilot.core.errors import ConfigError
    from investpilot.interface.tui_app import run_tui
    from investpilot.providers.factory import build_provider

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    provider = build_provider(cfg)
    session = ChatSession(provider)
    run_tui(session, provider=cfg.provider, model=cfg.model)
```

README 更新安装/运行：
```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml；export ANTHROPIC_AUTH_TOKEN=... 或 OPENAI_API_KEY=...
uv sync
uv run invest-pilot chat
```

- [ ] **Step 4: 全量验证**

Run:
```bash
uv run pytest
uv run ruff check .
uv run invest-pilot status
uv run invest-pilot --help
```
Expected: 全绿；status 显示 v0.2.0

手工（有 key 时）：
```bash
cp config.example.yaml config.yaml
# 配置 key 后
uv run invest-pilot chat
# 连续两轮对话，确认流式与上下文
```

- [ ] **Step 5: Commit**

```bash
git add src/investpilot/cli/main.py tests/test_cli.py tests/test_smoke.py README.md
git commit -m "feat: wire invest-pilot chat to TUI session"
```

---

### Task 7: 收尾验收对照 SPEC

**Files:** 按需修缺陷；不扩 scope

- [ ] **Step 1: 对照 SPEC §9 逐条勾选**

1. chat 启动 TUI  
2. ≥2 轮上下文  
3. 流式  
4. openai/anthropic 可切换（mock 已覆盖 + 可选真机）  
5. pytest + ruff  
6. config.yaml gitignore + example 在库  

- [ ] **Step 2: 全量命令**

```bash
uv run pytest --cov=investpilot --cov-report=term-missing --cov-fail-under=20
uv run ruff check .
```

- [ ] **Step 3: 若有修复则 commit**

```bash
git add -A
git commit -m "fix: close v0.2 acceptance gaps"
```

- [ ] **Step 4: 在交付说明中列出改动文件、验证命令、剩余风险**

---

## Spec coverage checklist（自检）

| SPEC 项 | Task |
|---------|------|
| Textual 全屏 TUI | 5, 6 |
| 多轮内存 history | 4 |
| 流式 | 3, 4, 5 |
| openai + anthropic | 3 |
| config.example + gitignore config.yaml | 1, 2 |
| 不读 ~/.claude/env.d | 2（仅 env + yaml） |
| invest-pilot chat/status | 1, 6 |
| 错误可恢复会话 | 4, 5 |
| pytest/ruff | 各 task + 7 |
| 版本 0.2.0 | 1 |
| 系统提示非投资建议 | 4 |
| MiniMax 默认 URL | 2 |

## Placeholder scan

无 TBD；测试与实现代码均已给出可粘贴骨架。

## Type consistency

- `AppConfig` / `Message` / `StreamChunk` / `ChatProvider.stream_chat` / `ChatSession.send` / `build_provider` / `run_tui` 命名在全文一致。
