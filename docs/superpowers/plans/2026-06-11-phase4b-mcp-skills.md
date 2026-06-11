# Phase 4b: MCP + Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MCP server integration (config-driven, tools auto-registered) and Skills discovery (SKILL.md scanning with system prompt injection).

**Architecture:** MCP clients spawn subprocess servers, wrap their tools as LangChain StructuredTools via the `mcp` Python SDK. Skills scanner parses markdown frontmatter. Both integrate into the existing ToolRegistry and AgentEngine.

**Tech Stack:** `mcp` Python SDK, `pyyaml` (frontmatter parsing), FastAPI, existing ToolRegistry

**Python Interpreter:** `D:\ProgramData\miniconda3\envs\py312\python.exe`

---

## File Structure

### Backend (new)
- `lc_agent/mcp/__init__.py`
- `lc_agent/mcp/manager.py` — MCP server lifecycle management
- `lc_agent/mcp/tool_adapter.py` — convert MCP tools to LangChain tools
- `lc_agent/skills/__init__.py`
- `lc_agent/skills/scanner.py` — discover and parse SKILL.md files
- `lc_agent/server/routes/mcp.py` — MCP status API
- `lc_agent/server/routes/skills.py` — Skills list API
- `tests/test_mcp.py`
- `tests/test_skills.py`

### Backend (modify)
- `pyproject.toml` — add `mcp`, `pyyaml`
- `lc_agent/config/schema.py` — add MCP + Skills config sections
- `lc_agent/core/engine.py` — inject skills into system prompt
- `lc_agent/server/app.py` — register new routers
- `lc_agent/app.py` — init MCP + Skills on startup

---

### Task 1: Skills Scanner

**Files:**
- Modify: `pyproject.toml` — add `pyyaml`
- Modify: `lc_agent/config/schema.py` — add SkillsConfig
- Create: `lc_agent/skills/__init__.py`
- Create: `lc_agent/skills/scanner.py`
- Create: `tests/test_skills.py`

- [ ] **Step 1: Add `pyyaml` to dependencies in `pyproject.toml`**

Add `"pyyaml>=6.0"` to the dependencies array.

Install: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pip install -e ".[dev]"`

- [ ] **Step 2: Add SkillsConfig to `lc_agent/config/schema.py`**

```python
class SkillsConfig(BaseModel):
    directory: str = "./skills"
```

Add to AppConfig: `skills: SkillsConfig = Field(default_factory=SkillsConfig)`

- [ ] **Step 3: Create `lc_agent/skills/__init__.py`**

```python
from lc_agent.skills.scanner import SkillInfo, SkillScanner

__all__ = ["SkillInfo", "SkillScanner"]
```

- [ ] **Step 4: Create `lc_agent/skills/scanner.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SkillInfo:
    name: str
    description: str
    content: str
    file_path: str


class SkillScanner:
    """Discovers and parses SKILL.md files from a directory."""

    def __init__(self, directory: str = "./skills"):
        self.directory = Path(directory)
        self._skills: list[SkillInfo] = []

    @property
    def skills(self) -> list[SkillInfo]:
        return self._skills

    def scan(self) -> list[SkillInfo]:
        """Scan directory recursively for SKILL.md files."""
        self._skills = []
        if not self.directory.exists():
            return self._skills

        for skill_file in self.directory.rglob("SKILL.md"):
            skill = self._parse_skill(skill_file)
            if skill:
                self._skills.append(skill)

        return self._skills

    def _parse_skill(self, path: Path) -> SkillInfo | None:
        """Parse a SKILL.md file with YAML frontmatter."""
        try:
            text = path.read_text(encoding="utf-8")
            frontmatter, content = self._split_frontmatter(text)

            name = frontmatter.get("name", path.parent.name)
            description = frontmatter.get("description", "")

            return SkillInfo(
                name=name,
                description=description,
                content=content.strip(),
                file_path=str(path),
            )
        except Exception:
            return None

    def _split_frontmatter(self, text: str) -> tuple[dict, str]:
        """Split YAML frontmatter from markdown content."""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if match:
            fm = yaml.safe_load(match.group(1)) or {}
            return fm, match.group(2)
        return {}, text

    def get_by_name(self, name: str) -> SkillInfo | None:
        """Get a skill by name."""
        for skill in self._skills:
            if skill.name == name:
                return skill
        return None

    def get_filtered(self, allowed: list[str] | None) -> list[SkillInfo]:
        """Filter skills by allowed list (three-value semantics)."""
        if allowed is None:
            return self._skills
        if not allowed:
            return []
        return [s for s in self._skills if s.name in allowed]
```

- [ ] **Step 5: Create test fixture — a temp skills directory**

Create `tests/test_skills.py`:

```python
import pytest
from pathlib import Path

from lc_agent.skills.scanner import SkillScanner, SkillInfo


@pytest.fixture
def skills_dir(tmp_path):
    skill1 = tmp_path / "coding" / "SKILL.md"
    skill1.parent.mkdir()
    skill1.write_text(
        "---\nname: coding-assistant\ndescription: Expert coding help\n---\n\n# Coding\n\nYou write clean code.\n",
        encoding="utf-8",
    )

    skill2 = tmp_path / "research" / "SKILL.md"
    skill2.parent.mkdir()
    skill2.write_text(
        "---\nname: researcher\ndescription: Deep research\n---\n\n# Research\n\nYou research thoroughly.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_scan_skills(skills_dir):
    scanner = SkillScanner(str(skills_dir))
    skills = scanner.scan()
    assert len(skills) == 2
    names = [s.name for s in skills]
    assert "coding-assistant" in names
    assert "researcher" in names


def test_skill_content(skills_dir):
    scanner = SkillScanner(str(skills_dir))
    scanner.scan()
    skill = scanner.get_by_name("coding-assistant")
    assert skill is not None
    assert "clean code" in skill.content
    assert skill.description == "Expert coding help"


def test_filter_skills(skills_dir):
    scanner = SkillScanner(str(skills_dir))
    scanner.scan()

    all_skills = scanner.get_filtered(None)
    assert len(all_skills) == 2

    no_skills = scanner.get_filtered([])
    assert len(no_skills) == 0

    some = scanner.get_filtered(["researcher"])
    assert len(some) == 1
    assert some[0].name == "researcher"


def test_empty_directory(tmp_path):
    scanner = SkillScanner(str(tmp_path / "nonexistent"))
    skills = scanner.scan()
    assert len(skills) == 0
```

- [ ] **Step 6: Run tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_skills.py -v`
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml lc_agent/config/schema.py lc_agent/skills/ tests/test_skills.py
git commit -m "feat: Skills scanner with SKILL.md discovery and frontmatter parsing"
```

---

### Task 2: Skills API + Engine Integration

**Files:**
- Create: `lc_agent/server/routes/skills.py`
- Modify: `lc_agent/core/engine.py` — inject skills into prompt
- Modify: `lc_agent/app.py` — init SkillScanner on startup
- Modify: `lc_agent/server/app.py` — register skills router

- [ ] **Step 1: Create `lc_agent/server/routes/skills.py`**

```python
from fastapi import APIRouter, Request

router = APIRouter(tags=["skills"])


@router.get("/skills")
def list_skills(request: Request):
    """List discovered skills."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        return []
    return [
        {"name": s.name, "description": s.description, "file_path": s.file_path}
        for s in scanner.skills
    ]
```

- [ ] **Step 2: Register router in `lc_agent/server/app.py`**

Add before static mount:
```python
from lc_agent.server.routes.skills import router as skills_router
app.include_router(skills_router, prefix="/api")
```

- [ ] **Step 3: Modify `lc_agent/app.py` — init SkillScanner**

In `__init__`, after engine creation:
```python
from lc_agent.skills.scanner import SkillScanner
skills_dir = config.get("skills", {}).get("directory", "./skills")
self.skill_scanner = SkillScanner(skills_dir)
self.skill_scanner.scan()
self.fastapi_app.state.skill_scanner = self.skill_scanner
self.engine._skill_scanner = self.skill_scanner
```

- [ ] **Step 4: Modify `lc_agent/core/engine.py` — inject skills into system prompt**

In `build_agent`, after getting the preset system prompt, append enabled skills:

```python
system_prompt = preset.system_prompt
if hasattr(self, '_skill_scanner') and self._skill_scanner:
    enabled_skills = self._skill_scanner.get_filtered(preset.allowed_skills)
    if enabled_skills:
        skills_text = "\n\n---\n\n".join(
            f"## Skill: {s.name}\n\n{s.content}" for s in enabled_skills
        )
        system_prompt = f"{system_prompt}\n\n# Available Skills\n\n{skills_text}"
```

- [ ] **Step 5: Run all tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass (61+)

- [ ] **Step 6: Commit**

```bash
git add lc_agent/server/routes/skills.py lc_agent/server/app.py lc_agent/app.py lc_agent/core/engine.py
git commit -m "feat: Skills API + system prompt injection for enabled skills"
```

---

### Task 3: MCP Manager (Core)

**Files:**
- Modify: `pyproject.toml` — add `mcp` package
- Modify: `lc_agent/config/schema.py` — add McpConfig
- Create: `lc_agent/mcp/__init__.py`
- Create: `lc_agent/mcp/manager.py`
- Create: `lc_agent/mcp/tool_adapter.py`
- Create: `tests/test_mcp.py`

- [ ] **Step 1: Add `mcp` to dependencies**

Add `"mcp>=1.0"` to pyproject.toml dependencies. Install.

- [ ] **Step 2: Add McpServerConfig to `lc_agent/config/schema.py`**

```python
class McpServerConfig(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
```

Add to AppConfig: `mcp_servers: dict[str, McpServerConfig] = Field(default_factory=dict)`

- [ ] **Step 3: Create `lc_agent/mcp/__init__.py`**

```python
from lc_agent.mcp.manager import McpManager

__all__ = ["McpManager"]
```

- [ ] **Step 4: Create `lc_agent/mcp/manager.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpServerStatus:
    name: str
    command: str
    status: str = "disconnected"  # connected, disconnected, error
    tools: list[str] = field(default_factory=list)
    error: str | None = None


class McpManager:
    """Manages MCP server connections and tool discovery."""

    def __init__(self, config: dict[str, dict]):
        self._config = config
        self._servers: dict[str, McpServerStatus] = {}
        self._tools: dict[str, Any] = {}

        for name, conf in config.items():
            self._servers[name] = McpServerStatus(
                name=name,
                command=conf.get("command", ""),
            )

    @property
    def servers(self) -> list[McpServerStatus]:
        return list(self._servers.values())

    def get_server(self, name: str) -> McpServerStatus | None:
        return self._servers.get(name)

    async def connect_all(self):
        """Attempt to connect to all configured MCP servers."""
        for name, conf in self._config.items():
            await self._connect_server(name, conf)

    async def _connect_server(self, name: str, conf: dict):
        """Connect to a single MCP server."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            env = {**os.environ, **conf.get("env", {})}
            params = StdioServerParameters(
                command=conf["command"],
                args=conf.get("args", []),
                env=env,
            )

            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()

                    tool_names = [t.name for t in tools_result.tools]
                    self._servers[name].status = "connected"
                    self._servers[name].tools = tool_names

        except Exception as e:
            self._servers[name].status = "error"
            self._servers[name].error = str(e)

    def get_tools_for_server(self, server_name: str) -> list[str]:
        """Get tool names for a given server."""
        server = self._servers.get(server_name)
        return server.tools if server else []
```

- [ ] **Step 5: Create `lc_agent/mcp/tool_adapter.py`** (placeholder for now)

```python
"""Adapts MCP tools into LangChain StructuredTool format.

Full implementation requires an active MCP session to call tools.
For Phase 4b, we focus on discovery and status reporting.
"""


def mcp_tool_names_to_display(server_name: str, tool_names: list[str]) -> list[dict]:
    """Convert MCP tool names to display format."""
    return [
        {"name": f"mcp__{server_name}__{name}", "group": f"mcp__{server_name}", "description": f"MCP tool: {name}"}
        for name in tool_names
    ]
```

- [ ] **Step 6: Create `tests/test_mcp.py`** (unit tests for McpManager without actual MCP servers)

```python
import pytest

from lc_agent.mcp.manager import McpManager, McpServerStatus


def test_mcp_manager_init():
    config = {
        "filesystem": {"command": "npx", "args": ["-y", "server-fs"]},
        "github": {"command": "npx", "args": ["-y", "server-github"]},
    }
    manager = McpManager(config)
    assert len(manager.servers) == 2
    assert manager.get_server("filesystem") is not None
    assert manager.get_server("filesystem").status == "disconnected"


def test_mcp_manager_empty():
    manager = McpManager({})
    assert len(manager.servers) == 0


def test_mcp_server_status_fields():
    status = McpServerStatus(name="test", command="echo")
    assert status.status == "disconnected"
    assert status.tools == []
    assert status.error is None
```

- [ ] **Step 7: Run tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_mcp.py -v`
Expected: 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml lc_agent/config/schema.py lc_agent/mcp/ tests/test_mcp.py
git commit -m "feat: MCP manager with server lifecycle and tool discovery"
```

---

### Task 4: MCP API + App Integration

**Files:**
- Create: `lc_agent/server/routes/mcp.py`
- Modify: `lc_agent/app.py` — init McpManager
- Modify: `lc_agent/server/app.py` — register MCP router

- [ ] **Step 1: Create `lc_agent/server/routes/mcp.py`**

```python
from fastapi import APIRouter, Request

router = APIRouter(tags=["mcp"])


@router.get("/mcp")
def list_mcp_servers(request: Request):
    """List MCP servers with their status."""
    manager = getattr(request.app.state, "mcp_manager", None)
    if manager is None:
        return []
    return [
        {
            "name": s.name,
            "command": s.command,
            "status": s.status,
            "tools": s.tools,
            "error": s.error,
        }
        for s in manager.servers
    ]
```

- [ ] **Step 2: Register MCP router in `lc_agent/server/app.py`**

- [ ] **Step 3: Modify `lc_agent/app.py` — init McpManager**

In `__init__`:
```python
from lc_agent.mcp.manager import McpManager
mcp_config = config.get("mcp_servers", {})
self.mcp_manager = McpManager(mcp_config)
self.fastapi_app.state.mcp_manager = self.mcp_manager
```

- [ ] **Step 4: Run all tests**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass (65+)

- [ ] **Step 5: Commit**

```bash
git add lc_agent/server/routes/mcp.py lc_agent/server/app.py lc_agent/app.py
git commit -m "feat: MCP status API + app integration"
```

---

### Task 5: Frontend MCP + Skills Display

**Files:**
- Modify: `frontend/src/api/http.ts` — add mcp + skills endpoints
- Modify: `frontend/src/stores/tools.ts` — fetch mcp/skills data
- Modify: `frontend/src/components/layout/RightPanel.vue` — display mcp/skills

- [ ] **Step 1: Add endpoints to `frontend/src/api/http.ts`**

```typescript
getMcpServers: () => fetchApi<any[]>('/mcp'),
getSkills: () => fetchApi<any[]>('/skills'),
```

- [ ] **Step 2: Update `frontend/src/stores/tools.ts`**

Add refs and fetch in init():
```typescript
const mcpServers = ref<any[]>([])
const skills = ref<any[]>([])

// In init():
const [groupsData, modelsData, mcpData, skillsData] = await Promise.all([
  api.getToolGroups(),
  api.getModels(),
  api.getMcpServers(),
  api.getSkills(),
])
mcpServers.value = mcpData
skills.value = skillsData
```

Return them from the store.

- [ ] **Step 3: Update `frontend/src/components/layout/RightPanel.vue`**

Replace the MCP and Skills placeholder sections with real data display:

```vue
<div class="panel-section">
  <h4>MCP 服务器</h4>
  <div v-for="server in toolsStore.mcpServers" :key="server.name" class="mcp-item">
    <span>{{ server.name }}</span>
    <el-tag size="small" :type="server.status === 'connected' ? 'success' : 'danger'">
      {{ server.status }}
    </el-tag>
  </div>
  <p v-if="!toolsStore.mcpServers.length" class="empty-hint">暂无 MCP 服务器</p>
</div>

<div class="panel-section">
  <h4>Skills</h4>
  <div v-for="skill in toolsStore.skills" :key="skill.name" class="skill-item">
    <span class="skill-name">{{ skill.name }}</span>
    <span class="skill-desc">{{ skill.description }}</span>
  </div>
  <p v-if="!toolsStore.skills.length" class="empty-hint">暂无 Skills</p>
</div>
```

- [ ] **Step 4: Build frontend**

Run: `cd D:\codes\lc-agent\frontend && npx vite build`

- [ ] **Step 5: Commit**

```bash
git add frontend/ lc_agent/web/dist/
git commit -m "feat: frontend displays MCP servers and Skills in right panel"
```

---

## Summary

After 5 tasks:
- Skills discovered from `./skills/` dir, parsed SKILL.md frontmatter
- Skills content injected into agent system prompt based on preset
- MCP servers configured in config.jsonc, manager tracks status
- REST APIs: GET /api/skills, GET /api/mcp
- Frontend Right Panel shows real MCP + Skills data
- 65+ backend tests passing
