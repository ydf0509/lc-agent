import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.tools.registry import ToolRegistry


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
