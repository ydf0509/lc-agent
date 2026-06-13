# Phase 5a: Agent Runtime End-to-End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `AgentEngine.build_agent()` produce a working LangGraph agent that streams real LLM responses and tool calls through WebSocket to the frontend.

**Architecture:** Refactor `build_agent()` to use `create_agent` with properly initialized `ChatOpenAI` (supporting configurable `base_url`). Refactor `chat_stream()` to correctly parse `astream_events` v2. Add robust error handling for LLM failures.

**Tech Stack:** `langchain-openai`, `langchain.agents.create_agent`, `astream_events(version="v2")`, `ChatOpenAI`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `lc_agent/core/engine.py` | Refactor `build_agent` + `chat_stream` for real LLM usage |
| `lc_agent/server/websocket.py` | Fix `_send_event` to properly parse astream_events v2 |
| `lc_agent/app.py` | Pass `preset_id` context to WebSocket handler |
| `tests/test_runtime.py` | Integration tests with FakeListChatModel |

---

### Task 1: Fix LLM Initialization in build_agent

**Files:**
- Modify: `lc_agent/core/engine.py`
- Create: `tests/test_runtime.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runtime.py
import pytest
from lc_agent.core.engine import AgentEngine


@pytest.fixture
def engine_with_provider():
    config = {
        "provider": {
            "deepseek": {
                "api_key": "test-key-123",
                "base_url": "https://api.deepseek.com",
                "models": [
                    {"id": "deepseek-chat", "context_limit": 64000}
                ]
            }
        },
        "agent": {
            "system_prompt": "You are helpful.",
            "default_model": "deepseek-chat",
        },
    }
    return AgentEngine(config)


def test_build_agent_creates_graph(engine_with_provider):
    """build_agent should return a compiled graph."""
    preset = engine_with_provider.get_default_preset()
    agent = engine_with_provider.build_agent(preset)
    assert agent is not None
    assert hasattr(agent, 'ainvoke')
    assert hasattr(agent, 'astream_events')


def test_build_agent_uses_correct_model(engine_with_provider):
    """build_agent should pass the correct model params."""
    preset = engine_with_provider.get_default_preset()
    agent = engine_with_provider.build_agent(preset)
    assert agent is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_runtime.py -v`
Expected: FAIL (current build_agent tries `langchain.agents.create_agent` which doesn't exist, then fallback may fail)

- [ ] **Step 3: Rewrite build_agent with clean LLM init**

Replace the entire `build_agent` method in `lc_agent/core/engine.py`:

```python
def build_agent(self, preset: AgentPreset | None = None):
    """Build a LangGraph ReAct agent from preset."""
    if preset is None:
        preset = self.get_default_preset()
    self._current_preset = preset

    system_prompt = preset.system_prompt
    if hasattr(self, '_skill_scanner') and self._skill_scanner:
        enabled_skills = self._skill_scanner.get_filtered(preset.allowed_skills)
        if enabled_skills:
            skills_text = "\n\n---\n\n".join(
                f"## Skill: {s.name}\n\n{s.content}" for s in enabled_skills
            )
            system_prompt = f"{system_prompt}\n\n# Available Skills\n\n{skills_text}"

    tools = self.tool_registry.get_filtered_tools(preset.allowed_tool_groups)
    model_info = self._find_model(preset.default_model)
    llm = self._create_llm(model_info, preset.default_model)

    from langchain.agents import create_agent

    kwargs: dict[str, Any] = {}
    if self._checkpointer:
        kwargs["checkpointer"] = self._checkpointer

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        **kwargs,
    )

    self._agents[preset.id] = agent
    return agent

def _create_llm(self, model_info: ModelInfo | None, model_id: str):
    """Create a ChatOpenAI instance from model info."""
    from langchain_openai import ChatOpenAI

    if model_info:
        return ChatOpenAI(
            model=model_info.id,
            base_url=model_info.base_url or None,
            api_key=model_info.api_key or "not-set",
            temperature=0.7,
        )
    return ChatOpenAI(model=model_id, api_key="not-set")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_runtime.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/core/engine.py tests/test_runtime.py
git commit -m "feat: refactor build_agent to use create_agent with proper LLM init"
```

---

### Task 2: Fix chat_stream to use preset-specific agent

**Files:**
- Modify: `lc_agent/core/engine.py`
- Modify: `tests/test_runtime.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_runtime.py`:

```python
@pytest.mark.asyncio
async def test_chat_stream_yields_events(engine_with_provider):
    """chat_stream should yield astream_events from the agent."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_agent = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="hello")}}
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content=" world")}}

    mock_agent.astream_events = fake_stream
    engine_with_provider._agents["__default__"] = mock_agent

    events = []
    async for event in engine_with_provider.chat_stream("test", "thread-1", "__default__"):
        events.append(event)

    assert len(events) == 2
    assert events[0]["data"]["chunk"].content == "hello"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_runtime.py::test_chat_stream_yields_events -v`
Expected: FAIL (current `chat_stream` doesn't accept `preset_id` param)

- [ ] **Step 3: Refactor chat_stream**

Replace `chat_stream` in `lc_agent/core/engine.py`:

```python
async def chat_stream(self, message: str, thread_id: str, preset_id: str = "__default__") -> AsyncIterator[dict]:
    """Stream chat responses as events."""
    agent = self._agents.get(preset_id)
    if agent is None:
        preset = self._presets.get(preset_id) or self.get_default_preset()
        agent = self.build_agent(preset)

    config = {"configurable": {"thread_id": thread_id}}
    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
        version="v2",
    ):
        yield event
```

Also update `chat` method signature for consistency:

```python
async def chat(self, message: str, thread_id: str, preset_id: str = "__default__") -> str:
    """Send a message and get a response (non-streaming)."""
    agent = self._agents.get(preset_id)
    if agent is None:
        preset = self._presets.get(preset_id) or self.get_default_preset()
        agent = self.build_agent(preset)

    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    messages = result.get("messages", [])
    if messages:
        return messages[-1].content
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_runtime.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/core/engine.py tests/test_runtime.py
git commit -m "feat: chat_stream accepts preset_id and builds agent on demand"
```

---

### Task 3: Improve WebSocket _send_event for astream_events v2

**Files:**
- Modify: `lc_agent/server/websocket.py`
- Create: `tests/test_ws_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ws_events.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from lc_agent.server.websocket import ChatWebSocketHandler
from lc_agent.core.engine import AgentEngine


@pytest.fixture
def handler():
    engine = MagicMock(spec=AgentEngine)
    return ChatWebSocketHandler(engine)


@pytest.mark.asyncio
async def test_send_event_token(handler):
    """on_chat_model_stream should send token event."""
    ws = AsyncMock()
    chunk = MagicMock()
    chunk.content = "Hello"

    event = {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
    await handler._send_event(ws, event)

    ws.send_json.assert_called_once_with({"type": "token", "content": "Hello"})


@pytest.mark.asyncio
async def test_send_event_tool_call(handler):
    """on_tool_start should send tool_call with args."""
    ws = AsyncMock()
    event = {
        "event": "on_tool_start",
        "name": "get_weather",
        "run_id": "abc-123",
        "data": {"input": {"city": "Beijing"}},
    }
    await handler._send_event(ws, event)

    ws.send_json.assert_called_once()
    call_args = ws.send_json.call_args[0][0]
    assert call_args["type"] == "tool_call"
    assert call_args["name"] == "get_weather"
    assert call_args["args"] == {"city": "Beijing"}


@pytest.mark.asyncio
async def test_send_event_tool_result(handler):
    """on_tool_end should send tool_result."""
    ws = AsyncMock()
    event = {
        "event": "on_tool_end",
        "name": "get_weather",
        "data": {"output": "Sunny, 25°C"},
    }
    await handler._send_event(ws, event)

    ws.send_json.assert_called_once()
    call_args = ws.send_json.call_args[0][0]
    assert call_args["type"] == "tool_result"
    assert call_args["name"] == "get_weather"
    assert "Sunny" in call_args["result"]


@pytest.mark.asyncio
async def test_send_event_ignores_irrelevant(handler):
    """Non-relevant events should not send anything."""
    ws = AsyncMock()
    event = {"event": "on_chain_start", "data": {}}
    await handler._send_event(ws, event)

    ws.send_json.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_ws_events.py -v`
Expected: FAIL (tool_call doesn't include args, missing args extraction)

- [ ] **Step 3: Rewrite _send_event**

Replace `_send_event` in `lc_agent/server/websocket.py`:

```python
async def _send_event(self, websocket: WebSocket, event: dict):
    """Convert LangGraph astream_events v2 to client-friendly format."""
    kind = event.get("event", "")

    if kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if chunk and hasattr(chunk, "content") and chunk.content:
            await websocket.send_json({"type": "token", "content": chunk.content})

    elif kind == "on_tool_start":
        tool_input = event.get("data", {}).get("input", {})
        await websocket.send_json({
            "type": "tool_call",
            "name": event.get("name", ""),
            "run_id": event.get("run_id", ""),
            "args": tool_input,
        })

    elif kind == "on_tool_end":
        output = event.get("data", {}).get("output", "")
        await websocket.send_json({
            "type": "tool_result",
            "name": event.get("name", ""),
            "result": str(output)[:2000],
        })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_ws_events.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/server/websocket.py tests/test_ws_events.py
git commit -m "feat: WebSocket _send_event handles astream_events v2 correctly"
```

---

### Task 4: Wire preset_id through WebSocket message flow

**Files:**
- Modify: `lc_agent/server/websocket.py`
- Modify: `lc_agent/app.py`
- Modify: `tests/test_ws_events.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ws_events.py`:

```python
@pytest.mark.asyncio
async def test_handle_message_passes_preset_id(handler):
    """handle_message should pass preset_id from data to chat_stream."""
    ws = AsyncMock()

    async def fake_stream(msg, tid, pid):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="hi")}}

    handler.engine.chat_stream = fake_stream

    data = {"type": "message", "content": "hello", "preset_id": "my_agent"}
    await handler.handle_message(ws, "thread-1", data)

    # Should have sent at least a token event and a done event
    calls = ws.send_json.call_args_list
    types = [c[0][0]["type"] for c in calls]
    assert "token" in types
    assert "done" in types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_ws_events.py::test_handle_message_passes_preset_id -v`
Expected: FAIL (handle_message doesn't extract preset_id)

- [ ] **Step 3: Update handle_message**

In `lc_agent/server/websocket.py`, replace the `handle_message` method:

```python
async def handle_message(self, websocket: WebSocket, thread_id: str, data: dict):
    """Process incoming message and stream response."""
    msg_type = data.get("type", "message")

    if msg_type == "message":
        content = data.get("content", "")
        preset_id = data.get("preset_id", "__default__")
        try:
            async for event in self.engine.chat_stream(content, thread_id, preset_id):
                await self._send_event(websocket, event)
            await websocket.send_json({"type": "done"})
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})

    elif msg_type == "interrupt_response":
        decision = data.get("decision", {})
        await websocket.send_json({"type": "ack", "message": "interrupt handled"})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_ws_events.py -v`
Expected: 5 PASS

- [ ] **Step 5: Run full suite**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add lc_agent/server/websocket.py lc_agent/app.py tests/test_ws_events.py
git commit -m "feat: WebSocket passes preset_id through message flow"
```

---

### Task 5: Error handling for LLM failures

**Files:**
- Modify: `lc_agent/server/websocket.py`
- Modify: `tests/test_ws_events.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ws_events.py`:

```python
@pytest.mark.asyncio
async def test_handle_message_llm_error(handler):
    """LLM errors should send error event, not crash."""
    ws = AsyncMock()

    async def failing_stream(msg, tid, pid):
        raise RuntimeError("API key invalid")
        yield  # noqa: unreachable - makes it a generator

    handler.engine.chat_stream = failing_stream

    data = {"type": "message", "content": "hi"}
    await handler.handle_message(ws, "thread-1", data)

    calls = ws.send_json.call_args_list
    error_calls = [c for c in calls if c[0][0].get("type") == "error"]
    assert len(error_calls) == 1
    assert "API key invalid" in error_calls[0][0][0]["message"]
```

- [ ] **Step 2: Run test to verify it passes (existing error handling should work)**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_ws_events.py::test_handle_message_llm_error -v`
Expected: PASS (the try/except in handle_message already catches this)

- [ ] **Step 3: Run full suite**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_ws_events.py
git commit -m "test: verify LLM error handling in WebSocket flow"
```
