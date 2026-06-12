# tests/test_integration.py
"""End-to-end integration test for lc_agent framework."""
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent import LcAgentApp, load_config, tool
from lc_agent.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry between tests."""
    ToolRegistry._instance = None
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}
    yield
    ToolRegistry._instance = None
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}


@pytest.fixture
def config(sample_config):
    return sample_config


@pytest.fixture
def lc_app(config):
    """Create LcAgentApp instance with custom tools."""
    @tool(group="math")
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @tool(group="text")
    def reverse(text: str) -> str:
        """Reverse a string."""
        return text[::-1]

    return LcAgentApp(config)


class TestIntegration:
    async def test_app_starts_and_health_works(self, lc_app):
        transport = ASGITransport(app=lc_app.fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_tools_registered(self, lc_app):
        tools = lc_app.engine.tool_registry.get_all_tools()
        tool_names = [t.name for t in tools]
        assert "math__add" in tool_names
        assert "text__reverse" in tool_names

    def test_tool_groups(self, lc_app):
        groups = lc_app.engine.tool_registry.get_group_names()
        assert "math" in groups
        assert "text" in groups

    def test_engine_has_models(self, lc_app):
        models = lc_app.engine.get_models()
        assert len(models) > 0
        assert models[0].id == "test-model"

    def test_default_preset(self, lc_app):
        preset = lc_app.engine.get_default_preset()
        assert preset.system_prompt == "You are a helpful assistant."
        assert preset.default_model == "test-model"

    def test_tool_filtering_none_allows_all(self, lc_app):
        tools = lc_app.engine.tool_registry.get_filtered_tools(allowed_groups=None)
        assert len(tools) == 2

    def test_tool_filtering_specific_group(self, lc_app):
        tools = lc_app.engine.tool_registry.get_filtered_tools(allowed_groups=["math"])
        assert len(tools) == 1
        assert tools[0].name == "math__add"

    def test_tool_filtering_empty_blocks_all(self, lc_app):
        tools = lc_app.engine.tool_registry.get_filtered_tools(allowed_groups=[])
        assert len(tools) == 0

    async def test_api_docs_accessible(self, lc_app):
        transport = ASGITransport(app=lc_app.fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/openapi.json")
            assert response.status_code == 200
            data = response.json()
            assert data["info"]["title"] == "lc_agent"
