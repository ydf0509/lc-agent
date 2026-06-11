# Phase 5d: User Code Agent Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow developers to register pre-built `CompiledStateGraph` agents via `app.add_agent(name, graph)`. These agents appear in the frontend's agent selector and can be used for chat.

**Architecture:** `LcAgentApp` gains a `_custom_agents` dict storing user-registered graphs. The `/api/agents` endpoint includes them with `source: "code"`. When selected, the WebSocket handler uses the pre-built graph directly instead of calling `build_agent`.

**Tech Stack:** `langgraph.graph.state.CompiledStateGraph`, FastAPI, Pinia

---

## File Structure

| File | Responsibility |
|------|---------------|
| `lc_agent/app.py` | `add_agent()` method |
| `lc_agent/core/engine.py` | Store + retrieve custom agents |
| `lc_agent/server/routes/agents.py` | Include custom agents in list |
| `tests/test_custom_agents.py` | Test registration and retrieval |

---

### Task 1: Implement add_agent on LcAgentApp

**Files:**
- Modify: `lc_agent/app.py`
- Create: `tests/test_custom_agents.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_custom_agents.py
import pytest
from unittest.mock import MagicMock
from lc_agent.app import LcAgentApp


@pytest.fixture
def app_instance():
    config = {
        "provider": {},
        "agent": {"system_prompt": "Hi", "default_model": ""},
    }
    return LcAgentApp(config)


def test_add_agent_registers_custom(app_instance):
    """add_agent should store the graph and create a preset."""
    mock_graph = MagicMock()
    mock_graph.ainvoke = MagicMock()
    mock_graph.astream_events = MagicMock()

    app_instance.add_agent("my_agent", mock_graph, description="My custom agent")

    # Should be accessible via engine
    assert "my_agent" in app_instance.engine._agents
    assert app_instance.engine._agents["my_agent"] is mock_graph


def test_add_agent_creates_preset(app_instance):
    """add_agent should create a preset with source=code."""
    mock_graph = MagicMock()
    app_instance.add_agent("code_agent", mock_graph, description="Code agent")

    presets = app_instance.engine.get_presets()
    code_presets = [p for p in presets if p.id == "code_agent"]
    assert len(code_presets) == 1
    assert code_presets[0].name == "code_agent"


def test_add_agent_duplicate_raises(app_instance):
    """Adding same name twice should raise ValueError."""
    mock_graph = MagicMock()
    app_instance.add_agent("dup", mock_graph)

    with pytest.raises(ValueError, match="already registered"):
        app_instance.add_agent("dup", mock_graph)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_custom_agents.py -v`
Expected: FAIL (LcAgentApp has no `add_agent` method)

- [ ] **Step 3: Implement add_agent**

In `lc_agent/app.py`, add the method to `LcAgentApp` class:

```python
def add_agent(self, name: str, graph, description: str = ""):
    """Register a pre-built CompiledStateGraph as a named agent.

    Args:
        name: Unique agent identifier
        graph: A compiled LangGraph (must have ainvoke and astream_events)
        description: Human-readable description
    """
    if name in self.engine._agents:
        raise ValueError(f"Agent '{name}' already registered")

    from lc_agent.core.models import AgentPreset

    self.engine._agents[name] = graph
    preset = AgentPreset(
        id=name,
        name=name,
        system_prompt=description or f"Custom agent: {name}",
        default_model="custom",
    )
    self.engine._custom_presets[name] = preset
```

Also add `_custom_presets` to `AgentEngine.__init__`:

In `lc_agent/core/engine.py`, add in `__init__`:

```python
self._custom_presets: dict[str, AgentPreset] = {}
```

And update `get_presets` to include custom presets:

```python
def get_presets(self) -> list[AgentPreset]:
    """Return all agent presets (including default and custom)."""
    default = self.get_default_preset()
    return [default] + list(self._presets.values()) + list(self._custom_presets.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_custom_agents.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/app.py lc_agent/core/engine.py tests/test_custom_agents.py
git commit -m "feat: app.add_agent() registers custom CompiledStateGraph agents"
```

---

### Task 2: Custom agents in /api/agents response

**Files:**
- Modify: `lc_agent/server/routes/agents.py`
- Modify: `tests/test_custom_agents.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_custom_agents.py`:

```python
import httpx
from httpx import ASGITransport


@pytest.mark.asyncio
async def test_api_agents_includes_custom(app_instance):
    """GET /api/agents should include custom agents with source flag."""
    mock_graph = MagicMock()
    app_instance.add_agent("api_agent", mock_graph, description="API test")

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance.fastapi_app),
        base_url="http://test"
    ) as client:
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        custom = [a for a in agents if a["id"] == "api_agent"]
        assert len(custom) == 1
        assert custom[0].get("source") == "code"


@pytest.mark.asyncio
async def test_api_custom_agent_not_deletable(app_instance):
    """DELETE on custom agent should return 403."""
    mock_graph = MagicMock()
    app_instance.add_agent("protected", mock_graph)

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance.fastapi_app),
        base_url="http://test"
    ) as client:
        resp = await client.delete("/api/agents/protected")
        assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_custom_agents.py::test_api_agents_includes_custom -v`
Expected: FAIL (no "source" field in response)

- [ ] **Step 3: Update agents route to include source and protect custom agents**

In `lc_agent/server/routes/agents.py`, read the file and update the `list_agents` endpoint:

```python
@router.get("/agents")
def list_agents(engine: AgentEngine = Depends(get_engine)):
    presets = engine.get_presets()
    result = []
    for p in presets:
        item = {
            "id": p.id,
            "name": p.name,
            "system_prompt": p.system_prompt,
            "default_model": p.default_model,
            "allowed_tool_groups": p.allowed_tool_groups,
            "allowed_mcp_servers": p.allowed_mcp_servers,
            "allowed_skills": p.allowed_skills,
            "dangerous_tools": p.dangerous_tools,
            "source": "code" if p.id in engine._custom_presets else "config",
        }
        result.append(item)
    return result
```

Update the `delete_agent` endpoint to reject custom agents:

```python
@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, engine: AgentEngine = Depends(get_engine)):
    if agent_id == "__default__":
        raise HTTPException(status_code=400, detail="Cannot delete default agent")
    if agent_id in engine._custom_presets:
        raise HTTPException(status_code=403, detail="Cannot delete code-registered agent")
    success = engine.delete_preset(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Response(status_code=204)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_custom_agents.py -v`
Expected: 5 PASS

- [ ] **Step 5: Run full suite**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add lc_agent/server/routes/agents.py tests/test_custom_agents.py
git commit -m "feat: /api/agents includes custom agents with source flag and deletion protection"
```

---

### Task 3: Custom agent streaming via WebSocket

**Files:**
- Modify: `lc_agent/server/websocket.py`
- Modify: `tests/test_custom_agents.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_custom_agents.py`:

```python
from lc_agent.server.websocket import ChatWebSocketHandler


@pytest.mark.asyncio
async def test_websocket_uses_custom_agent(app_instance):
    """WebSocket should use pre-built graph for custom agent."""
    mock_graph = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="custom response")}}

    mock_graph.astream_events = fake_stream
    app_instance.add_agent("ws_agent", mock_graph, description="WS test")

    handler = ChatWebSocketHandler(app_instance.engine)
    ws = AsyncMock()

    data = {"type": "message", "content": "hello", "preset_id": "ws_agent"}
    await handler.handle_message(ws, "thread-1", data)

    calls = ws.send_json.call_args_list
    token_calls = [c for c in calls if c[0][0].get("type") == "token"]
    assert len(token_calls) >= 1
    assert "custom response" in token_calls[0][0][0]["content"]
```

- [ ] **Step 2: Run test to verify behavior**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_custom_agents.py::test_websocket_uses_custom_agent -v`
Expected: PASS (since chat_stream already checks `self._agents.get(preset_id)` which includes custom agents)

- [ ] **Step 3: Add missing import if needed**

Add `from unittest.mock import AsyncMock` at the top of `tests/test_custom_agents.py` if not already there.

- [ ] **Step 4: Run full suite**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add tests/test_custom_agents.py
git commit -m "test: verify custom agent streaming through WebSocket"
```

---

### Task 4: Update __init__.py exports for framework usage

**Files:**
- Modify: `lc_agent/__init__.py`

- [ ] **Step 1: Update public exports**

In `lc_agent/__init__.py`, ensure these are exported:

```python
"""lc_agent — LangChain Agent framework with built-in Web UI."""

__version__ = "0.1.0"

from lc_agent.app import LcAgentApp
from lc_agent.config.loader import load_config
from lc_agent.tools.registry import ToolRegistry, tool

__all__ = [
    "LcAgentApp",
    "load_config",
    "ToolRegistry",
    "tool",
    "__version__",
]
```

- [ ] **Step 2: Verify import works**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -c "from lc_agent import LcAgentApp, load_config, tool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run full suite**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add lc_agent/__init__.py
git commit -m "feat: clean public API exports for framework usage"
```
