# API Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize LLM initialization to use `init_chat_model` for multi-provider support, fix pre-existing test failures, and ensure all langchain/langgraph API usage follows latest patterns.

**Architecture:** Replace hardcoded `ChatOpenAI` instantiation with `langchain.chat_models.init_chat_model` factory which automatically routes to the correct provider (openai, deepseek, anthropic, etc.). Retain `ChatOpenAI` direct usage only for custom `base_url` scenarios where string notation is insufficient.

**Tech Stack:** `langchain.chat_models.init_chat_model`, `langchain.agents.create_agent`, `langchain_openai.ChatOpenAI`, `langgraph.checkpoint.sqlite.aio.AsyncSqliteSaver`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `lc_agent/core/engine.py` | Agent engine with `_create_llm` refactored to use `init_chat_model` |
| `tests/test_engine.py` | Unit tests for engine including `_create_llm` scenarios |
| `tests/test_runtime.py` | Integration tests for `build_agent` with mocked LLM |
| `tests/conftest.py` | Shared fixtures |

---

### Task 1: Fix pre-existing test failure in test_engine.py

**Files:**
- Modify: `tests/test_engine.py:67-73`

- [ ] **Step 1: Fix the outdated assertion**

The test asserts `preset.id == "__default__"` but the engine now returns `"__chat__"` as the default preset ID.

```python
def test_get_default_preset(self, sample_config):
    from lc_agent.core.engine import AgentEngine
    engine = AgentEngine(sample_config)
    preset = engine.get_default_preset()
    assert preset.id == "__chat__"
    assert preset.system_prompt == "You are a helpful assistant. Respond in the user's language."
    assert preset.default_model == "test-model"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py::TestAgentEngine::test_get_default_preset -v`
Expected: PASS

---

### Task 2: Write failing tests for `_create_llm` with `init_chat_model`

**Files:**
- Modify: `tests/test_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
class TestCreateLlm:
    """Test _create_llm method with init_chat_model integration."""

    def test_creates_llm_with_base_url_uses_chatopenai(self, sample_config):
        """When base_url is set, should use ChatOpenAI directly for compatibility."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo

        engine = AgentEngine(sample_config)
        model_info = ModelInfo(
            id="deepseek-chat",
            provider="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key="test-key",
        )
        llm = engine._create_llm(model_info, "deepseek-chat")
        assert llm.model_name == "deepseek-chat"
        assert llm.openai_api_base == "https://api.deepseek.com/v1"

    def test_creates_llm_without_base_url_uses_init_chat_model(self, sample_config):
        """When no base_url, should use init_chat_model for provider routing."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo

        engine = AgentEngine(sample_config)
        model_info = ModelInfo(
            id="deepseek-chat",
            provider="deepseek",
            base_url="",
            api_key="test-key",
        )
        llm = engine._create_llm(model_info, "deepseek-chat")
        assert llm is not None
        assert hasattr(llm, 'ainvoke')

    def test_creates_llm_fallback_when_no_model_info(self, sample_config):
        """When model_info is None, should create ChatOpenAI with model_id."""
        from lc_agent.core.engine import AgentEngine

        engine = AgentEngine(sample_config)
        llm = engine._create_llm(None, "gpt-4o")
        assert llm is not None
        assert hasattr(llm, 'ainvoke')

    def test_creates_llm_passes_temperature(self, sample_config):
        """LLM should be configured with temperature=0.7."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo

        engine = AgentEngine(sample_config)
        model_info = ModelInfo(
            id="gpt-4o",
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )
        llm = engine._create_llm(model_info, "gpt-4o")
        assert llm.temperature == 0.7

    def test_creates_llm_enables_stream_usage(self, sample_config):
        """LLM should have stream_usage=True for token tracking."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo

        engine = AgentEngine(sample_config)
        model_info = ModelInfo(
            id="gpt-4o",
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )
        llm = engine._create_llm(model_info, "gpt-4o")
        assert llm.stream_usage is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py::TestCreateLlm -v`
Expected: `test_creates_llm_without_base_url_uses_init_chat_model` FAILS (currently all use ChatOpenAI)

---

### Task 3: Implement `_create_llm` with `init_chat_model`

**Files:**
- Modify: `lc_agent/core/engine.py:133-145`

- [ ] **Step 1: Implement the updated `_create_llm`**

```python
def _create_llm(self, model_info: ModelInfo | None, model_id: str):
    """Create a chat model instance from model info.

    Uses ChatOpenAI directly when base_url is set (custom/compatible endpoints).
    Uses init_chat_model for standard providers (handles provider routing).
    """
    if model_info and model_info.base_url:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_info.id,
            base_url=model_info.base_url,
            api_key=model_info.api_key or "not-set",
            temperature=0.7,
            stream_usage=True,
        )

    from langchain.chat_models import init_chat_model

    if model_info:
        model_str = f"{model_info.provider}:{model_info.id}" if model_info.provider else model_info.id
        return init_chat_model(
            model_str,
            api_key=model_info.api_key or "not-set",
            temperature=0.7,
            stream_usage=True,
        )

    return init_chat_model(model_id, api_key="not-set", temperature=0.7, stream_usage=True)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py::TestCreateLlm -v`
Expected: ALL PASS

---

### Task 4: Fix test_runtime.py mock test

**Files:**
- Modify: `tests/test_runtime.py:41-60`

- [ ] **Step 1: Fix the mock to work with _get_or_build_agent**

The test injects a mock into `_agents["__default__"]` but `_get_or_build_agent` uses preset resolution which maps to different IDs. Fix by using the correct preset ID.

```python
@pytest.mark.asyncio
async def test_chat_stream_yields_events(engine_with_provider):
    """chat_stream should yield astream_events from the agent."""
    from unittest.mock import MagicMock, AsyncMock

    mock_agent = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="hello")}}
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content=" world")}}

    mock_agent.astream_events = fake_stream
    engine_with_provider._agents["__chat__"] = mock_agent
    engine_with_provider._agent_mcp_gen["__chat__"] = engine_with_provider._mcp_generation

    events = []
    async for event in engine_with_provider.chat_stream("test", "thread-1"):
        events.append(event)

    assert len(events) == 2
    assert events[0]["data"]["chunk"].content == "hello"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_runtime.py::test_chat_stream_yields_events -v`
Expected: PASS

---

### Task 5: Run full test suite and verify

- [ ] **Step 1: Run all tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py tests/test_runtime.py -v`
Expected: ALL PASS

- [ ] **Step 2: Run broader test suite**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -v --tb=short`
Expected: No new failures

---

### Task 6: Update documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-06-11-lc-agent-project-design.md`
- Modify: `docs/superpowers/specs/2026-06-11-phase5-agent-runtime-design.md`

- [ ] **Step 1: Update project design doc**

Update the architecture description to mention multi-provider support via `init_chat_model`.

- [ ] **Step 2: Update runtime design doc**

Update the LLM Initialization section to show `init_chat_model` usage.
