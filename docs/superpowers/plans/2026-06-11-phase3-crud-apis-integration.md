# Phase 3: Backend CRUD APIs + Frontend Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add REST APIs for tools/models/agents/sessions management and wire the frontend stores to consume them in real-time.

**Architecture:** New FastAPI router modules expose the AgentEngine and ToolRegistry state via RESTful endpoints. A Pinia `init()` action in the frontend fetches data on mount. Agent presets are managed in-memory (persistent storage deferred to Phase 4). An Agent Editor dialog lets users create/modify presets from the UI.

**Tech Stack:** FastAPI routers, Pydantic response schemas, Pinia stores, Element Plus form dialogs, Vue 3 Composition API

---

## File Structure

### Backend (new)
- `lc_agent/server/routes/tools.py` — GET /api/tools, GET /api/tools/groups
- `lc_agent/server/routes/models.py` — GET /api/models
- `lc_agent/server/routes/agents.py` — CRUD /api/agents
- `lc_agent/server/routes/sessions.py` — GET/POST/DELETE /api/sessions
- `lc_agent/server/dependencies.py` — shared deps (get_engine, get_registry)
- `tests/test_routes_tools.py` — tests for tools API
- `tests/test_routes_models.py` — tests for models API
- `tests/test_routes_agents.py` — tests for agents API

### Backend (modify)
- `lc_agent/server/app.py` — register new routers
- `lc_agent/app.py` — expose engine via app.state

### Frontend (new)
- `frontend/src/components/dialogs/AgentEditorDialog.vue` — create/edit agent
- `frontend/src/stores/agents.ts` — agent presets store

### Frontend (modify)
- `frontend/src/stores/tools.ts` — add `fetchFromBackend()` action
- `frontend/src/App.vue` — call init on mount
- `frontend/src/components/layout/AppHeader.vue` — agent selector
- `frontend/src/components/layout/LeftSidebar.vue` — agent preset list

---

### Task 1: Backend Dependencies + Router Registration

**Files:**
- Create: `lc_agent/server/dependencies.py`
- Modify: `lc_agent/server/app.py`
- Modify: `lc_agent/app.py`

- [ ] **Step 1: Create `lc_agent/server/dependencies.py`**

```python
# lc_agent/server/dependencies.py
from fastapi import Request

from lc_agent.core.engine import AgentEngine
from lc_agent.tools.registry import ToolRegistry


def get_engine(request: Request) -> AgentEngine:
    """Dependency to get the AgentEngine from app state."""
    return request.app.state.engine


def get_registry(request: Request) -> ToolRegistry:
    """Dependency to get the ToolRegistry singleton."""
    return ToolRegistry()
```

- [ ] **Step 2: Modify `lc_agent/app.py` — expose engine on app.state**

Add `self.fastapi_app.state.engine = self.engine` after the engine is created in `__init__`.

In `LcAgentApp.__init__`, after line `self.fastapi_app = create_app(config)`, add:

```python
self.fastapi_app.state.engine = self.engine
```

- [ ] **Step 3: Modify `lc_agent/server/app.py` — prepare for new routers**

Add imports and register new routers (they'll be created in subsequent tasks). For now, just add a placeholder comment and register the first router we'll create.

Replace the entire file content with:

```python
# lc_agent/server/app.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

    web_dist = Path(__file__).parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="frontend")

    return app
```

- [ ] **Step 4: Commit**

```bash
git add lc_agent/server/dependencies.py lc_agent/app.py lc_agent/server/app.py
git commit -m "feat: add server dependencies module and expose engine on app.state"
```

---

### Task 2: Tools API

**Files:**
- Create: `lc_agent/server/routes/tools.py`
- Create: `tests/test_routes_tools.py`
- Modify: `lc_agent/server/app.py` — register tools router

- [ ] **Step 1: Write failing test**

```python
# tests/test_routes_tools.py
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.tools import tool, ToolRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None
    yield
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None


@pytest.fixture
def app_with_tools():
    @tool(group="web")
    def search_web(query: str) -> str:
        """Search the web for information."""
        return f"results for {query}"

    @tool(group="web")
    def fetch_page(url: str) -> str:
        """Fetch a webpage."""
        return f"content of {url}"

    @tool(group="filesystem")
    def read_file(path: str) -> str:
        """Read a file from disk."""
        return f"content of {path}"

    config = {
        "provider": {"openai": {"base_url": "http://fake", "api_key": "sk-fake", "models": [{"id": "gpt-4"}]}},
        "agent": {"default_model": "gpt-4", "system_prompt": "Test"},
    }
    return LcAgentApp(config)


@pytest.mark.asyncio
async def test_get_tools(app_with_tools):
    transport = ASGITransport(app=app_with_tools.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        names = [t["name"] for t in data]
        assert "web__search_web" in names
        assert "filesystem__read_file" in names


@pytest.mark.asyncio
async def test_get_tool_groups(app_with_tools):
    transport = ASGITransport(app=app_with_tools.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools/groups")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        group_names = [g["name"] for g in data]
        assert "web" in group_names
        assert "filesystem" in group_names
        web_group = next(g for g in data if g["name"] == "web")
        assert len(web_group["tools"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_routes_tools.py -v`
Expected: FAIL (routes don't exist yet)

- [ ] **Step 3: Implement tools router**

```python
# lc_agent/server/routes/tools.py
from fastapi import APIRouter, Depends

from lc_agent.server.dependencies import get_registry
from lc_agent.tools.registry import ToolRegistry

router = APIRouter(tags=["tools"])


@router.get("/tools")
def list_tools(registry: ToolRegistry = Depends(get_registry)):
    """List all registered tools."""
    tools = []
    for name, entry in registry._global_tools.items():
        tools.append({
            "name": name,
            "group": entry["group"],
            "description": entry["tool"].description,
        })
    return tools


@router.get("/tools/groups")
def list_tool_groups(registry: ToolRegistry = Depends(get_registry)):
    """List tool groups with their tools."""
    groups: dict[str, list] = {}
    for name, entry in registry._global_tools.items():
        group_name = entry["group"] or "__ungrouped__"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append({
            "name": name,
            "description": entry["tool"].description,
        })
    return [
        {"name": group, "tools": tools}
        for group, tools in sorted(groups.items())
    ]
```

- [ ] **Step 4: Register tools router in `lc_agent/server/app.py`**

Add after the health_router include:

```python
from lc_agent.server.routes.tools import router as tools_router
# ... in create_app():
app.include_router(tools_router, prefix="/api")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_routes_tools.py -v`
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add lc_agent/server/routes/tools.py tests/test_routes_tools.py lc_agent/server/app.py
git commit -m "feat: tools API with /api/tools and /api/tools/groups endpoints"
```

---

### Task 3: Models API

**Files:**
- Create: `lc_agent/server/routes/models.py`
- Create: `tests/test_routes_models.py`
- Modify: `lc_agent/server/app.py` — register models router

- [ ] **Step 1: Write failing test**

```python
# tests/test_routes_models.py
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None
    yield
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None


@pytest.fixture
def app_with_models():
    config = {
        "provider": {
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test",
                "models": [
                    {"id": "gpt-4", "context_limit": 128000},
                    {"id": "gpt-3.5-turbo", "context_limit": 16000},
                ],
            },
            "deepseek": {
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-ds",
                "models": [
                    {"id": "deepseek-chat", "context_limit": 64000},
                ],
            },
        },
        "agent": {"default_model": "gpt-4", "system_prompt": "Test"},
    }
    return LcAgentApp(config)


@pytest.mark.asyncio
async def test_get_models(app_with_models):
    transport = ASGITransport(app=app_with_models.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        ids = [m["id"] for m in data]
        assert "gpt-4" in ids
        assert "deepseek-chat" in ids
        gpt4 = next(m for m in data if m["id"] == "gpt-4")
        assert gpt4["provider"] == "openai"
        assert gpt4["context_limit"] == 128000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_routes_models.py -v`
Expected: FAIL

- [ ] **Step 3: Implement models router**

```python
# lc_agent/server/routes/models.py
from fastapi import APIRouter, Depends

from lc_agent.core.engine import AgentEngine
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["models"])


@router.get("/models")
def list_models(engine: AgentEngine = Depends(get_engine)):
    """List all configured models."""
    return [
        {
            "id": m.id,
            "provider": m.provider,
            "base_url": m.base_url,
            "context_limit": m.context_limit,
        }
        for m in engine.get_models()
    ]
```

- [ ] **Step 4: Register models router in `lc_agent/server/app.py`**

```python
from lc_agent.server.routes.models import router as models_router
app.include_router(models_router, prefix="/api")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_routes_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add lc_agent/server/routes/models.py tests/test_routes_models.py lc_agent/server/app.py
git commit -m "feat: models API with /api/models endpoint"
```

---

### Task 4: Agents CRUD API

**Files:**
- Create: `lc_agent/server/routes/agents.py`
- Create: `tests/test_routes_agents.py`
- Modify: `lc_agent/core/engine.py` — add preset management methods
- Modify: `lc_agent/server/app.py` — register agents router

- [ ] **Step 1: Write failing test**

```python
# tests/test_routes_agents.py
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None
    yield
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None


@pytest.fixture
def app():
    config = {
        "provider": {"openai": {"base_url": "http://fake", "api_key": "sk-fake", "models": [{"id": "gpt-4"}]}},
        "agent": {"default_model": "gpt-4", "system_prompt": "You are helpful."},
    }
    return LcAgentApp(config)


@pytest.mark.asyncio
async def test_list_agents_returns_default(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(a["id"] == "__default__" for a in data)


@pytest.mark.asyncio
async def test_create_agent(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "Code Assistant",
            "system_prompt": "You are a coding expert.",
            "default_model": "gpt-4",
            "allowed_tool_groups": ["filesystem"],
            "dangerous_tools": ["filesystem__delete_file"],
        }
        resp = await client.post("/api/agents", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Code Assistant"
        assert "id" in data
        assert data["id"] != "__default__"


@pytest.mark.asyncio
async def test_update_agent(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "Test Agent",
            "system_prompt": "Original",
            "default_model": "gpt-4",
        })
        agent_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "name": "Updated Agent",
            "system_prompt": "Updated prompt",
            "default_model": "gpt-4",
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Agent"
        assert update_resp.json()["system_prompt"] == "Updated prompt"


@pytest.mark.asyncio
async def test_delete_agent(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "Temp Agent",
            "system_prompt": "Temp",
            "default_model": "gpt-4",
        })
        agent_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/agents/{agent_id}")
        assert del_resp.status_code == 204

        list_resp = await client.get("/api/agents")
        assert not any(a["id"] == agent_id for a in list_resp.json())


@pytest.mark.asyncio
async def test_cannot_delete_default(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/agents/__default__")
        assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_routes_agents.py -v`
Expected: FAIL

- [ ] **Step 3: Add preset management to `lc_agent/core/engine.py`**

Add these methods to the `AgentEngine` class:

```python
def get_presets(self) -> list[AgentPreset]:
    """Return all agent presets (including default)."""
    if not hasattr(self, '_presets'):
        self._presets: dict[str, AgentPreset] = {}
    default = self.get_default_preset()
    return [default] + list(self._presets.values())

def add_preset(self, preset: AgentPreset) -> AgentPreset:
    """Add a new agent preset."""
    if not hasattr(self, '_presets'):
        self._presets = {}
    self._presets[preset.id] = preset
    return preset

def update_preset(self, preset_id: str, data: dict) -> AgentPreset | None:
    """Update an existing preset."""
    if not hasattr(self, '_presets'):
        self._presets = {}
    if preset_id not in self._presets:
        return None
    existing = self._presets[preset_id]
    updated = existing.model_copy(update=data)
    self._presets[preset_id] = updated
    return updated

def delete_preset(self, preset_id: str) -> bool:
    """Delete a preset. Cannot delete default."""
    if not hasattr(self, '_presets'):
        self._presets = {}
    if preset_id == "__default__":
        return False
    return self._presets.pop(preset_id, None) is not None
```

- [ ] **Step 4: Implement agents router**

```python
# lc_agent/server/routes/agents.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["agents"])


class AgentCreateRequest(BaseModel):
    name: str
    system_prompt: str
    default_model: str
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    dangerous_tools: list[str] = []


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    default_model: str | None = None
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    dangerous_tools: list[str] | None = None


@router.get("/agents")
def list_agents(engine: AgentEngine = Depends(get_engine)):
    """List all agent presets."""
    return [preset.model_dump() for preset in engine.get_presets()]


@router.post("/agents", status_code=201)
def create_agent(body: AgentCreateRequest, engine: AgentEngine = Depends(get_engine)):
    """Create a new agent preset."""
    preset = AgentPreset(
        id=str(uuid.uuid4()),
        name=body.name,
        system_prompt=body.system_prompt,
        default_model=body.default_model,
        allowed_tool_groups=body.allowed_tool_groups,
        allowed_mcp_servers=body.allowed_mcp_servers,
        allowed_skills=body.allowed_skills,
        dangerous_tools=body.dangerous_tools,
    )
    engine.add_preset(preset)
    return preset.model_dump()


@router.put("/agents/{agent_id}")
def update_agent(agent_id: str, body: AgentUpdateRequest, engine: AgentEngine = Depends(get_engine)):
    """Update an agent preset."""
    update_data = body.model_dump(exclude_unset=True)
    result = engine.update_preset(agent_id, update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result.model_dump()


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: str, engine: AgentEngine = Depends(get_engine)):
    """Delete an agent preset."""
    if agent_id == "__default__":
        raise HTTPException(status_code=400, detail="Cannot delete default agent")
    deleted = engine.delete_preset(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Response(status_code=204)
```

- [ ] **Step 5: Register agents router in `lc_agent/server/app.py`**

```python
from lc_agent.server.routes.agents import router as agents_router
app.include_router(agents_router, prefix="/api")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_routes_agents.py -v`
Expected: 5 tests PASS

- [ ] **Step 7: Run all tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -v`
Expected: All tests pass (including Phase 1 integration tests)

- [ ] **Step 8: Commit**

```bash
git add lc_agent/server/routes/agents.py lc_agent/core/engine.py tests/test_routes_agents.py lc_agent/server/app.py
git commit -m "feat: agents CRUD API with presets management"
```

---

### Task 5: Frontend Store Integration (fetch tools + models from backend)

**Files:**
- Modify: `frontend/src/stores/tools.ts` — add `init()` action
- Create: `frontend/src/stores/agents.ts` — agent presets store
- Modify: `frontend/src/App.vue` — call stores init on mount
- Modify: `frontend/src/api/http.ts` — add missing endpoints

- [ ] **Step 1: Update `frontend/src/api/http.ts`**

Replace the entire file:

```typescript
// frontend/src/api/http.ts
const BASE_URL = '/api'

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  health: () => fetchApi<{ status: string; version: string }>('/health'),

  getTools: () => fetchApi<{ name: string; group: string; description: string }[]>('/tools'),
  getToolGroups: () => fetchApi<{ name: string; tools: { name: string; description: string }[] }[]>('/tools/groups'),

  getModels: () => fetchApi<{ id: string; provider: string; base_url: string; context_limit: number }[]>('/models'),

  getAgents: () => fetchApi<any[]>('/agents'),
  createAgent: (data: object) => fetchApi<any>('/agents', { method: 'POST', body: JSON.stringify(data) }),
  updateAgent: (id: string, data: object) => fetchApi<any>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAgent: (id: string) => fetchApi<void>(`/agents/${id}`, { method: 'DELETE' }),
}
```

- [ ] **Step 2: Update `frontend/src/stores/tools.ts`**

Replace entire file:

```typescript
// frontend/src/stores/tools.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/http'

export interface ToolGroup {
  name: string
  tools: { name: string; description: string }[]
  enabled: boolean
}

export interface ModelInfo {
  id: string
  provider: string
  base_url: string
  context_limit: number
}

export const useToolsStore = defineStore('tools', () => {
  const groups = ref<ToolGroup[]>([])
  const models = ref<ModelInfo[]>([])
  const currentModel = ref('')

  async function init() {
    try {
      const [groupsData, modelsData] = await Promise.all([
        api.getToolGroups(),
        api.getModels(),
      ])
      groups.value = groupsData.map(g => ({ ...g, enabled: true }))
      models.value = modelsData
      if (modelsData.length > 0 && !currentModel.value) {
        currentModel.value = modelsData[0].id
      }
    } catch (e) {
      console.error('[ToolsStore] Failed to fetch:', e)
    }
  }

  function toggleGroup(groupName: string) {
    const group = groups.value.find(g => g.name === groupName)
    if (group) group.enabled = !group.enabled
  }

  function setModel(modelId: string) {
    currentModel.value = modelId
  }

  return { groups, models, currentModel, init, toggleGroup, setModel }
})
```

- [ ] **Step 3: Create `frontend/src/stores/agents.ts`**

```typescript
// frontend/src/stores/agents.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'

export interface AgentPreset {
  id: string
  name: string
  system_prompt: string
  default_model: string
  allowed_tool_groups: string[] | null
  allowed_mcp_servers: string[] | null
  allowed_skills: string[] | null
  dangerous_tools: string[]
}

export const useAgentsStore = defineStore('agents', () => {
  const agents = ref<AgentPreset[]>([])
  const currentAgentId = ref('__default__')

  const currentAgent = computed(() =>
    agents.value.find(a => a.id === currentAgentId.value) || agents.value[0]
  )

  async function init() {
    try {
      agents.value = await api.getAgents()
    } catch (e) {
      console.error('[AgentsStore] Failed to fetch:', e)
    }
  }

  async function createAgent(data: Omit<AgentPreset, 'id'>) {
    const created = await api.createAgent(data)
    agents.value.push(created)
    return created
  }

  async function updateAgent(id: string, data: Partial<AgentPreset>) {
    const updated = await api.updateAgent(id, data)
    const idx = agents.value.findIndex(a => a.id === id)
    if (idx >= 0) agents.value[idx] = updated
    return updated
  }

  async function deleteAgent(id: string) {
    await api.deleteAgent(id)
    agents.value = agents.value.filter(a => a.id !== id)
    if (currentAgentId.value === id) currentAgentId.value = '__default__'
  }

  function selectAgent(id: string) {
    currentAgentId.value = id
  }

  return {
    agents,
    currentAgentId,
    currentAgent,
    init,
    createAgent,
    updateAgent,
    deleteAgent,
    selectAgent,
  }
})
```

- [ ] **Step 4: Update `frontend/src/App.vue` — call init on mount**

In the `<script setup>` section, add:

```typescript
import { onMounted } from 'vue'
import { useAgentsStore } from '@/stores/agents'

const agentsStore = useAgentsStore()

onMounted(async () => {
  await Promise.all([
    toolsStore.init(),
    agentsStore.init(),
  ])
})
```

Also update the template to use dynamic data:
- `agentName` prop: `agentsStore.currentAgent?.name || 'Default Agent'`
- `modelName` prop: `toolsStore.currentModel || agentsStore.currentAgent?.default_model || 'N/A'`

- [ ] **Step 5: Build frontend**

Run: `cd D:\codes\lc-agent\frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/http.ts frontend/src/stores/ frontend/src/App.vue lc_agent/web/dist/
git commit -m "feat: frontend stores fetch tools/models/agents from backend APIs"
```

---

### Task 6: Agent Editor Dialog

**Files:**
- Create: `frontend/src/components/dialogs/AgentEditorDialog.vue`
- Modify: `frontend/src/components/layout/AppHeader.vue` — add agent selector + new agent button
- Modify: `frontend/src/App.vue` — include dialog

- [ ] **Step 1: Create `frontend/src/components/dialogs/AgentEditorDialog.vue`**

```vue
<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑 Agent' : '新建 Agent'"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="100px" label-position="top">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" placeholder="例如：Code Assistant" />
      </el-form-item>

      <el-form-item label="模型">
        <el-select v-model="form.default_model" style="width:100%" placeholder="选择默认模型">
          <el-option
            v-for="model in toolsStore.models"
            :key="model.id"
            :label="`${model.id} (${model.provider})`"
            :value="model.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="系统提示词">
        <el-input
          v-model="form.system_prompt"
          type="textarea"
          :autosize="{ minRows: 4, maxRows: 12 }"
          placeholder="定义 Agent 的行为和角色..."
        />
      </el-form-item>

      <el-form-item label="允许的工具组">
        <div class="tool-group-select">
          <el-radio-group v-model="toolGroupMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="toolGroupMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="form.allowed_tool_groups_list">
              <el-checkbox
                v-for="group in toolsStore.groups"
                :key="group.name"
                :value="group.name"
              >
                {{ group.name }} ({{ group.tools.length }} tools)
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="危险工具（需要审批）">
        <el-input
          v-model="dangerousToolsStr"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="每行一个工具名, 例如: filesystem__delete_file"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="danger" v-if="isEdit && editingId !== '__default__'" @click="handleDelete">
        删除
      </el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore, type AgentPreset } from '@/stores/agents'

const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()

const visible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const toolGroupMode = ref<'all' | 'none' | 'custom'>('all')

const form = ref({
  name: '',
  system_prompt: '',
  default_model: '',
  allowed_tool_groups_list: [] as string[],
})

const dangerousToolsStr = ref('')

function open(agent?: AgentPreset) {
  if (agent) {
    isEdit.value = true
    editingId.value = agent.id
    form.value.name = agent.name
    form.value.system_prompt = agent.system_prompt
    form.value.default_model = agent.default_model
    dangerousToolsStr.value = (agent.dangerous_tools || []).join('\n')

    if (agent.allowed_tool_groups === null) {
      toolGroupMode.value = 'all'
    } else if (agent.allowed_tool_groups.length === 0) {
      toolGroupMode.value = 'none'
    } else {
      toolGroupMode.value = 'custom'
      form.value.allowed_tool_groups_list = [...agent.allowed_tool_groups]
    }
  } else {
    isEdit.value = false
    editingId.value = ''
    form.value = { name: '', system_prompt: '', default_model: toolsStore.currentModel, allowed_tool_groups_list: [] }
    dangerousToolsStr.value = ''
    toolGroupMode.value = 'all'
  }
  visible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const allowed_tool_groups =
      toolGroupMode.value === 'all' ? null :
      toolGroupMode.value === 'none' ? [] :
      form.value.allowed_tool_groups_list

    const data = {
      name: form.value.name,
      system_prompt: form.value.system_prompt,
      default_model: form.value.default_model,
      allowed_tool_groups,
      dangerous_tools: dangerousToolsStr.value.split('\n').map(s => s.trim()).filter(Boolean),
    }

    if (isEdit.value) {
      await agentsStore.updateAgent(editingId.value, data)
    } else {
      await agentsStore.createAgent(data as any)
    }
    visible.value = false
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  await agentsStore.deleteAgent(editingId.value)
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.tool-group-select {
  width: 100%;
}

.custom-groups {
  margin-top: 8px;
  padding: 8px;
  background: var(--lc-bg-tertiary);
  border-radius: 6px;
}
</style>
```

- [ ] **Step 2: Update `frontend/src/components/layout/AppHeader.vue`**

Replace the file:

```vue
<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">⚡ lc_agent</span>
    </div>
    <div class="header-center">
      <el-select
        :model-value="agentsStore.currentAgentId"
        size="small"
        style="width: 200px"
        @change="agentsStore.selectAgent"
      >
        <el-option
          v-for="agent in agentsStore.agents"
          :key="agent.id"
          :label="agent.name"
          :value="agent.id"
        />
      </el-select>
      <el-button size="small" @click="$emit('editAgent')">
        编辑
      </el-button>
      <el-button size="small" type="primary" @click="$emit('newAgent')">
        + 新Agent
      </el-button>
    </div>
    <div class="header-right">
      <el-tag size="small" type="info">{{ modelName }}</el-tag>
      <el-tag size="small" :type="connected ? 'success' : 'danger'" effect="dark">
        {{ connected ? '已连接' : '未连接' }}
      </el-tag>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useAgentsStore } from '@/stores/agents'

const agentsStore = useAgentsStore()

defineProps<{
  modelName: string
  connected: boolean
}>()

defineEmits<{
  editAgent: []
  newAgent: []
}>()
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--lc-bg-secondary);
  border-bottom: 1px solid var(--lc-border);
  height: 48px;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--lc-accent);
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
```

- [ ] **Step 3: Update `frontend/src/App.vue` — include AgentEditorDialog**

Final `App.vue`:

```vue
<template>
  <div class="app-container">
    <AppHeader
      :model-name="toolsStore.currentModel || agentsStore.currentAgent?.default_model || 'N/A'"
      :connected="chatStore.isConnected"
      @edit-agent="editCurrentAgent"
      @new-agent="createNewAgent"
    />

    <div class="app-body">
      <LeftSidebar @new-chat="handleNewChat" />

      <main class="chat-main">
        <ChatView />
      </main>

      <RightPanel />
    </div>

    <AgentEditorDialog ref="agentEditorRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore } from '@/stores/agents'
import AppHeader from '@/components/layout/AppHeader.vue'
import LeftSidebar from '@/components/layout/LeftSidebar.vue'
import RightPanel from '@/components/layout/RightPanel.vue'
import ChatView from '@/views/ChatView.vue'
import AgentEditorDialog from '@/components/dialogs/AgentEditorDialog.vue'

const chatStore = useChatStore()
const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()
const agentEditorRef = ref<InstanceType<typeof AgentEditorDialog>>()

onMounted(async () => {
  await Promise.all([
    toolsStore.init(),
    agentsStore.init(),
  ])
})

function handleNewChat() {
  chatStore.clearMessages()
  chatStore.disconnect()
  chatStore.connect()
}

function editCurrentAgent() {
  agentEditorRef.value?.open(agentsStore.currentAgent)
}

function createNewAgent() {
  agentEditorRef.value?.open()
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
```

- [ ] **Step 4: Build frontend**

Run: `cd D:\codes\lc-agent\frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 5: Run all backend tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add frontend/ lc_agent/web/dist/
git commit -m "feat: Agent Editor dialog with CRUD UI and header agent selector"
```

---

## Summary

After completing all 6 tasks:
- Full REST API: `/api/tools`, `/api/tools/groups`, `/api/models`, `/api/agents` (CRUD)
- Frontend stores auto-fetch backend data on mount
- Agent Editor dialog for creating/editing presets from the UI
- Three-value semantics for tool group permissions in the editor
- Dynamic header with agent selector and connection status

**Next:** Phase 4 can add:
- SQLModel persistence for agent presets and sessions
- MCP server management UI
- Skills management
- Multi-session support in the left sidebar
