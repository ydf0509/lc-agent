# lc_agent Phase 1: Backend Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal but functional lc_agent framework where a user can `pip install`, write 5 lines of code, and have a working Agent with WebSocket streaming and a FastAPI backend.

**Architecture:** LangChain `create_agent()` + LangGraph as the core engine, wrapped in a `LcAgentApp` class that auto-starts a FastAPI server with WebSocket chat. Config system uses JSONC (matching nb_agent convention). Tools register via `@tool` decorator with group support.

**Tech Stack:** Python 3.12, LangChain v1+, LangGraph, FastAPI, SQLModel, uvicorn, commentjson, pytest, pytest-asyncio

---

## File Structure

```
lc_agent/
├── __init__.py              # Public API: load_config, LcAgentApp
├── __main__.py              # python -m lc_agent
├── config/
│   ├── __init__.py
│   ├── loader.py            # JSONC + env substitution
│   └── schema.py            # Pydantic config models
├── tools/
│   ├── __init__.py
│   ├── registry.py          # @tool decorator + ToolRegistry
│   └── builtin.py           # get_current_time builtin
├── core/
│   ├── __init__.py
│   ├── engine.py            # AgentEngine wrapping create_agent
│   └── models.py            # AgentPreset, ModelInfo
├── server/
│   ├── __init__.py
│   ├── app.py               # FastAPI app factory
│   ├── websocket.py         # WebSocket chat handler
│   └── routes/
│       ├── __init__.py
│       └── health.py        # GET /api/health
└── app.py                   # LcAgentApp orchestrator

tests/
├── conftest.py              # Shared fixtures
├── test_config.py           # Config loading tests
├── test_tools.py            # Tool registry tests
├── test_engine.py           # AgentEngine tests
└── test_server.py           # FastAPI endpoint tests

pyproject.toml               # Package metadata + dependencies
config.example.jsonc         # Reference configuration
```

---

### Task 1: Project Scaffolding + pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `lc_agent/__init__.py`
- Create: `lc_agent/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "lc-agent"
version = "0.1.0"
description = "LangChain Agent framework with built-in Web UI"
requires-python = ">=3.12"
license = "MIT"
dependencies = [
    "langchain>=1.0",
    "langgraph>=0.4",
    "langchain-openai",
    "langchain-deepseek",
    "fastapi>=0.115",
    "uvicorn[standard]",
    "sqlmodel>=0.0.22",
    "aiosqlite",
    "python-dotenv",
    "commentjson",
    "websockets",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx",
    "ruff",
]

[project.scripts]
lc-agent = "lc_agent.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 120
```

- [ ] **Step 2: Create minimal lc_agent/__init__.py**

```python
"""lc_agent - LangChain Agent framework with built-in Web UI."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create lc_agent/__main__.py**

```python
from lc_agent.main import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create tests/__init__.py and tests/conftest.py**

`tests/__init__.py`: empty file

```python
# tests/conftest.py
import pytest


@pytest.fixture
def sample_config() -> dict:
    """Minimal valid configuration for testing."""
    return {
        "provider": {
            "default": {
                "api_key": "test-key",
                "base_url": "https://api.example.com/v1",
                "models": [{"id": "test-model", "context_limit": 8000}],
            }
        },
        "agent": {
            "system_prompt": "You are a helpful assistant.",
            "default_model": "test-model",
            "streaming": True,
        },
        "mcp": {},
        "session": {"db_path": ":memory:"},
    }
```

- [ ] **Step 5: Install dev dependencies and verify**

Run: `pip install -e ".[dev]"`
Expected: Successful install, all dependencies resolved

- [ ] **Step 6: Run pytest to verify empty test suite works**

Run: `pytest --co -q`
Expected: "no tests ran" (0 collected, no errors)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml lc_agent/__init__.py lc_agent/__main__.py tests/__init__.py tests/conftest.py
git commit -m "feat: project scaffolding with pyproject.toml and test setup"
```

---

### Task 2: Config System (JSONC Loader + Schema)

**Files:**
- Create: `lc_agent/config/__init__.py`
- Create: `lc_agent/config/loader.py`
- Create: `lc_agent/config/schema.py`
- Create: `config.example.jsonc`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config loading**

```python
# tests/test_config.py
import os
import tempfile
from pathlib import Path

import pytest

from lc_agent.config.loader import load_config_from_file, substitute_env_vars
from lc_agent.config.schema import AppConfig


class TestSubstituteEnvVars:
    def test_replaces_env_var(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-12345")
        result = substitute_env_vars({"key": "{env:TEST_API_KEY}"})
        assert result == {"key": "sk-12345"}

    def test_leaves_non_env_strings_unchanged(self):
        result = substitute_env_vars({"key": "plain-value"})
        assert result == {"key": "plain-value"}

    def test_handles_nested_dicts(self, monkeypatch):
        monkeypatch.setenv("NESTED_VAL", "secret")
        data = {"outer": {"inner": "{env:NESTED_VAL}"}}
        result = substitute_env_vars(data)
        assert result == {"outer": {"inner": "secret"}}

    def test_handles_lists(self, monkeypatch):
        monkeypatch.setenv("LIST_VAL", "item")
        data = {"items": ["{env:LIST_VAL}", "static"]}
        result = substitute_env_vars(data)
        assert result == {"items": ["item", "static"]}

    def test_missing_env_var_raises(self):
        with pytest.raises(ValueError, match="Environment variable 'NONEXISTENT' not found"):
            substitute_env_vars({"key": "{env:NONEXISTENT}"})


class TestLoadConfigFromFile:
    def test_loads_jsonc_file(self, tmp_path):
        config_file = tmp_path / "config.jsonc"
        config_file.write_text(
            """{
            // This is a comment
            "agent": {
                "system_prompt": "Hello",
                "default_model": "test-model",
                "streaming": true
            },
            "provider": {
                "default": {
                    "api_key": "sk-test",
                    "base_url": "https://api.example.com/v1",
                    "models": [{"id": "test-model", "context_limit": 8000}]
                }
            },
            "mcp": {},
            "session": {"db_path": ":memory:"}
        }"""
        )
        config = load_config_from_file(str(config_file))
        assert config["agent"]["system_prompt"] == "Hello"

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/nonexistent/path/config.jsonc")


class TestAppConfig:
    def test_validates_minimal_config(self):
        config = AppConfig(
            provider={"default": {"api_key": "sk-test", "base_url": "https://api.example.com/v1", "models": [{"id": "m1", "context_limit": 4000}]}},
            agent={"system_prompt": "Hi", "default_model": "m1", "streaming": True},
        )
        assert config.agent["default_model"] == "m1"

    def test_rejects_missing_agent_section(self):
        with pytest.raises(Exception):
            AppConfig(provider={"default": {}})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with ModuleNotFoundError (lc_agent.config.loader not found)

- [ ] **Step 3: Implement config/schema.py**

```python
# lc_agent/config/schema.py
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    id: str
    context_limit: int = 8000


class ProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    models: list[ModelConfig] = Field(default_factory=list)


class AppConfig(BaseModel):
    """Application configuration schema."""

    provider: dict[str, ProviderConfig | dict] = Field(default_factory=dict)
    agent: dict = Field(default_factory=lambda: {
        "system_prompt": "You are a helpful assistant.",
        "default_model": "",
        "streaming": True,
    })
    mcp: dict = Field(default_factory=dict)
    session: dict = Field(default_factory=lambda: {"db_path": ""})
    ui: dict = Field(default_factory=dict)
```

- [ ] **Step 4: Implement config/loader.py**

```python
# lc_agent/config/loader.py
import os
import re
from pathlib import Path
from typing import Any

import commentjson
from dotenv import load_dotenv

ENV_PATTERN = re.compile(r"\{env:([^}]+)\}")


def substitute_env_vars(data: Any) -> Any:
    """Recursively replace {env:VAR_NAME} patterns with environment variable values."""
    if isinstance(data, str):
        match = ENV_PATTERN.fullmatch(data)
        if match:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value
        def replacer(m):
            var_name = m.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value
        return ENV_PATTERN.sub(replacer, data)
    elif isinstance(data, dict):
        return {k: substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_env_vars(item) for item in data]
    return data


def load_config_from_file(path: str) -> dict:
    """Load a JSONC configuration file and apply env substitution."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw = commentjson.load(f)

    return substitute_env_vars(raw)


def load_config(
    config_path: str | None = None,
    dotenv_path: str | None = None,
) -> dict:
    """Load configuration with priority: explicit path > ./config.jsonc > ~/.lc_agent/config.jsonc > defaults."""
    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.append(Path.cwd() / "config.jsonc")
    search_paths.append(Path.home() / ".lc_agent" / "config.jsonc")

    for p in search_paths:
        if p.exists():
            config = load_config_from_file(str(p))
            config["_config_path"] = str(p)
            config["_project_root"] = str(p.parent)
            return config

    return {
        "provider": {},
        "agent": {
            "system_prompt": "You are a helpful assistant.",
            "default_model": "",
            "streaming": True,
        },
        "mcp": {},
        "session": {"db_path": ""},
        "_config_path": None,
        "_project_root": str(Path.cwd()),
    }
```

- [ ] **Step 5: Create config/__init__.py**

```python
# lc_agent/config/__init__.py
from lc_agent.config.loader import load_config, load_config_from_file, substitute_env_vars

__all__ = ["load_config", "load_config_from_file", "substitute_env_vars"]
```

- [ ] **Step 6: Create config.example.jsonc**

```jsonc
{
    // lc_agent 配置文件
    "provider": {
        "default": {
            "api_key": "{env:LLM_API_KEY}",
            "base_url": "https://api.deepseek.com/v1",
            "models": [
                {"id": "deepseek-chat", "context_limit": 64000},
                {"id": "deepseek-reasoner", "context_limit": 64000}
            ]
        }
    },
    "agent": {
        "system_prompt": "你是一个智能助手。请用中文回答。",
        "default_model": "deepseek-chat",
        "streaming": true
    },
    "mcp": {
        // MCP服务器配置
    },
    "session": {
        "db_path": ""  // 留空则使用 ~/.lc_agent/sessions.db
    }
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add lc_agent/config/ config.example.jsonc tests/test_config.py
git commit -m "feat: config system with JSONC loading and env substitution"
```

---

### Task 3: Tool Registry with @tool Decorator and Groups

**Files:**
- Create: `lc_agent/tools/__init__.py`
- Create: `lc_agent/tools/registry.py`
- Create: `lc_agent/tools/builtin.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests for tool registry**

```python
# tests/test_tools.py
import pytest

from lc_agent.tools.registry import ToolRegistry, tool


class TestToolDecorator:
    def setup_method(self):
        """Reset global registry before each test."""
        ToolRegistry._instance = None
        ToolRegistry._global_tools = {}

    def test_registers_function_as_tool(self):
        @tool
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}"

        registry = ToolRegistry()
        tools = registry.get_all_tools()
        assert "greet" in [t.name for t in tools]

    def test_registers_with_group(self):
        @tool(group="utils")
        def get_time() -> str:
            """Get current time."""
            return "12:00"

        registry = ToolRegistry()
        tools = registry.get_all_tools()
        tool_names = [t.name for t in tools]
        assert "utils__get_time" in tool_names

    def test_tool_is_callable(self):
        @tool
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        assert add(2, 3) == 5

    def test_get_tools_by_group(self):
        @tool(group="math")
        def add(a: int, b: int) -> int:
            """Add."""
            return a + b

        @tool(group="math")
        def sub(a: int, b: int) -> int:
            """Subtract."""
            return a - b

        @tool(group="text")
        def upper(s: str) -> str:
            """Uppercase."""
            return s.upper()

        registry = ToolRegistry()
        math_tools = registry.get_tools_by_groups(["math"])
        assert len(math_tools) == 2

    def test_filter_by_allowed_groups_none_returns_all(self):
        @tool(group="a")
        def fa() -> str:
            """A."""
            return "a"

        @tool(group="b")
        def fb() -> str:
            """B."""
            return "b"

        registry = ToolRegistry()
        filtered = registry.get_filtered_tools(allowed_groups=None)
        assert len(filtered) == 2

    def test_filter_by_allowed_groups_empty_returns_none(self):
        @tool(group="a")
        def fc() -> str:
            """A."""
            return "a"

        registry = ToolRegistry()
        filtered = registry.get_filtered_tools(allowed_groups=[])
        assert len(filtered) == 0

    def test_get_group_names(self):
        @tool(group="alpha")
        def fx() -> str:
            """X."""
            return "x"

        @tool(group="beta")
        def fy() -> str:
            """Y."""
            return "y"

        registry = ToolRegistry()
        groups = registry.get_group_names()
        assert "alpha" in groups
        assert "beta" in groups
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement tools/registry.py**

```python
# lc_agent/tools/registry.py
from __future__ import annotations

import functools
from typing import Any, Callable, overload

from langchain.tools import tool as langchain_tool
from langchain_core.tools import BaseTool


class ToolRegistry:
    """Central registry for all tools, supporting groups and filtering."""

    _instance: ToolRegistry | None = None
    _global_tools: dict[str, dict[str, Any]] = {}

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_all_tools(self) -> list[BaseTool]:
        """Return all registered tools as LangChain BaseTool instances."""
        return [entry["tool"] for entry in self._global_tools.values()]

    def get_tools_by_groups(self, groups: list[str]) -> list[BaseTool]:
        """Return tools belonging to specified groups."""
        return [
            entry["tool"]
            for entry in self._global_tools.values()
            if entry["group"] in groups
        ]

    def get_filtered_tools(self, allowed_groups: list[str] | None) -> list[BaseTool]:
        """Filter tools by allowed groups (three-value semantics).

        None = all allowed, [] = none allowed, ["a","b"] = only those groups.
        """
        if allowed_groups is None:
            return self.get_all_tools()
        if not allowed_groups:
            return []
        return self.get_tools_by_groups(allowed_groups)

    def get_group_names(self) -> list[str]:
        """Return unique list of all registered group names."""
        groups = set()
        for entry in self._global_tools.values():
            if entry["group"]:
                groups.add(entry["group"])
        return sorted(groups)

    def register(self, func: Callable, group: str = "") -> BaseTool:
        """Register a function as a tool."""
        name = f"{group}__{func.__name__}" if group else func.__name__
        lc_tool = langchain_tool(func)
        lc_tool.name = name
        self._global_tools[name] = {"tool": lc_tool, "group": group, "func": func}
        return lc_tool


@overload
def tool(func: Callable) -> Callable: ...

@overload
def tool(*, group: str = "") -> Callable[[Callable], Callable]: ...

def tool(func: Callable | None = None, *, group: str = ""):
    """Decorator to register a function as an agent tool.

    Usage:
        @tool
        def my_func(...): ...

        @tool(group="utils")
        def my_func(...): ...
    """
    registry = ToolRegistry()

    def decorator(fn: Callable) -> Callable:
        registry.register(fn, group=group)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
```

- [ ] **Step 4: Create tools/__init__.py**

```python
# lc_agent/tools/__init__.py
from lc_agent.tools.registry import ToolRegistry, tool

__all__ = ["ToolRegistry", "tool"]
```

- [ ] **Step 5: Create tools/builtin.py**

```python
# lc_agent/tools/builtin.py
from datetime import datetime

from lc_agent.tools.registry import tool


@tool(group="builtin")
def get_current_time() -> str:
    """获取当前日期和时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_tools.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add lc_agent/tools/ tests/test_tools.py
git commit -m "feat: tool registry with @tool decorator and group support"
```

---

### Task 4: Core Engine (AgentEngine wrapping create_agent)

**Files:**
- Create: `lc_agent/core/__init__.py`
- Create: `lc_agent/core/models.py`
- Create: `lc_agent/core/engine.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write failing tests for core models and engine**

```python
# tests/test_engine.py
import pytest

from lc_agent.core.models import AgentPreset, ModelInfo


class TestAgentPreset:
    def test_creates_with_defaults(self):
        preset = AgentPreset(
            id="default",
            name="Default Agent",
            system_prompt="Hello",
            default_model="test-model",
        )
        assert preset.allowed_tool_groups is None
        assert preset.allowed_mcp_servers is None
        assert preset.allowed_skills is None
        assert preset.dangerous_tools == []

    def test_three_value_semantics_none_means_all(self):
        preset = AgentPreset(
            id="all", name="All", system_prompt="", default_model="m"
        )
        assert preset.allowed_tool_groups is None  # All allowed

    def test_three_value_semantics_empty_means_none(self):
        preset = AgentPreset(
            id="none", name="None", system_prompt="", default_model="m",
            allowed_tool_groups=[],
        )
        assert preset.allowed_tool_groups == []  # None allowed

    def test_three_value_semantics_list_means_only_those(self):
        preset = AgentPreset(
            id="some", name="Some", system_prompt="", default_model="m",
            allowed_tool_groups=["math", "text"],
        )
        assert preset.allowed_tool_groups == ["math", "text"]


class TestModelInfo:
    def test_creates_model_info(self):
        info = ModelInfo(
            id="deepseek-chat",
            provider="default",
            base_url="https://api.deepseek.com/v1",
            context_limit=64000,
        )
        assert info.id == "deepseek-chat"
        assert info.context_limit == 64000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement core/models.py**

```python
# lc_agent/core/models.py
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """LLM model metadata."""

    id: str
    provider: str
    base_url: str
    context_limit: int = 8000
    api_key: str = ""


class AgentPreset(BaseModel):
    """Agent preset configuration (three-value semantics from nb_agent).

    For allowed_* fields:
      None  = all allowed (default)
      []    = all disabled
      ["a"] = only specified items allowed
    """

    id: str
    name: str
    system_prompt: str
    default_model: str

    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None

    dangerous_tools: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Create core/__init__.py**

```python
# lc_agent/core/__init__.py
from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset, ModelInfo

__all__ = ["AgentEngine", "AgentPreset", "ModelInfo"]
```

- [ ] **Step 5: Implement core/engine.py (minimal, testable)**

```python
# lc_agent/core/engine.py
from __future__ import annotations

from typing import Any, AsyncIterator

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

from lc_agent.config.loader import load_config
from lc_agent.core.models import AgentPreset, ModelInfo
from lc_agent.tools.registry import ToolRegistry


class AgentEngine:
    """Core agent engine wrapping LangChain create_agent with middleware support."""

    def __init__(self, config: dict):
        self.config = config
        self.tool_registry = ToolRegistry()
        self._checkpointer = InMemorySaver()
        self._agents: dict[str, Any] = {}
        self._current_preset: AgentPreset | None = None
        self._models: list[ModelInfo] = self._parse_models(config)

    def _parse_models(self, config: dict) -> list[ModelInfo]:
        """Extract ModelInfo list from config."""
        models = []
        for provider_name, provider_conf in config.get("provider", {}).items():
            if isinstance(provider_conf, dict):
                for model_conf in provider_conf.get("models", []):
                    models.append(ModelInfo(
                        id=model_conf["id"],
                        provider=provider_name,
                        base_url=provider_conf.get("base_url", ""),
                        context_limit=model_conf.get("context_limit", 8000),
                        api_key=provider_conf.get("api_key", ""),
                    ))
        return models

    def get_models(self) -> list[ModelInfo]:
        """Return available models."""
        return self._models

    def get_default_preset(self) -> AgentPreset:
        """Create default preset from config."""
        agent_conf = self.config.get("agent", {})
        return AgentPreset(
            id="__default__",
            name="Default Agent",
            system_prompt=agent_conf.get("system_prompt", "You are a helpful assistant."),
            default_model=agent_conf.get("default_model", ""),
        )

    def build_agent(self, preset: AgentPreset | None = None):
        """Build a LangGraph agent from preset."""
        if preset is None:
            preset = self.get_default_preset()
        self._current_preset = preset

        tools = self.tool_registry.get_filtered_tools(preset.allowed_tool_groups)

        model_info = self._find_model(preset.default_model)
        model_str = f"openai:{preset.default_model}"

        agent = create_agent(
            model=model_str,
            tools=tools,
            system_prompt=preset.system_prompt,
            interrupt_on=preset.dangerous_tools or None,
            checkpointer=self._checkpointer,
        )
        self._agents[preset.id] = agent
        return agent

    def _find_model(self, model_id: str) -> ModelInfo | None:
        """Find model info by ID."""
        for m in self._models:
            if m.id == model_id:
                return m
        return None

    async def chat(self, message: str, thread_id: str, preset_id: str = "__default__") -> str:
        """Send a message and get a response (non-streaming)."""
        agent = self._agents.get(preset_id)
        if agent is None:
            agent = self.build_agent(self._current_preset or self.get_default_preset())

        config = {"configurable": {"thread_id": thread_id}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""

    async def chat_stream(self, message: str, thread_id: str) -> AsyncIterator[dict]:
        """Stream chat responses as events."""
        agent = self._agents.get("__default__")
        if agent is None:
            agent = self.build_agent()

        config = {"configurable": {"thread_id": thread_id}}
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            version="v2",
        ):
            yield event
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_engine.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add lc_agent/core/ tests/test_engine.py
git commit -m "feat: AgentEngine with create_agent wrapper and preset support"
```

---

### Task 5: FastAPI Server + WebSocket Chat

**Files:**
- Create: `lc_agent/server/__init__.py`
- Create: `lc_agent/server/app.py`
- Create: `lc_agent/server/websocket.py`
- Create: `lc_agent/server/routes/__init__.py`
- Create: `lc_agent/server/routes/health.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write failing tests for FastAPI server**

```python
# tests/test_server.py
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.server.app import create_app


@pytest.fixture
def app(sample_config):
    return create_app(sample_config)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    async def test_health_includes_config_status(self, client):
        response = await client.get("/api/health")
        data = response.json()
        assert "config_loaded" in data


class TestCORS:
    async def test_cors_headers_present(self, client):
        response = await client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_server.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement server/app.py**

```python
# lc_agent/server/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lc_agent import __version__
from lc_agent.server.routes.health import router as health_router


def create_app(config: dict) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="lc_agent",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.config = config

    app.include_router(health_router, prefix="/api")

    return app
```

- [ ] **Step 4: Implement server/routes/health.py**

```python
# lc_agent/server/routes/health.py
from fastapi import APIRouter, Request

from lc_agent import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    """Health check endpoint."""
    config = request.app.state.config
    return {
        "status": "ok",
        "version": __version__,
        "config_loaded": config.get("_config_path") is not None,
    }
```

- [ ] **Step 5: Create server/__init__.py and server/routes/__init__.py**

```python
# lc_agent/server/__init__.py
from lc_agent.server.app import create_app

__all__ = ["create_app"]
```

```python
# lc_agent/server/routes/__init__.py
```

- [ ] **Step 6: Implement server/websocket.py (basic structure)**

```python
# lc_agent/server/websocket.py
import json
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from lc_agent.core.engine import AgentEngine


class ChatWebSocketHandler:
    """Handles WebSocket connections for streaming chat."""

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, thread_id: str | None = None):
        """Accept WebSocket connection."""
        await websocket.accept()
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        self.active_connections[thread_id] = websocket
        await websocket.send_json({"type": "connected", "thread_id": thread_id})
        return thread_id

    async def disconnect(self, thread_id: str):
        """Clean up on disconnect."""
        self.active_connections.pop(thread_id, None)

    async def handle_message(self, websocket: WebSocket, thread_id: str, data: dict):
        """Process incoming message and stream response."""
        msg_type = data.get("type", "message")

        if msg_type == "message":
            content = data.get("content", "")
            try:
                async for event in self.engine.chat_stream(content, thread_id):
                    await self._send_event(websocket, event)
                await websocket.send_json({"type": "done"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

        elif msg_type == "interrupt_response":
            decision = data.get("decision", {})
            await websocket.send_json({"type": "ack", "message": "interrupt handled"})

    async def _send_event(self, websocket: WebSocket, event: dict):
        """Convert LangGraph stream event to client-friendly format."""
        kind = event.get("event", "")
        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                await websocket.send_json({"type": "token", "content": chunk.content})
        elif kind == "on_tool_start":
            await websocket.send_json({
                "type": "tool_call",
                "name": event.get("name", ""),
                "run_id": event.get("run_id", ""),
            })
        elif kind == "on_tool_end":
            output = event.get("data", {}).get("output", "")
            await websocket.send_json({
                "type": "tool_result",
                "name": event.get("name", ""),
                "result": str(output)[:2000],
            })
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_server.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add lc_agent/server/ tests/test_server.py
git commit -m "feat: FastAPI server with health endpoint and WebSocket handler"
```

---

### Task 6: LcAgentApp Orchestrator + CLI Entry

**Files:**
- Create: `lc_agent/app.py`
- Create: `lc_agent/main.py`
- Modify: `lc_agent/__init__.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing tests for LcAgentApp**

```python
# tests/test_app.py
import pytest

from lc_agent.app import LcAgentApp


class TestLcAgentApp:
    def test_creates_with_config(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.config == sample_config

    def test_has_fastapi_app(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.fastapi_app is not None

    def test_has_engine(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.engine is not None

    def test_default_host_and_port(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.host == "127.0.0.1"
        assert app.port == 8000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_app.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement lc_agent/app.py**

```python
# lc_agent/app.py
from __future__ import annotations

import uvicorn
from fastapi import WebSocket, WebSocketDisconnect

from lc_agent.core.engine import AgentEngine
from lc_agent.server.app import create_app
from lc_agent.server.websocket import ChatWebSocketHandler


class LcAgentApp:
    """Main application orchestrator — creates engine, server, and runs."""

    def __init__(self, config: dict, host: str = "127.0.0.1", port: int = 8000):
        self.config = config
        self.host = host
        self.port = port
        self.engine = AgentEngine(config)
        self.fastapi_app = create_app(config)
        self._ws_handler = ChatWebSocketHandler(self.engine)
        self._setup_websocket_route()

    def _setup_websocket_route(self):
        @self.fastapi_app.websocket("/ws/chat/{thread_id}")
        async def websocket_chat(websocket: WebSocket, thread_id: str):
            tid = await self._ws_handler.connect(websocket, thread_id)
            try:
                while True:
                    data = await websocket.receive_json()
                    await self._ws_handler.handle_message(websocket, tid, data)
            except WebSocketDisconnect:
                await self._ws_handler.disconnect(tid)

        @self.fastapi_app.websocket("/ws/chat")
        async def websocket_chat_auto(websocket: WebSocket):
            tid = await self._ws_handler.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_json()
                    await self._ws_handler.handle_message(websocket, tid, data)
            except WebSocketDisconnect:
                await self._ws_handler.disconnect(tid)

    def run(self):
        """Start the server (blocking)."""
        print(f"\n  lc_agent v{self.config.get('_version', '0.1.0')}")
        print(f"  Web UI: http://{self.host}:{self.port}")
        print(f"  API Docs: http://{self.host}:{self.port}/api/docs\n")
        uvicorn.run(self.fastapi_app, host=self.host, port=self.port)
```

- [ ] **Step 4: Implement lc_agent/main.py (CLI entry)**

```python
# lc_agent/main.py
import argparse

from lc_agent.config.loader import load_config


def main():
    parser = argparse.ArgumentParser(description="lc_agent - LangChain Agent with Web UI")
    parser.add_argument("--config", "-c", help="Path to config.jsonc")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--dotenv", help="Path to .env file")
    args = parser.parse_args()

    config = load_config(config_path=args.config, dotenv_path=args.dotenv)

    from lc_agent.app import LcAgentApp

    app = LcAgentApp(config, host=args.host, port=args.port)
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Update lc_agent/__init__.py with public exports**

```python
# lc_agent/__init__.py
"""lc_agent - LangChain Agent framework with built-in Web UI."""

__version__ = "0.1.0"

from lc_agent.app import LcAgentApp
from lc_agent.config.loader import load_config
from lc_agent.tools.registry import ToolRegistry, tool

__all__ = ["LcAgentApp", "load_config", "ToolRegistry", "tool", "__version__"]
```

- [ ] **Step 6: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add lc_agent/app.py lc_agent/main.py lc_agent/__init__.py tests/test_app.py
git commit -m "feat: LcAgentApp orchestrator with CLI entry point"
```

---

### Task 7: Integration Test — End-to-End Smoke Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""End-to-end integration test for lc_agent framework."""
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent import LcAgentApp, load_config, tool
from lc_agent.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry between tests."""
    ToolRegistry._instance = None
    ToolRegistry._global_tools = {}
    yield


@pytest.fixture
def config(sample_config):
    return sample_config


@pytest.fixture
def lc_app(config):
    """Create LcAgentApp instance."""
    @tool(group="math")
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @tool(group="text")
    def reverse(text: str) -> str:
        """Reverse a string."""
        return text[::-1]

    return LcAgentApp(config)


class TestIntegration:
    async def test_app_starts_and_health_works(self, lc_app):
        transport = ASGITransport(app=lc_app.fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_tools_registered(self, lc_app):
        tools = lc_app.engine.tool_registry.get_all_tools()
        tool_names = [t.name for t in tools]
        assert "math__add" in tool_names
        assert "text__reverse" in tool_names

    def test_engine_has_models(self, lc_app):
        models = lc_app.engine.get_models()
        assert len(models) > 0
        assert models[0].id == "test-model"

    def test_default_preset(self, lc_app):
        preset = lc_app.engine.get_default_preset()
        assert preset.system_prompt == "You are a helpful assistant."
        assert preset.default_model == "test-model"
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: All tests PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for end-to-end smoke testing"
```

---

## Summary

After completing all 7 tasks, you will have:
- A working Python package (`lc-agent`) installable via pip
- Config system with JSONC + env variable support
- Tool registry with `@tool(group="xxx")` decorator
- AgentEngine wrapping LangChain `create_agent()` with LangGraph
- FastAPI server with health endpoint + WebSocket chat route
- `LcAgentApp` one-line launcher
- Full test coverage for all components

**Next:** Phase 2 will add the Vue frontend, and Phase 3 will add the full Agent management CRUD + Skills/MCP systems.
