# Phase 4a: SQLModel Persistence + Multi-Session Management

## Goal

Replace in-memory storage with database persistence for agent presets and chat sessions. Enable users to switch between sessions, restore full conversation history, and continue from where they left off — with LangGraph checkpoint support for complete state recovery.

## Architecture

### Storage Split (Hybrid Approach)

Two storage layers, each optimized for its purpose:

1. **SQLModel** (metadata + presets) — manages structured data:
   - `AgentPresetDB` — persisted agent presets (CRUD)
   - `SessionMeta` — session metadata (title, agent, model, timestamps)

2. **LangGraph Checkpoint** — manages conversation state:
   - Uses `langgraph-checkpoint-sqlite` (default) or `langgraph-checkpoint-postgres`
   - Stores full message history + tool call state + interrupt state
   - `thread_id` = `session.id` (shared key between both layers)

### Why Hybrid?

- LangGraph's checkpoint system already solves state serialization, resume-from-interrupt, and message replay
- Duplicating this in SQLModel would be fragile and tightly coupled to LangGraph internals
- SQLModel handles what LangGraph doesn't: session titles, timestamps, agent associations, listing/search

### Database Configuration

Config file gains a new `database` section:

```jsonc
{
  "database": {
    "url": "sqlite:///./lc_agent_data.db"
    // Or: "url": "postgresql://user:pass@localhost/lc_agent"
  }
}
```

Default: SQLite file in current working directory. No extra installation required.

For PostgreSQL: user must `pip install asyncpg langgraph-checkpoint-postgres`.

## Data Models

### AgentPresetDB (SQLModel table)

```
id: str (UUID, primary key)
name: str
system_prompt: str
default_model: str
allowed_tool_groups: JSON | null    (three-value semantics)
allowed_mcp_servers: JSON | null
allowed_skills: JSON | null
dangerous_tools: JSON               (list of tool names)
created_at: datetime
updated_at: datetime
```

### SessionMeta (SQLModel table)

```
id: str (UUID, primary key, = LangGraph thread_id)
title: str                          (auto-generated from first message)
agent_id: str                       (FK to AgentPresetDB or "__default__")
model: str                          (model used)
message_count: int                  (for display, updated on each exchange)
created_at: datetime
updated_at: datetime
```

## API Changes

### New/Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `GET /api/sessions` | Returns list of SessionMeta, sorted by updated_at DESC |
| `POST /api/sessions` | Creates new session, returns {id, title} |
| `DELETE /api/sessions/{id}` | Deletes session metadata + checkpoint |
| `PUT /api/sessions/{id}` | Update session title |
| `GET /api/sessions/{id}/messages` | Load messages from LangGraph checkpoint |
| `GET /api/agents` | Now reads from DB instead of in-memory |
| `POST/PUT/DELETE /api/agents` | Now persists to DB |

### WebSocket Changes

- On connect with existing `thread_id`: load checkpoint, send full message history to client as `{type: "history", messages: [...]}`
- On first user message in new session: auto-generate title from content[:20]

## Frontend Changes

### LeftSidebar Enhancement

- Replace placeholder with real session list from `GET /api/sessions`
- Each item shows: title + relative time ("3分钟前", "昨天")
- Click → switch session (disconnect WS → reconnect with session's thread_id)
- Highlight active session
- "新对话" button → `POST /api/sessions` → switch to new session
- Delete sessions (swipe or right-click menu)

### Chat Store Changes

- `connect(threadId?)` → if threadId provided, WS connects to that thread
- On `history` event from WS: populate messages array with restored history
- Track `sessionId` alongside `threadId`

### New Pinia Store: `sessions.ts`

```typescript
interface Session {
  id: string
  title: string
  agent_id: string
  model: string
  message_count: number
  created_at: string
  updated_at: string
}
```

Actions: `fetchSessions()`, `createSession()`, `deleteSession()`, `switchSession()`, `updateTitle()`

## Startup / Migration

- On `LcAgentApp` init: create SQLModel tables if not exist (SQLModel `create_all`)
- On first run: migrate in-memory default preset to DB
- Checkpoint saver instantiated from config database URL

## Error Handling

- DB connection failure on startup: log error, fall back to in-memory (graceful degradation)
- Session not found (deleted externally): return 404, frontend removes from list
- Checkpoint corrupted: create new session, show warning to user

## Testing

- New test file: `tests/test_persistence.py` — CRUD for AgentPresetDB and SessionMeta
- New test file: `tests/test_routes_sessions.py` — session endpoints
- Existing tests: update fixtures to use temp SQLite DB (`:memory:` or `tmp_path`)
- Frontend: no Vitest yet (defer to Phase 4b)

## Dependencies

### New packages:
- `langgraph-checkpoint-sqlite` (default checkpoint backend)
- `aiosqlite` (async SQLite driver for SQLModel)

### Optional packages (for PostgreSQL):
- `langgraph-checkpoint-postgres`
- `asyncpg`

## Scope Exclusions

- No full-text search on messages (defer)
- No session sharing between users (single-user framework)
- No automatic session archiving/cleanup
- No frontend unit tests (Phase 4b)
- No MCP/Skills management (Phase 4c)
