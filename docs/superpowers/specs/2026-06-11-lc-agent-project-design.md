# lc_agent Project Design Spec

> Retroactive design document capturing architecture and decisions for Phases 1-3.

## Goal

Build `lc_agent` — a Python intelligent agent framework powered by LangChain/LangGraph that ships with a production-ready dark-themed Web UI. Users can:
1. Import `lc_agent` as a library and build agents programmatically
2. Launch the built-in web server to interact with agents visually
3. Create, edit, and manage agent presets entirely from the browser

## Design Heritage

Derived from the user's prior `nb_agent` framework (TUI-based), adapting its proven patterns:
- **Tool Registry with groups** — `@tool(group="web")` decorator, three-value semantics for filtering
- **Agent Presets** — configurable profiles with allowed tools/skills/MCPs
- **JSONC Configuration** — comment-friendly config with `{env:VAR}` substitution
- **Human-in-the-Loop** — dangerous tool gating via interrupt mechanism

Key difference: replaces nb_agent's custom ReAct loop with LangGraph's `create_react_agent`, and the TUI with a Vue 3 Web UI.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Web Browser                       │
│  Vue 3 + Element Plus + Pinia + WebSocket Client    │
└───────────────┬──────────────────┬──────────────────┘
                │ HTTP (/api/*)    │ WS (/ws/chat)
┌───────────────▼──────────────────▼──────────────────┐
│              FastAPI Server                          │
│  Routes: health, tools, models, agents              │
│  Static: serves built Vue dist at /                 │
│  WebSocket: ChatWebSocketHandler                    │
└───────────────┬──────────────────┬──────────────────┘
                │                  │
┌───────────────▼───┐  ┌──────────▼──────────────────┐
│   AgentEngine     │  │    ToolRegistry (singleton)  │
│  - build_agent()  │  │  - register(), @tool()       │
│  - chat_stream()  │  │  - get_filtered_tools()      │
│  - preset CRUD    │  │  - group management          │
└───────────────┬───┘  └──────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────┐
│   LangGraph / LangChain                              │
│   create_react_agent + InMemorySaver + stream_events │
└──────────────────────────────────────────────────────┘
```

## Components

### Backend (`lc_agent/`)

| Module | Responsibility |
|--------|---------------|
| `config/` | JSONC loader with env substitution, Pydantic schema validation |
| `tools/` | Singleton ToolRegistry, `@tool` decorator, group-based filtering |
| `core/` | AgentEngine (builds LangGraph agents), AgentPreset/ModelInfo models |
| `server/` | FastAPI app factory, REST routes, WebSocket handler |
| `app.py` | LcAgentApp orchestrator — wires engine + server + WS |
| `main.py` | CLI entry point with argparse |
| `web/dist/` | Built frontend assets (served by StaticFiles) |

### Frontend (`frontend/`)

| Module | Responsibility |
|--------|---------------|
| `api/` | HTTP helper + WebSocket connection class |
| `stores/` | Pinia stores: chat (streaming), tools (groups/models), agents (CRUD) |
| `components/chat/` | ChatBubble, ChatInput, ToolCallCard, InterruptDialog |
| `components/layout/` | AppHeader, LeftSidebar, RightPanel |
| `components/panels/` | ModelSelector, ToolGroupPanel |
| `components/dialogs/` | AgentEditorDialog |
| `views/` | ChatView (main chat orchestrator) |

## Data Flow

### Chat Message Flow
1. User types message → ChatInput emits `send` event
2. ChatView calls `chatStore.sendMessage(content)`
3. Store pushes user message to local state + sends via WebSocket
4. Backend `ChatWebSocketHandler.handle_message` invokes `engine.chat_stream()`
5. LangGraph `astream_events` yields events → handler converts to `token`/`tool_call`/`tool_result`/`done`
6. Frontend WS handler dispatches events → store updates streaming message reactively

### Agent Preset Flow
1. User creates/edits preset via AgentEditorDialog
2. Frontend calls `api.createAgent()` / `api.updateAgent()`
3. Backend stores preset in-memory via `engine.add_preset()` / `engine.update_preset()`
4. Agent selection changes what LLM + tools + system prompt are used

## Key Design Decisions

1. **LangGraph over DeepAgents** — DeepAgents is beta/opinionated; LangGraph provides stability and flexibility
2. **In-memory preset storage (Phase 1-3)** — persistence deferred to Phase 4 (SQLModel)
3. **Three-value semantics** — `null` = all, `[]` = none, `[items]` = specific (from nb_agent)
4. **Static files in package** — `lc_agent/web/dist/` ships with pip install, served by FastAPI
5. **Dark theme only (Phase 1-3)** — simpler CSS, matches dev-tool aesthetic
6. **No vue-router (Phase 1-3)** — single-page app, routing deferred until multi-view needed

## Error Handling

- Backend: FastAPI HTTPException with appropriate status codes (400, 404, 204)
- WebSocket: try/catch around stream, sends `{type: "error", message: ...}` on failure
- Frontend: stores catch API errors silently with console.error (graceful degradation)
- Config: Pydantic validation on load, clear error messages for missing env vars

## Testing Strategy

- 49 backend tests (pytest + pytest-asyncio + httpx AsyncClient)
- Tests mock no external services; use ASGITransport for HTTP, test registry/engine in isolation
- TDD approach: tests written before implementation for each task
- Frontend: build verification only (no unit tests yet — candidate for Phase 4)

## Phases Completed

- **Phase 1** (merged): Config, Tools, Engine, Server, WebSocket, CLI — 41 tests
- **Phase 2** (merged): Vue setup, WebSocket client, Chat UI, Right Panel, Static serving
- **Phase 3** (current branch): REST APIs (tools, models, agents CRUD), Frontend store integration, Agent Editor

## Future (Phase 4+)

- SQLModel persistence for presets and sessions
- MCP server management (add/remove/toggle from UI)
- Skills management with SKILL.md file discovery
- Multi-session sidebar with history
- Frontend unit tests (Vitest)
- Light theme toggle
- Agent import/export (JSON)
