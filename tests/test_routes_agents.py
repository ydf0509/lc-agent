import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.db.engine import init_db, reset_engine
from lc_agent.tools.registry import ToolRegistry
from tests.conftest import setup_test_auth


@pytest.fixture(autouse=True)
async def setup(tmp_path):
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}
    ToolRegistry._instance = None
    reset_engine()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    await init_db(db_url)
    yield db_url
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}
    ToolRegistry._instance = None
    reset_engine()


@pytest.fixture
async def app_and_headers(setup):
    db_url = setup
    config = {
        "provider": {"openai": {"base_url": "http://fake", "api_key": "sk-fake", "models": [{"id": "gpt-4"}]}},
        "agent": {"default_model": "gpt-4", "system_prompt": "You are helpful."},
        "database": {"url": db_url, "checkpoint_path": ":memory:"},
    }
    app = LcAgentApp(config)
    headers = await setup_test_auth(app.fastapi_app, db_url)
    return app, headers


@pytest.mark.asyncio
async def test_list_agents_returns_default(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/agents", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(a["id"] == "__chat__" for a in data)


@pytest.mark.asyncio
async def test_create_agent(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "Code Assistant",
            "system_prompt": "You are a coding expert.",
            "default_model": "gpt-4",
            "allowed_tool_groups": ["filesystem"],
        }
        resp = await client.post("/api/agents", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Code Assistant"
        assert "id" in data
        assert data["id"] != "__default__"


@pytest.mark.asyncio
async def test_update_agent(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "Test Agent",
            "system_prompt": "Original",
            "default_model": "gpt-4",
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "name": "Updated Agent",
            "system_prompt": "Updated prompt",
            "default_model": "gpt-4",
        }, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Agent"
        assert update_resp.json()["system_prompt"] == "Updated prompt"


@pytest.mark.asyncio
async def test_agent_presets_persist_allowed_sub_agents(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        body = {
            "name": "Coordinator",
            "system_prompt": "Coordinate work.",
            "default_model": "",
            "allowed_tool_groups": [],
            "allowed_mcp_servers": [],
            "allowed_skills": [],
            "allowed_sub_agents": ["research_assistant"],
            "llm_params": None,
        }

        create_resp = await client.post("/api/agents", headers=headers, json=body)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["allowed_sub_agents"] == ["research_assistant"]

        agent_id = created["id"]
        update_resp = await client.put(
            f"/api/agents/{agent_id}",
            headers=headers,
            json={"allowed_sub_agents": []},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["allowed_sub_agents"] == []

        list_resp = await client.get("/api/agents", headers=headers)
        assert list_resp.status_code == 200
        listed = next(agent for agent in list_resp.json() if agent["id"] == agent_id)
        assert listed["allowed_sub_agents"] == []


@pytest.mark.asyncio
async def test_update_agent_invalidates_model_variant_cache(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "Cache Agent",
            "system_prompt": "Old prompt",
            "default_model": "gpt-4",
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        app.engine._agents[agent_id] = object()
        app.engine._agents[f"{agent_id}::model::gpt-4"] = object()
        app.engine._agent_mcp_gen[agent_id] = app.engine._mcp_generation
        app.engine._agent_mcp_gen[f"{agent_id}::model::gpt-4"] = app.engine._mcp_generation

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "system_prompt": "New prompt",
        }, headers=headers)

    assert update_resp.status_code == 200
    assert agent_id not in app.engine._agents
    assert f"{agent_id}::model::gpt-4" not in app.engine._agents
    assert agent_id not in app.engine._agent_mcp_gen
    assert f"{agent_id}::model::gpt-4" not in app.engine._agent_mcp_gen


@pytest.mark.asyncio
async def test_update_code_agent_rejects_ui_framework_config_changes(app_and_headers):
    app, headers = app_and_headers
    graph = object()
    app.add_agent("code_agent_cache", graph)
    app.engine._agents["code_agent_cache::model::gpt-4"] = object()
    app.engine._agent_mcp_gen["code_agent_cache::model::gpt-4"] = app.engine._mcp_generation

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put("/api/agents/code_agent_cache", json={
            "allowed_skills": [],
        }, headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Code agents are defined by their registered graph and cannot be edited from the UI"
    assert "code_agent_cache" in app.engine._custom_presets
    assert "code_agent_cache::model::gpt-4" in app.engine._agents


@pytest.mark.asyncio
async def test_delete_agent(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "Temp Agent",
            "system_prompt": "Temp",
            "default_model": "gpt-4",
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/agents/{agent_id}", headers=headers)
        assert del_resp.status_code == 204

        list_resp = await client.get("/api/agents", headers=headers)
        assert not any(a["id"] == agent_id for a in list_resp.json())


@pytest.mark.asyncio
async def test_cannot_delete_default(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/agents/__chat__", headers=headers)
        assert resp.status_code == 400


def test_preset_to_dict_normalizes_code_agent_capabilities():
    from lc_agent.core.models import AgentPreset
    from lc_agent.server.routes.agents import _preset_to_dict

    preset = AgentPreset(
        id="research",
        name="research",
        system_prompt="Research graph",
        default_model="custom",
        source="code",
        allowed_tool_groups=None,
        allowed_mcp_servers=None,
        allowed_skills=None,
        default_enabled=True,
    )

    data = _preset_to_dict(preset)

    assert data["source"] == "code"
    assert data["default_model"] == "custom"
    assert data["allowed_tool_groups"] == []
    assert data["allowed_mcp_servers"] == []
    assert data["allowed_skills"] == []
    assert data["default_enabled"] is False


def test_activate_code_agent_is_noop():
    from types import SimpleNamespace
    from lc_agent.core.engine import AgentEngine
    from lc_agent.core.models import AgentPreset
    from lc_agent.server.routes.agents import activate_agent

    engine = AgentEngine({"agent": {"default_model": "model-a"}})
    engine._custom_presets["research"] = AgentPreset(
        id="research",
        name="research",
        system_prompt="Research graph",
        default_model="custom",
        source="code",
        allowed_tool_groups=[],
        allowed_mcp_servers=[],
        allowed_skills=[],
        default_enabled=False,
    )
    engine._agents["research"] = object()
    engine._mcp_generation = 7
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(mcp_manager=None)))

    result = activate_agent("research", request, engine, admin=SimpleNamespace(role="admin"))

    assert result == {
        "agent_id": "research",
        "action": "none",
        "reason": "code agent is controlled by its registered graph",
    }
    assert engine._mcp_generation == 7
