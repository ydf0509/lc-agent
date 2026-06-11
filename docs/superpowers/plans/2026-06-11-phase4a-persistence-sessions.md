# Phase 4a: SQLModel Persistence + Multi-Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist agent presets and chat sessions to SQLite (configurable to PostgreSQL), enable multi-session switching with full state restoration via LangGraph checkpoints.

**Architecture:** SQLModel handles structured metadata (presets, session titles), LangGraph's AsyncSqliteSaver handles conversation state. Both share SQLite file by default. Frontend gains a real session store and enhanced sidebar.

**Tech Stack:** SQLModel, aiosqlite, langgraph-checkpoint-sqlite, FastAPI async, Pinia

**Python Interpreter:** `D:\ProgramData\miniconda3\envs\py312\python.exe`

---

## File Structure

### Backend (new)
- `lc_agent/db/__init__.py` — DB module init
- `lc_agent/db/models.py` — SQLModel table definitions
- `lc_agent/db/engine.py` — DB engine creation + session management
- `lc_agent/db/repository.py` — CRUD operations for presets and sessions
- `lc_agent/server/routes/sessions.py` — Sessions REST API
- `tests/test_db.py` — DB model + repository tests
- `tests/test_routes_sessions.py` — Sessions API tests

### Backend (modify)
- `pyproject.toml` — add new dependencies
- `lc_agent/config/schema.py` — add DatabaseConfig
- `lc_agent/core/engine.py` — switch to AsyncSqliteSaver, load presets from DB
- `lc_agent/server/routes/agents.py` — use DB repository instead of in-memory
- `lc_agent/server/app.py` — register sessions router
- `lc_agent/app.py` — init DB on startup, pass checkpoint saver
- `lc_agent/server/websocket.py` — send history on reconnect

### Frontend (new)
- `frontend/src/stores/sessions.ts` — sessions Pinia store

### Frontend (modify)
- `frontend/src/api/http.ts` — add session endpoints
- `frontend/src/stores/chat.ts` — handle history event
- `frontend/src/components/layout/LeftSidebar.vue` — real session list

---

### Task 1: Dependencies + Database Models

**Files:**
- Modify: `pyproject.toml`
- Create: `lc_agent/db/__init__.py`
- Create: `lc_agent/db/models.py`
- Create: `lc_agent/db/engine.py`
- Modify: `lc_agent/config/schema.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Add dependencies to `pyproject.toml`**

In the `[project] dependencies` array, add:
```
"sqlmodel>=0.0.22",
"aiosqlite>=0.20",
"langgraph-checkpoint-sqlite>=3.0",
```

Then install: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pip install -e ".[dev]"`

- [ ] **Step 2: Add DatabaseConfig to `lc_agent/config/schema.py`**

Add a new class and modify AppConfig:

```python
class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./lc_agent_data.db"
    checkpoint_path: str = "./lc_agent_checkpoints.db"
```

Add to AppConfig:
```python
database: DatabaseConfig = Field(default_factory=DatabaseConfig)
```

- [ ] **Step 3: Create `lc_agent/db/__init__.py`**

```python
from lc_agent.db.models import AgentPresetDB, SessionMeta
from lc_agent.db.engine import get_async_engine, get_async_session, init_db

__all__ = ["AgentPresetDB", "SessionMeta", "get_async_engine", "get_async_session", "init_db"]
```

- [ ] **Step 4: Create `lc_agent/db/models.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


def utcnow():
    return datetime.now(timezone.utc)


class AgentPresetDB(SQLModel, table=True):
    __tablename__ = "agent_presets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    system_prompt: str = ""
    default_model: str = ""
    allowed_tool_groups: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_mcp_servers: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_skills: list[str] | None = Field(default=None, sa_column=Column(JSON))
    dangerous_tools: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SessionMeta(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = "新对话"
    agent_id: str = "__default__"
    model: str = ""
    message_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 5: Create `lc_agent/db/engine.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

_engine = None
_async_session_factory = None


def get_async_engine(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    global _engine
    if _engine is None:
        _engine = create_async_engine(url, echo=False)
    return _engine


def get_async_session(url: str = "sqlite+aiosqlite:///./lc_agent_data.db") -> AsyncSession:
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine(url)
        _async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session_factory()


async def init_db(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    """Create all tables."""
    engine = get_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def reset_engine():
    """Reset engine state (for testing)."""
    global _engine, _async_session_factory
    _engine = None
    _async_session_factory = None
```

- [ ] **Step 6: Write tests `tests/test_db.py`**

```python
import pytest
from sqlmodel import SQLModel

from lc_agent.db.models import AgentPresetDB, SessionMeta
from lc_agent.db.engine import get_async_engine, get_async_session, init_db, reset_engine


@pytest.fixture(autouse=True)
async def setup_db():
    reset_engine()
    await init_db("sqlite+aiosqlite:///:memory:")
    yield
    reset_engine()


@pytest.mark.asyncio
async def test_create_agent_preset():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        preset = AgentPresetDB(name="Test Agent", system_prompt="Hello", default_model="gpt-4")
        session.add(preset)
        await session.commit()
        await session.refresh(preset)
        assert preset.id is not None
        assert preset.name == "Test Agent"
        assert preset.created_at is not None


@pytest.mark.asyncio
async def test_create_session():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        sess = SessionMeta(title="Test Chat", agent_id="__default__", model="gpt-4")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        assert sess.id is not None
        assert sess.title == "Test Chat"
        assert sess.message_count == 0


@pytest.mark.asyncio
async def test_session_default_values():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        sess = SessionMeta()
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        assert sess.title == "新对话"
        assert sess.agent_id == "__default__"
```

- [ ] **Step 7: Run tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_db.py -v`
Expected: 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml lc_agent/db/ lc_agent/config/schema.py tests/test_db.py
git commit -m "feat: database models and engine setup with SQLModel + aiosqlite"
```

---

### Task 2: Database Repository (CRUD layer)

**Files:**
- Create: `lc_agent/db/repository.py`
- Extend: `tests/test_db.py`

- [ ] **Step 1: Create `lc_agent/db/repository.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models import AgentPresetDB, SessionMeta


class PresetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[AgentPresetDB]:
        result = await self.session.execute(select(AgentPresetDB).order_by(AgentPresetDB.created_at))
        return list(result.scalars().all())

    async def get_by_id(self, preset_id: str) -> AgentPresetDB | None:
        return await self.session.get(AgentPresetDB, preset_id)

    async def create(self, **kwargs) -> AgentPresetDB:
        preset = AgentPresetDB(**kwargs)
        self.session.add(preset)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset

    async def update(self, preset_id: str, **kwargs) -> AgentPresetDB | None:
        preset = await self.get_by_id(preset_id)
        if preset is None:
            return None
        for key, value in kwargs.items():
            if hasattr(preset, key):
                setattr(preset, key, value)
        preset.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset

    async def delete(self, preset_id: str) -> bool:
        preset = await self.get_by_id(preset_id)
        if preset is None:
            return False
        await self.session.delete(preset)
        await self.session.commit()
        return True


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self, limit: int = 50) -> list[SessionMeta]:
        result = await self.session.execute(
            select(SessionMeta).order_by(SessionMeta.updated_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, session_id: str) -> SessionMeta | None:
        return await self.session.get(SessionMeta, session_id)

    async def create(self, **kwargs) -> SessionMeta:
        sess = SessionMeta(**kwargs)
        self.session.add(sess)
        await self.session.commit()
        await self.session.refresh(sess)
        return sess

    async def update(self, session_id: str, **kwargs) -> SessionMeta | None:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return None
        for key, value in kwargs.items():
            if hasattr(sess, key):
                setattr(sess, key, value)
        sess.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(sess)
        return sess

    async def delete(self, session_id: str) -> bool:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return False
        await self.session.delete(sess)
        await self.session.commit()
        return True

    async def increment_messages(self, session_id: str) -> None:
        sess = await self.get_by_id(session_id)
        if sess:
            sess.message_count += 1
            sess.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
```

- [ ] **Step 2: Add repository tests to `tests/test_db.py`**

```python
@pytest.mark.asyncio
async def test_preset_repository_crud():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        repo = PresetRepository(session)

        created = await repo.create(name="Coder", system_prompt="Code", default_model="gpt-4")
        assert created.id is not None

        fetched = await repo.get_by_id(created.id)
        assert fetched.name == "Coder"

        updated = await repo.update(created.id, name="Super Coder")
        assert updated.name == "Super Coder"

        all_presets = await repo.list_all()
        assert len(all_presets) == 1

        deleted = await repo.delete(created.id)
        assert deleted is True

        all_presets = await repo.list_all()
        assert len(all_presets) == 0


@pytest.mark.asyncio
async def test_session_repository_crud():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        repo = SessionRepository(session)

        created = await repo.create(title="Hello chat", agent_id="__default__", model="gpt-4")
        assert created.id is not None

        await repo.increment_messages(created.id)
        fetched = await repo.get_by_id(created.id)
        assert fetched.message_count == 1

        sessions = await repo.list_all()
        assert len(sessions) == 1

        await repo.delete(created.id)
        sessions = await repo.list_all()
        assert len(sessions) == 0
```

Import `PresetRepository` and `SessionRepository` at the top of the test file.

- [ ] **Step 3: Run tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_db.py -v`
Expected: 5 tests PASS

- [ ] **Step 4: Commit**

```bash
git add lc_agent/db/repository.py tests/test_db.py
git commit -m "feat: CRUD repository classes for presets and sessions"
```

---

### Task 3: Sessions REST API

**Files:**
- Create: `lc_agent/server/routes/sessions.py`
- Create: `tests/test_routes_sessions.py`
- Modify: `lc_agent/server/app.py` — register sessions router
- Modify: `lc_agent/server/dependencies.py` — add get_db_session dependency

- [ ] **Step 1: Update `lc_agent/server/dependencies.py`**

Add a DB session dependency:

```python
from lc_agent.db.engine import get_async_session as _get_session

async def get_db_session():
    """Dependency to get an async DB session."""
    db_url = "sqlite+aiosqlite:///./lc_agent_data.db"
    async with _get_session(db_url) as session:
        yield session
```

Note: In a later step, the actual URL will come from app.state. For now this is a placeholder that works.

- [ ] **Step 2: Create `lc_agent/server/routes/sessions.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.repository import SessionRepository
from lc_agent.server.dependencies import get_db_session

router = APIRouter(tags=["sessions"])


class SessionCreateRequest(BaseModel):
    title: str = "新对话"
    agent_id: str = "__default__"
    model: str = ""


class SessionUpdateRequest(BaseModel):
    title: str | None = None


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    sessions = await repo.list_all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "agent_id": s.agent_id,
            "model": s.model,
            "message_count": s.message_count,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.post("/sessions", status_code=201)
async def create_session(body: SessionCreateRequest, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    session = await repo.create(title=body.title, agent_id=body.agent_id, model=body.model)
    return {"id": session.id, "title": session.title}


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, body: SessionUpdateRequest, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    update_data = body.model_dump(exclude_unset=True)
    result = await repo.update(session_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": result.id, "title": result.title}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    deleted = await repo.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)
```

- [ ] **Step 3: Register sessions router in `lc_agent/server/app.py`**

Add import and registration (before static mount):
```python
from lc_agent.server.routes.sessions import router as sessions_router
app.include_router(sessions_router, prefix="/api")
```

- [ ] **Step 4: Write tests `tests/test_routes_sessions.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.db.engine import init_db, reset_engine
from lc_agent.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
async def setup():
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None
    reset_engine()
    await init_db("sqlite+aiosqlite:///:memory:")
    yield
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None
    reset_engine()


@pytest.fixture
def app():
    config = {
        "provider": {"openai": {"base_url": "http://fake", "api_key": "sk-fake", "models": [{"id": "gpt-4"}]}},
        "agent": {"default_model": "gpt-4", "system_prompt": "Test"},
        "database": {"url": "sqlite+aiosqlite:///:memory:", "checkpoint_path": ":memory:"},
    }
    return LcAgentApp(config)


@pytest.mark.asyncio
async def test_create_and_list_sessions(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/sessions", json={"title": "Test Chat", "model": "gpt-4"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Chat"
        assert "id" in data

        list_resp = await client.get("/api/sessions")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_update_session_title(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "Original"})
        session_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/sessions/{session_id}", json={"title": "Updated"})
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_delete_session(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "To Delete"})
        session_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/sessions/{session_id}")
        assert del_resp.status_code == 204

        list_resp = await client.get("/api/sessions")
        assert len(list_resp.json()) == 0
```

- [ ] **Step 5: Run tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_routes_sessions.py -v`
Expected: 3 tests PASS

- [ ] **Step 6: Run all tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass (52+)

- [ ] **Step 7: Commit**

```bash
git add lc_agent/server/routes/sessions.py lc_agent/server/dependencies.py lc_agent/server/app.py tests/test_routes_sessions.py
git commit -m "feat: sessions REST API with CRUD endpoints"
```

---

### Task 4: Integrate Checkpoint Saver + Engine Migration

**Files:**
- Modify: `lc_agent/core/engine.py` — use AsyncSqliteSaver instead of InMemorySaver
- Modify: `lc_agent/app.py` — init DB + checkpoint on startup
- Modify: `lc_agent/server/websocket.py` — load history on connect, auto-title

- [ ] **Step 1: Modify `lc_agent/core/engine.py`**

Replace the InMemorySaver import with conditional checkpoint setup:

```python
# Replace:
# from langgraph.checkpoint.memory import InMemorySaver

# The engine now accepts an optional checkpointer parameter
class AgentEngine:
    def __init__(self, config: dict, checkpointer=None):
        self.config = config
        self.tool_registry = ToolRegistry()
        self._checkpointer = checkpointer
        self._agents: dict[str, Any] = {}
        self._current_preset: AgentPreset | None = None
        self._models: list[ModelInfo] = self._parse_models(config)
        self._presets: dict[str, AgentPreset] = {}
```

Update `build_agent` to use `self._checkpointer` (it can be None during testing).

- [ ] **Step 2: Modify `lc_agent/app.py` — startup with DB init**

Add async startup event that:
1. Calls `init_db(url)` 
2. Creates `AsyncSqliteSaver` for checkpoints
3. Passes saver to `AgentEngine`

```python
from lc_agent.db.engine import init_db, get_async_engine

# In LcAgentApp.__init__:
db_config = config.get("database", {})
self._db_url = db_config.get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
self._checkpoint_path = db_config.get("checkpoint_path", "./lc_agent_checkpoints.db")

# Add lifespan or startup event:
@self.fastapi_app.on_event("startup")
async def startup():
    await init_db(self._db_url)
```

- [ ] **Step 3: Modify WebSocket handler — send history on reconnect**

In `ChatWebSocketHandler.connect`, after accepting the connection:
- If `thread_id` was provided (reconnecting), load checkpoint state
- Send `{type: "history", messages: [...]}` with the conversation history

```python
async def connect(self, websocket: WebSocket, thread_id: str | None = None) -> str:
    await websocket.accept()
    if thread_id is None:
        thread_id = str(uuid.uuid4())
    self.active_connections[thread_id] = websocket
    await websocket.send_json({"type": "connected", "thread_id": thread_id})

    # Send history if reconnecting to existing thread
    if self.engine._checkpointer:
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = await self.engine._agents.get("__default__", self.engine.build_agent()).aget_state(config)
            if state and state.values.get("messages"):
                history = []
                for msg in state.values["messages"]:
                    history.append({
                        "role": getattr(msg, "type", "unknown"),
                        "content": getattr(msg, "content", ""),
                    })
                await websocket.send_json({"type": "history", "messages": history})
        except Exception:
            pass  # No history available

    return thread_id
```

- [ ] **Step 4: Run all backend tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass (tests use None checkpointer / InMemorySaver fallback)

- [ ] **Step 5: Commit**

```bash
git add lc_agent/core/engine.py lc_agent/app.py lc_agent/server/websocket.py
git commit -m "feat: integrate AsyncSqliteSaver checkpoint and history replay on reconnect"
```

---

### Task 5: Frontend Sessions Store + Sidebar

**Files:**
- Create: `frontend/src/stores/sessions.ts`
- Modify: `frontend/src/api/http.ts` — add session endpoints
- Modify: `frontend/src/stores/chat.ts` — handle history event
- Modify: `frontend/src/components/layout/LeftSidebar.vue` — real session list
- Modify: `frontend/src/App.vue` — init sessions store

- [ ] **Step 1: Add session endpoints to `frontend/src/api/http.ts`**

Add to the `api` object:

```typescript
getSessions: () => fetchApi<any[]>('/sessions'),
createSession: (data: { title?: string; agent_id?: string; model?: string }) =>
  fetchApi<{ id: string; title: string }>('/sessions', { method: 'POST', body: JSON.stringify(data) }),
updateSession: (id: string, data: { title?: string }) =>
  fetchApi<any>(`/sessions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
deleteSession: (id: string) =>
  fetchApi<void>(`/sessions/${id}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Create `frontend/src/stores/sessions.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'

export interface Session {
  id: string
  title: string
  agent_id: string
  model: string
  message_count: number
  created_at: string
  updated_at: string
}

export const useSessionsStore = defineStore('sessions', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)

  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value)
  )

  async function init() {
    try {
      sessions.value = await api.getSessions()
    } catch (e) {
      console.error('[SessionsStore] Failed to fetch:', e)
    }
  }

  async function createSession(agentId: string = '__default__', model: string = '') {
    const created = await api.createSession({ agent_id: agentId, model })
    sessions.value.unshift({ ...created, agent_id: agentId, model, message_count: 0, created_at: new Date().toISOString(), updated_at: new Date().toISOString() })
    currentSessionId.value = created.id
    return created
  }

  async function deleteSession(id: string) {
    await api.deleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value[0]?.id || null
    }
  }

  async function updateTitle(id: string, title: string) {
    await api.updateSession(id, { title })
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.title = title
  }

  function selectSession(id: string) {
    currentSessionId.value = id
  }

  return { sessions, currentSessionId, currentSession, init, createSession, deleteSession, updateTitle, selectSession }
})
```

- [ ] **Step 3: Update `frontend/src/stores/chat.ts` — handle history event**

Add a handler in the `connect()` function:

```typescript
ws.value.on('history', (msg: WsMessage) => {
  const historyMessages = (msg as any).messages || []
  messages.value = historyMessages.map((m: any, idx: number) => ({
    id: crypto.randomUUID(),
    role: m.role === 'human' ? 'user' : m.role === 'ai' ? 'assistant' : m.role,
    content: m.content || '',
    timestamp: Date.now() - (historyMessages.length - idx) * 1000,
  }))
})
```

- [ ] **Step 4: Replace `frontend/src/components/layout/LeftSidebar.vue`**

```vue
<template>
  <aside class="left-sidebar">
    <div class="sidebar-section">
      <el-button type="primary" size="small" style="width:100%" @click="$emit('newChat')">
        + 新对话
      </el-button>
    </div>
    <div class="sidebar-section">
      <h4>会话历史</h4>
      <div class="session-list">
        <div
          v-for="session in sessionsStore.sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === sessionsStore.currentSessionId }"
          @click="$emit('switchSession', session.id)"
        >
          <span class="session-title">{{ session.title }}</span>
          <span class="session-time">{{ formatTime(session.updated_at) }}</span>
        </div>
        <p v-if="!sessionsStore.sessions.length" class="empty-hint">暂无会话</p>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useSessionsStore } from '@/stores/sessions'

const sessionsStore = useSessionsStore()

defineEmits<{ newChat: []; switchSession: [id: string] }>()

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}
</script>

<style scoped>
.left-sidebar {
  width: 240px;
  background: var(--lc-bg-secondary);
  border-right: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 16px;
}

.sidebar-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--lc-text-primary);
}

.session-item:hover {
  background: var(--lc-bg-tertiary);
}

.session-item.active {
  background: var(--lc-bg-tertiary);
  border-left: 2px solid var(--lc-accent);
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}

.session-time {
  font-size: 11px;
  color: var(--lc-text-secondary);
  flex-shrink: 0;
}

.empty-hint {
  font-size: 12px;
  color: var(--lc-text-secondary);
  text-align: center;
  padding: 12px;
}
</style>
```

- [ ] **Step 5: Update `frontend/src/App.vue`**

Add sessions store init + switchSession handler:

```typescript
import { useSessionsStore } from '@/stores/sessions'
const sessionsStore = useSessionsStore()

onMounted(async () => {
  await Promise.all([
    toolsStore.init(),
    agentsStore.init(),
    sessionsStore.init(),
  ])
})

async function handleNewChat() {
  const session = await sessionsStore.createSession()
  chatStore.clearMessages()
  chatStore.disconnect()
  chatStore.connect(session.id)
}

function handleSwitchSession(sessionId: string) {
  sessionsStore.selectSession(sessionId)
  chatStore.clearMessages()
  chatStore.disconnect()
  chatStore.connect(sessionId)
}
```

Update template to pass `@switch-session="handleSwitchSession"` to LeftSidebar.

- [ ] **Step 6: Build frontend**

Run: `cd D:\codes\lc-agent\frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add frontend/src/stores/sessions.ts frontend/src/api/http.ts frontend/src/stores/chat.ts frontend/src/components/layout/LeftSidebar.vue frontend/src/App.vue
git add -f lc_agent/web/dist/
git commit -m "feat: multi-session frontend with session switching and history restore"
```

---

## Summary

After completing all 5 tasks:
- Agent presets persisted to SQLite via SQLModel
- Sessions stored with metadata (title, agent, timestamps)
- LangGraph checkpoint replaces InMemorySaver (full state recovery)
- WebSocket sends message history on reconnect
- Left sidebar shows real session list with relative timestamps
- Session switching triggers WS reconnect + history load
- Default SQLite, configurable to PostgreSQL via config

**Next:** Phase 4b (MCP + Skills management) or Phase 4c (frontend tests with Vitest)
