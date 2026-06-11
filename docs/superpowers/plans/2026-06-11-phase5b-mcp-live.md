# Phase 5b: MCP Live Connection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect MCP servers in the background after app startup, convert discovered tools to LangChain `StructuredTool`, and register them into the tool registry so agents can call them.

**Architecture:** App startup triggers `asyncio.create_task` for MCP connection. Each connected server's tools are dynamically converted to `StructuredTool` with proper schemas and registered under `mcp__{server}` group. The MCP session is kept alive for tool invocations.

**Tech Stack:** `mcp` SDK, `langchain_core.tools.StructuredTool`, `asyncio`, `pydantic` dynamic models

---

## File Structure

| File | Responsibility |
|------|---------------|
| `lc_agent/mcp/manager.py` | Refactor: keep sessions alive, expose tool schemas |
| `lc_agent/mcp/tool_adapter.py` | Convert MCP tools to LangChain StructuredTool |
| `lc_agent/app.py` | Background task for MCP connection |
| `tests/test_mcp_adapter.py` | Test tool conversion logic |

---

### Task 1: Refactor McpManager to keep sessions alive

**Files:**
- Modify: `lc_agent/mcp/manager.py`
- Modify: `tests/test_mcp.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mcp.py`:

```python
def test_mcp_manager_has_tool_schemas():
    """After connect, servers should have tool_schemas."""
    config = {"test": {"command": "echo"}}
    manager = McpManager(config)
    # Before connect, tool_schemas should be empty
    assert manager.get_server("test").tool_schemas == []


def test_mcp_server_status_has_tool_schemas():
    status = McpServerStatus(name="x", command="y")
    assert hasattr(status, 'tool_schemas')
    assert status.tool_schemas == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_mcp.py -v`
Expected: FAIL (McpServerStatus has no `tool_schemas` field)

- [ ] **Step 3: Add tool_schemas to McpServerStatus**

In `lc_agent/mcp/manager.py`, modify `McpServerStatus`:

```python
@dataclass
class McpServerStatus:
    name: str
    command: str
    status: str = "disconnected"
    tools: list[str] = field(default_factory=list)
    tool_schemas: list[dict] = field(default_factory=list)
    error: str | None = None
```

And update `_connect_server` to store schemas:

```python
async def _connect_server(self, name: str, conf: dict):
    """Connect to a single MCP server and discover tools with schemas."""
    self._servers[name].status = "connecting"
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
                tool_schemas = [
                    {
                        "name": t.name,
                        "description": getattr(t, 'description', '') or '',
                        "input_schema": getattr(t, 'inputSchema', {}) or {},
                    }
                    for t in tools_result.tools
                ]
                self._servers[name].status = "connected"
                self._servers[name].tools = tool_names
                self._servers[name].tool_schemas = tool_schemas

    except Exception as e:
        self._servers[name].status = "error"
        self._servers[name].error = str(e)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_mcp.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/mcp/manager.py tests/test_mcp.py
git commit -m "feat: McpServerStatus stores tool schemas for conversion"
```

---

### Task 2: MCP Tool → LangChain StructuredTool Adapter

**Files:**
- Modify: `lc_agent/mcp/tool_adapter.py`
- Create: `tests/test_mcp_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp_adapter.py
import pytest
from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas


def test_create_langchain_tools_basic():
    """Should create StructuredTool from MCP schema."""
    schemas = [
        {
            "name": "read_file",
            "description": "Read a file from disk",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"],
            },
        }
    ]

    tools = create_langchain_tools_from_schemas("filesystem", schemas)
    assert len(tools) == 1
    assert tools[0].name == "mcp__filesystem__read_file"
    assert "Read a file" in tools[0].description


def test_create_langchain_tools_empty():
    """Empty schemas should return empty list."""
    tools = create_langchain_tools_from_schemas("test", [])
    assert tools == []


def test_tool_has_correct_group():
    """Tool name should follow mcp__{server}__{tool} convention."""
    schemas = [{"name": "list_repos", "description": "List repos", "input_schema": {"type": "object", "properties": {}}}]
    tools = create_langchain_tools_from_schemas("github", schemas)
    assert tools[0].name == "mcp__github__list_repos"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_mcp_adapter.py -v`
Expected: FAIL (function doesn't exist)

- [ ] **Step 3: Implement tool adapter**

Replace `lc_agent/mcp/tool_adapter.py`:

```python
"""Converts MCP tool schemas into LangChain StructuredTool instances."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model


def _build_pydantic_model(tool_name: str, input_schema: dict) -> type[BaseModel]:
    """Dynamically create a Pydantic model from JSON Schema."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    fields: dict[str, Any] = {}
    for prop_name, prop_def in properties.items():
        python_type = _json_type_to_python(prop_def.get("type", "string"))
        description = prop_def.get("description", "")
        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            fields[prop_name] = (python_type | None, Field(default=None, description=description))

    if not fields:
        fields["__placeholder__"] = (str | None, Field(default=None, description="no params"))

    model_name = f"McpInput_{tool_name}"
    return create_model(model_name, **fields)


def _json_type_to_python(json_type: str) -> type:
    """Map JSON Schema type to Python type."""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, str)


def create_langchain_tools_from_schemas(
    server_name: str,
    tool_schemas: list[dict],
    invoke_fn: Any = None,
) -> list[StructuredTool]:
    """Convert MCP tool schemas to LangChain StructuredTool list.

    Args:
        server_name: MCP server name for namespacing
        tool_schemas: List of {name, description, input_schema}
        invoke_fn: Optional async callable(tool_name, args) -> result
    """
    tools = []
    for schema in tool_schemas:
        name = schema["name"]
        description = schema.get("description", "")
        input_schema = schema.get("input_schema", {"type": "object", "properties": {}})

        args_model = _build_pydantic_model(name, input_schema)
        full_name = f"mcp__{server_name}__{name}"

        if invoke_fn:
            async def _invoke(invoke=invoke_fn, tool_name=name, **kwargs):
                return await invoke(tool_name, kwargs)

            tool = StructuredTool.from_function(
                func=None,
                coroutine=_invoke,
                name=full_name,
                description=f"[MCP:{server_name}] {description}",
                args_schema=args_model,
            )
        else:
            def _placeholder(**kwargs):
                return f"MCP tool {full_name} not connected"

            tool = StructuredTool.from_function(
                func=_placeholder,
                name=full_name,
                description=f"[MCP:{server_name}] {description}",
                args_schema=args_model,
            )

        tools.append(tool)

    return tools


def mcp_tool_names_to_display(server_name: str, tool_names: list[str]) -> list[dict]:
    """Convert MCP tool names to display format."""
    return [
        {"name": f"mcp__{server_name}__{name}", "group": f"mcp__{server_name}", "description": f"MCP tool: {name}"}
        for name in tool_names
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_mcp_adapter.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add lc_agent/mcp/tool_adapter.py tests/test_mcp_adapter.py
git commit -m "feat: MCP tool adapter converts schemas to LangChain StructuredTool"
```

---

### Task 3: Background MCP connection on app startup

**Files:**
- Modify: `lc_agent/app.py`
- Modify: `lc_agent/mcp/manager.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mcp.py`:

```python
@pytest.mark.asyncio
async def test_mcp_manager_registers_tools_after_connect():
    """After connect, tools should be available via get_langchain_tools."""
    config = {}
    manager = McpManager(config)
    # With empty config, should return empty
    tools = manager.get_langchain_tools()
    assert tools == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_mcp.py::test_mcp_manager_registers_tools_after_connect -v`
Expected: FAIL (no `get_langchain_tools` method)

- [ ] **Step 3: Add get_langchain_tools to McpManager**

In `lc_agent/mcp/manager.py`, add method and import:

```python
def get_langchain_tools(self) -> list:
    """Get all connected MCP tools as LangChain StructuredTools."""
    from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas

    all_tools = []
    for server in self._servers.values():
        if server.status == "connected" and server.tool_schemas:
            tools = create_langchain_tools_from_schemas(server.name, server.tool_schemas)
            all_tools.extend(tools)
    return all_tools
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/test_mcp.py -v`
Expected: All PASS

- [ ] **Step 5: Add background task to app.py**

In `lc_agent/app.py`, inside the `async def startup():` event handler, add AFTER the checkpoint setup:

```python
import asyncio

async def _connect_mcp_background():
    try:
        await self.mcp_manager.connect_all()
        connected = [s for s in self.mcp_manager.servers if s.status == "connected"]
        if connected:
            print(f"[MCP] Connected: {[s.name for s in connected]}")
    except Exception as e:
        print(f"[MCP] Background connection error: {e}")

asyncio.create_task(_connect_mcp_background())
```

- [ ] **Step 6: Run full suite**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add lc_agent/mcp/manager.py lc_agent/app.py tests/test_mcp.py
git commit -m "feat: background MCP connection with LangChain tool registration"
```
