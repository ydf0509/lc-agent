import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.mcp.manager import McpServerStatus
from lc_agent.tools import tool, ToolRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}
    ToolRegistry._instance = None
    yield
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}
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
        group_ids = [g["id"] for g in data]
        assert "web" in group_ids
        assert "filesystem" in group_ids
        web_group = next(g for g in data if g["id"] == "web")
        assert len(web_group["tools"]) == 2


@pytest.mark.asyncio
async def test_toggle_tool_group_increments_mcp_generation(app_with_tools):
    """Toggling a tool group must invalidate cached agents by incrementing _mcp_generation."""
    transport = ASGITransport(app=app_with_tools.fastapi_app)
    engine = app_with_tools.engine
    gen_before = engine._mcp_generation

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/tools/groups/web/toggle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False

    assert engine._mcp_generation == gen_before + 1

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/tools/groups/web/toggle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True

    assert engine._mcp_generation == gen_before + 2


@pytest.mark.asyncio
async def test_toggle_mcp_server_increments_mcp_generation(app_with_tools):
    """Toggling an MCP server must invalidate cached agents."""
    app = app_with_tools
    engine = app.engine

    # Manually inject a fake MCP server status
    from lc_agent.mcp.manager import McpManager
    mcp_manager = McpManager({"fake_server": {"command": "echo", "enabled": True}})
    mcp_manager._servers["fake_server"].status = "connected"
    app.fastapi_app.state.mcp_manager = mcp_manager

    gen_before = engine._mcp_generation

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/mcp/fake_server/toggle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False

    assert engine._mcp_generation == gen_before + 1
