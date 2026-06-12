import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
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
