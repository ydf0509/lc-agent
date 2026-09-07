import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.db.engine import get_async_session, init_db, reset_engine
from lc_agent.db.models_auth import User, UserAgentAccess
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
        assert any(a["id"] == "chat" for a in data)


@pytest.mark.asyncio
async def test_authorized_user_can_list_available_subagents(app_and_headers, setup):
    app, admin_headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "shared-agent",
            "system_prompt": "Shared agent",
            "default_model": "gpt-4",
            "default_delegation_description": "可处理共享委派任务",
            "can_be_subagent": True,
        }, headers=admin_headers)
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["id"]

    auth_service = app.fastapi_app.state.auth_service
    user_id = "user2-id"
    async with get_async_session(setup) as db:
        db.add(User(
            id=user_id,
            username="user2",
            password_hash=auth_service.hash_password("pass"),
            role="user",
        ))
        db.add_all([
            UserAgentAccess(user_id=user_id, agent_id="chat"),
            UserAgentAccess(user_id=user_id, agent_id=agent_id),
        ])
        await db.commit()

    user2_headers = {
        "Authorization": f"Bearer {auth_service.create_token(user_id=user_id, username='user2', role='user')}"
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents_resp = await client.get("/api/agents", headers=user2_headers)
        available_resp = await client.get("/api/agents/available-subagents", headers=user2_headers)

    assert agents_resp.status_code == 200
    assert any(agent["id"] == agent_id for agent in agents_resp.json())
    assert available_resp.status_code == 200
    assert {item["id"] for item in available_resp.json()} == {agent_id}


@pytest.mark.asyncio
async def test_create_agent(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "code-assistant",
            "system_prompt": "You are a coding expert.",
            "default_model": "gpt-4",
            "allowed_tool_groups": ["filesystem"],
        }
        resp = await client.post("/api/agents", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "code-assistant"
        assert "id" in data
        assert data["id"] != "__default__"


@pytest.mark.asyncio
async def test_update_agent(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "test-agent",
            "system_prompt": "Original",
            "default_model": "gpt-4",
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "name": "updated-agent",
            "system_prompt": "Updated prompt",
            "default_model": "gpt-4",
        }, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "updated-agent"
        assert update_resp.json()["system_prompt"] == "Updated prompt"


@pytest.mark.asyncio
async def test_update_agent_invalidates_model_variant_cache(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "cache-agent",
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
            "name": "temp-agent",
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
        resp = await client.delete("/api/agents/chat", headers=headers)
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


def test_activate_agent_restores_skills_to_default_enabled_state():
    from types import SimpleNamespace
    from lc_agent.core.engine import AgentEngine
    from lc_agent.core.models import AgentPreset
    from lc_agent.server.routes.agents import activate_agent

    class FakeLoader:
        def __init__(self):
            self.disabled_skills = {"web-search"}

        def list_all_skills(self):
            return [SimpleNamespace(name="web-search"), SimpleNamespace(name="pdf")]

    engine = AgentEngine({"agent": {"default_model": "model-a"}})
    engine._presets["power"] = AgentPreset(
        id="power",
        name="power",
        system_prompt="Power agent",
        default_model="model-a",
        source="user",
        allowed_tool_groups=None,
        allowed_mcp_servers=None,
        allowed_skills=None,
        default_enabled=True,
    )
    engine._mcp_generation = 3
    loader = FakeLoader()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(mcp_manager=None, filtered_loader=loader)))

    result = activate_agent("power", request, engine, admin=SimpleNamespace(role="admin"))

    assert loader.disabled_skills == set()
    assert result["changed_skills"] == ["web-search"]
    assert engine._mcp_generation == 4


def test_activate_agent_disables_allowed_skills_when_default_disabled():
    from types import SimpleNamespace
    from lc_agent.core.engine import AgentEngine
    from lc_agent.core.models import AgentPreset
    from lc_agent.server.routes.agents import activate_agent

    class FakeLoader:
        def __init__(self):
            self.disabled_skills = set()

        def list_all_skills(self):
            return [SimpleNamespace(name="web-search"), SimpleNamespace(name="pdf")]

    engine = AgentEngine({"agent": {"default_model": "model-a"}})
    engine._presets["skill-tester"] = AgentPreset(
        id="skill-tester",
        name="skill-tester",
        system_prompt="Empty agent",
        default_model="model-a",
        source="user",
        allowed_tool_groups=None,
        allowed_mcp_servers=None,
        allowed_skills=["web-search"],
        default_enabled=False,
    )
    engine._mcp_generation = 3
    loader = FakeLoader()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(mcp_manager=None, filtered_loader=loader)))

    result = activate_agent("skill-tester", request, engine, admin=SimpleNamespace(role="admin"))

    assert loader.disabled_skills == {"web-search"}
    assert result["changed_skills"] == ["web-search"]
    assert engine._mcp_generation == 4


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


@pytest.mark.asyncio
async def test_create_agent_persists_general_purpose_subagent_flag(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "delegating-agent",
            "system_prompt": "Delegate when useful.",
            "default_model": "gpt-4",
            "enable_general_purpose_subagent": True,
        }
        create_resp = await client.post("/api/agents", json=payload, headers=headers)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["enable_general_purpose_subagent"] is True

        list_resp = await client.get("/api/agents", headers=headers)
        assert list_resp.status_code == 200
        listed = next(a for a in list_resp.json() if a["id"] == created["id"])
        assert listed["enable_general_purpose_subagent"] is True


@pytest.mark.asyncio
async def test_create_agent_accepts_subagents_payload(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sub_resp = await client.post("/api/agents", json={
            "name": "payload-subagent",
            "system_prompt": "Handle delegated work.",
            "default_model": "gpt-4",
            "default_delegation_description": "可处理委派的研究与分析任务",
            "can_be_subagent": True,
        }, headers=headers)
        assert sub_resp.status_code == 201
        sub_id = sub_resp.json()["id"]

        payload = {
            "name": "delegating-agent",
            "system_prompt": "Delegate when useful.",
            "default_model": "gpt-4",
            "subagents": [
                {
                    "agent_id": sub_id,
                    "delegation_description": "当你需要查询 funboost 知识时调用它",
                }
            ],
        }
        create_resp = await client.post("/api/agents", json=payload, headers=headers)

        assert create_resp.status_code == 201
        created = create_resp.json()
        assert "subagent_ids" not in created
        assert created["subagents"][0]["agent_id"] == sub_id
        assert created["subagents"][0]["delegation_description"] == "当你需要查询 funboost 知识时调用它"

        list_resp = await client.get("/api/agents", headers=headers)
        assert list_resp.status_code == 200
        listed = next(a for a in list_resp.json() if a["id"] == created["id"])
        assert "subagent_ids" not in listed
        assert listed["subagents"][0]["agent_id"] == sub_id


@pytest.mark.asyncio
async def test_create_agent_rejects_can_be_subagent_without_default_description(app_and_headers):
    """can_be_subagent=True requires the agent's own default delegation description."""
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "blank-description-subagent",
            "system_prompt": "Handle delegated work.",
            "default_model": "gpt-4",
            "can_be_subagent": True,
        }, headers=headers)

        assert create_resp.status_code == 422
        assert "触发描述" in create_resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_agent_allows_blank_override_when_subagent_has_default(app_and_headers):
    """Blank override is fine when the subagent itself defines a default delegation description."""
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sub_resp = await client.post("/api/agents", json={
            "name": "researcher",
            "system_prompt": "Research things.",
            "default_model": "gpt-4",
            "default_delegation_description": "当需要调研资料时调用它",
            "can_be_subagent": True,
        }, headers=headers)
        assert sub_resp.status_code == 201
        sub_id = sub_resp.json()["id"]

        payload = {
            "name": "delegating-agent",
            "system_prompt": "Delegate when useful.",
            "default_model": "gpt-4",
            "subagents": [
                {
                    "agent_id": sub_id,
                    "delegation_description": "",
                }
            ],
        }
        create_resp = await client.post("/api/agents", json=payload, headers=headers)

        assert create_resp.status_code == 201
        assert create_resp.json()["subagents"][0]["delegation_description"] == ""


@pytest.mark.asyncio
async def test_create_agent_persists_default_delegation_description(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "researcher",
            "system_prompt": "Research things.",
            "default_model": "gpt-4",
            "default_delegation_description": "当需要调研资料时调用它",
            "can_be_subagent": True,
        }, headers=headers)
        assert create_resp.status_code == 201
        assert create_resp.json()["default_delegation_description"] == "当需要调研资料时调用它"

        list_resp = await client.get("/api/agents", headers=headers)
        listed = next(a for a in list_resp.json() if a["id"] == create_resp.json()["id"])
        assert listed["default_delegation_description"] == "当需要调研资料时调用它"

        available_resp = await client.get("/api/agents/available-subagents", headers=headers)
        available = next(a for a in available_resp.json() if a["id"] == create_resp.json()["id"])
        assert available["description"] == "当需要调研资料时调用它"


@pytest.mark.asyncio
async def test_update_agent_changes_default_delegation_description(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "researcher",
            "system_prompt": "Research things.",
            "default_model": "gpt-4",
            "default_delegation_description": "可处理委派任务",
            "can_be_subagent": True,
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "default_delegation_description": "当需要深入研究时调用它",
        }, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["default_delegation_description"] == "当需要深入研究时调用它"
        assert update_resp.json()["can_be_subagent"] is True

        available_resp = await client.get("/api/agents/available-subagents", headers=headers)
        available = next(a for a in available_resp.json() if a["id"] == agent_id)
        assert available["description"] == "当需要深入研究时调用它"


@pytest.mark.asyncio
async def test_update_agent_persists_general_purpose_subagent_flag(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "delegating-agent",
            "system_prompt": "Original",
            "default_model": "gpt-4",
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "enable_general_purpose_subagent": True,
        }, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["enable_general_purpose_subagent"] is True

        second_update = await client.put(f"/api/agents/{agent_id}", json={
            "enable_general_purpose_subagent": False,
        }, headers=headers)
        assert second_update.status_code == 200
        assert second_update.json()["enable_general_purpose_subagent"] is False


@pytest.mark.asyncio
async def test_update_agent_replaces_subagents_payload(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        subagent_resp = await client.post("/api/agents", json={
            "name": "custom-subagent",
            "system_prompt": "Handle delegated work.",
            "default_model": "gpt-4",
            "default_delegation_description": "可处理委派任务",
            "can_be_subagent": True,
        }, headers=headers)
        assert subagent_resp.status_code == 201
        subagent_id = subagent_resp.json()["id"]

        create_resp = await client.post("/api/agents", json={
            "name": "delegating-agent",
            "system_prompt": "Original",
            "default_model": "gpt-4",
            "subagents": [
                {
                    "agent_id": subagent_id,
                    "delegation_description": "旧描述",
                }
            ],
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "subagents": [
                {
                    "agent_id": subagent_id,
                    "delegation_description": "新描述",
                }
            ],
        }, headers=headers)

        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert "subagent_ids" not in updated
        assert updated["subagents"] == [
            {
                "agent_id": subagent_id,
                "delegation_description": "新描述",
            }
        ]


@pytest.mark.asyncio
async def test_update_agent_serializes_subagents_for_db_json_column(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        subagent_ids = []
        for name in ("serializable-subagent-one", "serializable-subagent-two"):
            subagent_resp = await client.post("/api/agents", json={
                "name": name,
                "system_prompt": "Handle delegated work.",
                "default_model": "gpt-4",
                "default_delegation_description": "可处理委派任务",
                "can_be_subagent": True,
            }, headers=headers)
            assert subagent_resp.status_code == 201
            subagent_ids.append(subagent_resp.json()["id"])

        create_resp = await client.post("/api/agents", json={
            "name": "delegating-agent",
            "system_prompt": "Original",
            "default_model": "gpt-4",
        }, headers=headers)
        agent_id = create_resp.json()["id"]

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "subagents": [
                {
                    "agent_id": subagent_ids[0],
                    "delegation_description": "当需要分析数据时调用它",
                },
                {
                    "agent_id": subagent_ids[1],
                    "delegation_description": "当需要隔离执行简单任务时调用它",
                },
            ],
        }, headers=headers)

        assert update_resp.status_code == 200
        assert update_resp.json()["subagents"] == [
            {
                "agent_id": subagent_ids[0],
                "delegation_description": "当需要分析数据时调用它",
            },
            {
                "agent_id": subagent_ids[1],
                "delegation_description": "当需要隔离执行简单任务时调用它",
            },
        ]


@pytest.mark.asyncio
async def test_create_agent_rejects_nonexistent_subagent_id(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "delegating-agent",
            "system_prompt": "Delegate when useful.",
            "default_model": "gpt-4",
            "subagents": [
                {
                    "agent_id": "nonexistent-agent",
                    "delegation_description": "描述",
                }
            ],
        }
        create_resp = await client.post("/api/agents", json=payload, headers=headers)

    assert create_resp.status_code == 422


@pytest.mark.asyncio
async def test_create_agent_rejects_duplicate_subagent_id(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "delegating-agent",
            "system_prompt": "Delegate when useful.",
            "default_model": "gpt-4",
            "subagents": [
                {
                    "agent_id": "power",
                    "delegation_description": "描述一",
                },
                {
                    "agent_id": "power",
                    "delegation_description": "描述二",
                }
            ],
        }
        create_resp = await client.post("/api/agents", json=payload, headers=headers)

    assert create_resp.status_code == 422
