# Phase 5: Agent Runtime + MCP Live + HITL + User Registration

## Overview

Phase 5 将 lc_agent 从"可展示的骨架"升级为"可真正使用的 Agent 框架"。核心目标是让用户能够通过 Web UI 与真实 LLM 流式对话、调用工具、使用 MCP 服务器、体验人工审批流程，并允许开发者通过代码注册自定义 Agent。

## Sub-phases

| Sub-phase | Focus | Depends on |
|-----------|-------|------------|
| 5a | Agent Runtime E2E | - |
| 5b | MCP Live Connection | 5a |
| 5c | Human-in-the-Loop | 5a |
| 5d | User Code Agent Registration | 5a |

---

## 5a: Agent Runtime End-to-End

### Goal

`build_agent()` 构建出真正可用的 LangGraph ReAct agent，支持流式输出和工具调用。

### Architecture

```
User → WebSocket → ChatWebSocketHandler
  → engine.build_agent(preset) → CompiledStateGraph
  → graph.astream_events(input, config) → stream tokens/tool events
  → WebSocket → Frontend renders streaming
```

### Key Changes

1. **LLM Initialization** (`lc_agent/core/engine.py`)
   - Parse `provider` config → use `init_chat_model` for standard providers or `ChatOpenAI` for custom base_url
   - Support provider types: `openai`, `deepseek`, `anthropic`, `ollama` (via `langchain.chat_models.init_chat_model`)
   - `temperature`, `stream_usage` from model config

2. **Agent Construction** (`lc_agent/core/engine.py`)
   - Use `langchain.agents.create_agent(model, tools, checkpointer=checkpointer, system_prompt=system_prompt)`
   - Tools come from `ToolRegistry.get_tools(preset.allowed_tools)`
   - Checkpointer from `self._checkpointer` (AsyncSqliteSaver)

3. **Streaming Handler** (`lc_agent/server/websocket.py`)
   - Use `graph.astream_events({"messages": [HumanMessage(content)]}, config={"configurable": {"thread_id": ...}}, version="v2")`
   - Parse events:
     - `on_chat_model_stream` → extract token delta → send `{type: "token", content}`
     - `on_tool_start` → send `{type: "tool_call", name, args}`
     - `on_tool_end` → send `{type: "tool_result", name, output}`
     - Stream end → send `{type: "done"}`

4. **Error Handling**
   - LLM API error → send `{type: "error", message}` via WebSocket
   - Rate limit → exponential backoff (optional, v1 just reports error)
   - Invalid API key → clear error message to frontend

### Data Flow

```
Config:
  providers:
    deepseek:
      api_key: "{env:DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com"
      models:
        - id: "deepseek-chat"
          name: "DeepSeek Chat"

AgentPreset:
  model: "deepseek:deepseek-chat"  →  provider_key="deepseek", model_id="deepseek-chat"
```

### Dependencies

- `langchain-openai>=0.3` (already implied by langchain install)

---

## 5b: MCP Live Connection

### Goal

应用启动后异步连接 MCP 服务器，发现的工具自动转为 LangChain `StructuredTool` 并注册到 tool registry。

### Architecture

```
App startup → UI ready immediately
  → asyncio.create_task(mcp_manager.connect_all())
  → For each server: stdio_client → session.initialize() → list_tools()
  → Convert tools → register as mcp__{server}__{tool_name}
  → Notify frontend via /api/mcp status update
```

### Key Changes

1. **Background Connection** (`lc_agent/app.py`)
   - In startup event, `asyncio.create_task(self._connect_mcp_background())`
   - UI available immediately, MCP connects in background

2. **Tool Conversion** (`lc_agent/mcp/tool_adapter.py`)
   - For each MCP tool: create `StructuredTool` with:
     - `name`: `mcp__{server}__{tool_name}`
     - `description`: from MCP tool schema
     - `args_schema`: dynamic Pydantic model from MCP `inputSchema`
     - `func`: async wrapper that calls `session.call_tool(name, args)`
   - Register into `ToolRegistry` under group `mcp__{server}`

3. **Lifecycle Management** (`lc_agent/mcp/manager.py`)
   - Keep `ClientSession` alive for the app lifetime
   - Track status per server: `connecting` → `connected` / `error`
   - `disconnect_all()` on app shutdown

4. **Status Push** (optional enhancement)
   - Frontend polls `/api/mcp` on interval (simple approach for v1)
   - Future: WebSocket push MCP status changes

### Config Example

```jsonc
{
  "mcp_servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "/tmp"],
      "env": {}
    }
  }
}
```

---

## 5c: Human-in-the-Loop (HITL)

### Goal

当 agent 要调用 `dangerous_tools` 中的工具时，暂停执行并请求用户审批。

### Architecture

```
Agent calls dangerous tool → LangGraph interrupt()
  → WebSocket sends {type: "interrupt", tool_name, args, interrupt_id}
  → Frontend shows InterruptDialog
  → User clicks approve/reject
  → WebSocket sends {action: "approve"/"reject", interrupt_id}
  → Handler invokes Command(resume={"approved": true/false})
  → Agent continues or aborts
```

### Key Changes

1. **Interrupt Node** (`lc_agent/core/engine.py`)
   - When building agent, wrap dangerous tools with a custom node that calls `interrupt({"tool_name": ..., "args": ...})` before execution
   - Use LangGraph's `interrupt()` from `langgraph.types`

2. **WebSocket Integration** (`lc_agent/server/websocket.py`)
   - Detect `__interrupt` in streamed state
   - Send interrupt event to client
   - On resume message from client: `graph.ainvoke(Command(resume=...), config)`

3. **Frontend** (already has `InterruptDialog.vue`)
   - Wire the dialog to actually send the approval/rejection back via WebSocket

### Interrupt Flow Detail

```python
from langgraph.types import interrupt, Command

def approval_node(state):
    tool_call = state["pending_tool_call"]
    decision = interrupt({
        "tool_name": tool_call["name"],
        "args": tool_call["args"],
        "message": f"Allow {tool_call['name']}?"
    })
    if not decision.get("approved"):
        return {"messages": [AIMessage(content="Tool call rejected by user.")]}
    # proceed with actual tool execution
```

---

## 5d: User Code Agent Registration

### Goal

开发者可以通过 `app.add_agent(name, graph)` 注册自定义 `CompiledStateGraph`，这些 agent 在页面 Agent 选择器中可见。

### API Design

```python
from lc_agent import LcAgentApp
from langchain.agents import create_agent

app = LcAgentApp(config_path="config.jsonc")

# Register custom agent
my_graph = create_agent(my_model, my_tools)
app.add_agent("my_custom_agent", my_graph, description="My custom agent")

app.run()
```

### Key Changes

1. **`LcAgentApp.add_agent(name, graph, description="")`** (`lc_agent/app.py`)
   - Store in `self._custom_agents: dict[str, CompiledStateGraph]`
   - Create an `AgentPreset` with `source="code"` marker

2. **Engine Integration** (`lc_agent/core/engine.py`)
   - `build_agent(preset)` checks if preset references a custom agent → return stored graph directly
   - Custom agents bypass normal build flow (they're pre-built)

3. **API Response** (`lc_agent/server/routes/agents.py`)
   - `/api/agents` includes custom agents with `source: "code"` flag
   - Custom agents are read-only in the UI (cannot edit/delete from frontend)

4. **WebSocket** (`lc_agent/server/websocket.py`)
   - When connecting with a custom agent's preset, use the stored graph for streaming

---

## Testing Strategy

- **5a**: Integration test with mocked LLM (use `FakeListChatModel` from langchain) + one optional real test marked `@pytest.mark.integration`
- **5b**: Unit test MCP tool adapter with mocked MCP session
- **5c**: Integration test interrupt flow with `FakeListChatModel` + dangerous tool
- **5d**: Unit test `add_agent` registration + API response

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid API key | WebSocket error event, clear message |
| LLM timeout | Retry once, then error event |
| MCP server crash | Status → "error", tools removed from registry |
| MCP reconnect | Auto-retry with backoff |
| Interrupt timeout | After 5min, auto-reject (configurable) |

## Non-Goals (Phase 5)

- Multi-agent orchestration (agent-to-agent)
- File upload/attachment in chat
- Conversation branching/forking
- Agent marketplace/sharing
