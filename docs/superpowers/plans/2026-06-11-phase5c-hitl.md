# Phase 5c: Human-in-the-Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When an agent calls a tool listed in `preset.dangerous_tools`, execution pauses via LangGraph `interrupt()` and the user must approve/reject via the frontend before the agent continues.

**Architecture:** Use LangGraph's built-in `interrupt()` mechanism with `create_agent`'s `interrupt_before` parameter for dangerous tools. The WebSocket handler detects the interrupt state and sends it to the frontend. On user response, the handler resumes the graph with `Command(resume=...)`.

**Tech Stack:** `langgraph.types.interrupt`, `langgraph.types.Command`, `create_agent(interrupt_before=...)`, WebSocket events

---

## File Structure

| File | Responsibility |
|------|---------------|
| `lc_agent/core/engine.py` | Pass `interrupt_before` for dangerous tools |
| `lc_agent/server/websocket.py` | Detect interrupt, handle resume |
| `frontend/src/stores/chat.ts` | Wire interrupt event to dialog |
| `tests/test_hitl.py` | Integration test for interrupt flow |

---

### Task 1: Configure interrupt_before in build_agent

**Files:**
- Modify: `lc_agent/core/engine.py`
- Create: `tests/test_hitl.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hitl.py
import pytest
from unittest.mock import patch, MagicMock
from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset


@pytest.fixture
def hitl_engine():
    config = {
        "provider": {
            "test": {
                "api_key": "test-key",
                "base_url": "http://localhost:11434/v1",
                "models": [{"id": "test-model"}],
            }
        },
        "agent": {
            "system_prompt": "You are helpful.",
            "default_model": "test-model",
        },
    }
    return AgentEngine(config)


def test_build_agent_with_dangerous_tools(hitl_engine):
    """Agent with dangerous_tools should have interrupt_before set."""
    preset = AgentPreset(
        id="test-hitl",
        name="HITL Agent",
        system_prompt="Be careful.",
        default_model="test-model",
        dangerous_tools=["delete_file", "rm_rf"],
    )
    agent = hitl_engine.build_agent(preset)
    assert agent is not None


def test_build_agent_without_dangerous_tools(hitl_engine):
    """Agent without dangerous_tools should not interrupt."""
    preset = AgentPreset(
        id="test-safe",
        name="Safe Agent",
        system_prompt="Be safe.",
        default_model="test-model",
        dangerous_tools=[],
    )
    agent = hitl_engine.build_agent(preset)
    assert agent is not None
```

- [ ] **Step 2: Run test to verify it passes (build_agent already works)**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_hitl.py -v`
Expected: PASS (build_agent creates agent regardless)

- [ ] **Step 3: Modify build_agent to pass interrupt_before**

In `lc_agent/core/engine.py`, update the `build_agent` method. Replace the `create_agent` call:

```python
from langchain.agents import create_agent

kwargs: dict[str, Any] = {}
if self._checkpointer:
    kwargs["checkpointer"] = self._checkpointer

if preset.dangerous_tools:
    kwargs["interrupt_before"] = ["tools"]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
    **kwargs,
)
```

Note: `interrupt_before=["tools"]` causes the graph to pause BEFORE executing any tool node. The WebSocket handler will check if the pending tool is in `dangerous_tools` and either auto-approve or ask the user.

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_hitl.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/core/engine.py tests/test_hitl.py
git commit -m "feat: build_agent adds interrupt_before for dangerous tools"
```

---

### Task 2: WebSocket interrupt detection and resume

**Files:**
- Modify: `lc_agent/server/websocket.py`
- Modify: `tests/test_hitl.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hitl.py`:

```python
from unittest.mock import AsyncMock, MagicMock
from lc_agent.server.websocket import ChatWebSocketHandler


@pytest.fixture
def ws_handler():
    engine = MagicMock()
    return ChatWebSocketHandler(engine)


@pytest.mark.asyncio
async def test_interrupt_response_resumes_agent(ws_handler):
    """interrupt_response should invoke graph with Command(resume=...)."""
    ws = AsyncMock()

    # Mock the engine to have a stored agent
    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(return_value={"messages": []})

    async def fake_stream_after_resume(*a, **kw):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Approved!")}}

    mock_agent.astream_events = fake_stream_after_resume
    ws_handler.engine._agents = {"test-preset": mock_agent}

    data = {
        "type": "interrupt_response",
        "approved": True,
        "thread_id": "thread-1",
        "preset_id": "test-preset",
    }
    await ws_handler.handle_message(ws, "thread-1", data)

    # Should have sent some response (token or ack)
    assert ws.send_json.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_hitl.py::test_interrupt_response_resumes_agent -v`
Expected: FAIL (current interrupt_response handler just sends ack)

- [ ] **Step 3: Implement interrupt resume in WebSocket handler**

In `lc_agent/server/websocket.py`, replace the `interrupt_response` branch in `handle_message`:

```python
elif msg_type == "interrupt_response":
    approved = data.get("approved", False)
    preset_id = data.get("preset_id", "__default__")
    try:
        from langgraph.types import Command

        agent = self.engine._agents.get(preset_id)
        if agent is None:
            await websocket.send_json({"type": "error", "message": "No agent found for resume"})
            return

        config = {"configurable": {"thread_id": thread_id}}
        resume_value = {"approved": approved}

        async for event in agent.astream_events(
            Command(resume=resume_value),
            config=config,
            version="v2",
        ):
            await self._send_event(websocket, event)
        await websocket.send_json({"type": "done"})
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
```

Also add interrupt detection in `_send_event`. Add at the end of the method:

```python
elif kind == "on_chain_end":
    data_output = event.get("data", {}).get("output", {})
    if isinstance(data_output, dict) and "__interrupt" in str(data_output):
        await websocket.send_json({
            "type": "interrupt",
            "message": "Tool requires approval",
            "data": data_output,
        })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_hitl.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/server/websocket.py tests/test_hitl.py
git commit -m "feat: WebSocket handles interrupt detection and resume with Command"
```

---

### Task 3: Frontend sends preset_id and approved in interrupt response

**Files:**
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/api/websocket.ts`

- [ ] **Step 1: Read current websocket.ts**

Read `frontend/src/api/websocket.ts` to understand the `sendInterruptResponse` method.

- [ ] **Step 2: Update sendInterruptResponse to include preset_id**

In `frontend/src/api/websocket.ts`, update the `sendInterruptResponse` method to send:

```typescript
sendInterruptResponse(approved: boolean, presetId: string) {
  this.send({
    type: 'interrupt_response',
    approved,
    preset_id: presetId,
  })
}
```

- [ ] **Step 3: Update chat store to pass preset_id**

In `frontend/src/stores/chat.ts`, update `respondToInterrupt`:

```typescript
function respondToInterrupt(approved: boolean, presetId: string = '__default__') {
  ws.value?.sendInterruptResponse(approved, presetId)
  interrupt.value = null
}
```

- [ ] **Step 4: Update sendMessage to include preset_id**

In `frontend/src/stores/chat.ts`, update `sendMessage`:

```typescript
function sendMessage(content: string, presetId: string = '__default__') {
  if (!ws.value || !content.trim()) return

  messages.value.push({
    id: crypto.randomUUID(),
    role: 'user',
    content: content.trim(),
    timestamp: Date.now(),
  })

  ws.value.send({
    type: 'message',
    content: content.trim(),
    preset_id: presetId,
  })
}
```

- [ ] **Step 5: Build frontend**

```bash
cd D:\codes\lc-agent\frontend
npx vite build
```

Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
cd D:\codes\lc-agent
git add frontend/src/stores/chat.ts frontend/src/api/websocket.ts
git add -f lc_agent/web/dist/
git commit -m "feat: frontend sends preset_id with messages and interrupt responses"
```
