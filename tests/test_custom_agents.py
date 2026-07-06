import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import AsyncMock, MagicMock
from lc_agent.app import LcAgentApp


@pytest.fixture
def app_instance():
    config = {
        "provider": {},
        "agent": {"system_prompt": "Hi", "default_model": ""},
    }
    return LcAgentApp(config)


def test_add_agent_registers_custom(app_instance):
    """add_agent should store the graph and create a preset."""
    mock_graph = MagicMock()
    mock_graph.ainvoke = MagicMock()
    mock_graph.astream_events = MagicMock()

    app_instance.add_agent("my_agent", mock_graph, description="My custom agent")

    # Should be accessible via engine
    assert "my_agent" in app_instance.engine._agents
    assert app_instance.engine._agents["my_agent"] is mock_graph


def test_add_agent_creates_preset(app_instance):
    """add_agent should create a preset with source=code."""
    mock_graph = MagicMock()
    app_instance.add_agent("code_agent", mock_graph, description="Code agent")

    presets = app_instance.engine.get_presets()
    code_presets = [p for p in presets if p.id == "code_agent"]
    assert len(code_presets) == 1
    assert code_presets[0].name == "code_agent"


def test_add_agent_duplicate_raises(app_instance):
    """Adding same name twice should raise ValueError."""
    mock_graph = MagicMock()
    app_instance.add_agent("dup", mock_graph)

    with pytest.raises(ValueError, match="already registered"):
        app_instance.add_agent("dup", mock_graph)


@pytest.mark.asyncio
async def test_api_agents_includes_custom(tmp_path):
    """GET /api/agents should include custom agents with source flag."""
    from lc_agent.db.engine import init_db, reset_engine
    from tests.conftest import setup_test_auth

    reset_engine()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    await init_db(db_url)

    config = {
        "provider": {},
        "agent": {"system_prompt": "Hi", "default_model": ""},
        "database": {"url": db_url, "checkpoint_path": ":memory:"},
    }
    app_instance = LcAgentApp(config)
    headers = await setup_test_auth(app_instance.fastapi_app, db_url)

    mock_graph = MagicMock()
    app_instance.add_agent("api_agent", mock_graph, description="API test")

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance.fastapi_app),
        base_url="http://test"
    ) as client:
        resp = await client.get("/api/agents", headers=headers)
        assert resp.status_code == 200
        agents = resp.json()
        custom = [a for a in agents if a["id"] == "api_agent"]
        assert len(custom) == 1
        assert custom[0].get("source") == "code"

    reset_engine()


@pytest.mark.asyncio
async def test_api_custom_agent_not_deletable(tmp_path):
    """DELETE on custom agent should return 403."""
    from lc_agent.db.engine import init_db, reset_engine
    from tests.conftest import setup_test_auth

    reset_engine()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    await init_db(db_url)

    config = {
        "provider": {},
        "agent": {"system_prompt": "Hi", "default_model": ""},
        "database": {"url": db_url, "checkpoint_path": ":memory:"},
    }
    app_instance = LcAgentApp(config)
    headers = await setup_test_auth(app_instance.fastapi_app, db_url)

    mock_graph = MagicMock()
    app_instance.add_agent("protected", mock_graph)

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance.fastapi_app),
        base_url="http://test"
    ) as client:
        resp = await client.delete("/api/agents/protected", headers=headers)
        assert resp.status_code == 403

    reset_engine()




def test_add_agent_wraps_graph_with_lc_agent_name_metadata():
    """add_agent should call with_config on graphs that support Runnable metadata."""
    from lc_agent.app import LcAgentApp

    wrapped = None

    class GraphWithConfig:
        async def ainvoke(self, *args, **kwargs):
            return {"messages": []}

        async def astream_events(self, *args, **kwargs):
            if False:
                yield {}

        def with_config(self, config):
            nonlocal wrapped
            wrapped = config
            return self

    app = LcAgentApp({"agent": {"default_model": "model-a"}})
    graph = GraphWithConfig()
    app.add_agent("research", graph, "Research graph")

    assert wrapped is not None
    assert wrapped["metadata"]["lc_agent_name"] == "research"
    assert wrapped["run_name"] == "research"


def test_add_agent_marks_code_agent_as_self_contained():
    from lc_agent.app import LcAgentApp

    class DummyGraph:
        async def ainvoke(self, *args, **kwargs):
            return {"messages": []}

        async def astream_events(self, *args, **kwargs):
            if False:
                yield {}

    app = LcAgentApp({"agent": {"default_model": "model-a"}})
    graph = DummyGraph()

    app.add_agent("research", graph, "Research graph")

    preset = app.engine._custom_presets["research"]
    assert app.engine._agents["research"] is graph
    assert preset.source == "code"
    assert preset.default_model == "custom"
    assert preset.system_prompt == "Research graph"
    assert preset.allowed_tool_groups == []
    assert preset.allowed_mcp_servers == []
    assert preset.allowed_skills == []
    assert preset.default_enabled is False


def test_code_agent_resolution_returns_registered_graph_without_rebuild(monkeypatch):
    from lc_agent.app import LcAgentApp

    class DummyGraph:
        async def ainvoke(self, *args, **kwargs):
            return {"messages": []}

        async def astream_events(self, *args, **kwargs):
            if False:
                yield {}

    app = LcAgentApp({"agent": {"default_model": "model-a"}})
    graph = DummyGraph()
    app.add_agent("research", graph, "Research graph")
    app.engine._mcp_generation = 99

    def fail_build_agent(*args, **kwargs):
        raise AssertionError("code agents must not be rebuilt through build_agent")

    monkeypatch.setattr(app.engine, "build_agent", fail_build_agent)

    resolved = app.engine._get_or_build_agent("research", model_id="some-ui-model")

    assert resolved is graph
    assert "research::model::some-ui-model" not in app.engine._agents


@pytest.mark.asyncio
async def test_code_agent_chat_stream_does_not_receive_framework_memory_context():
    from lc_agent.app import LcAgentApp

    captured = {}

    class DummyGraph:
        async def astream_events(self, payload, **kwargs):
            captured["payload"] = payload
            captured["kwargs"] = kwargs
            if False:
                yield {}

    app = LcAgentApp({"agent": {"default_model": "model-a"}})
    app.engine._store = object()
    app.add_agent("research", DummyGraph(), "Research graph")

    events = [
        event async for event in app.engine.chat_stream(
            "hello",
            "thread-1",
            preset_id="research",
            user_id="user-123",
        )
    ]

    assert events == []
    assert "context" not in captured["kwargs"]
    assert captured["kwargs"]["config"]["configurable"]["thread_id"] == "thread-1"
    assert captured["kwargs"]["version"] == "v2"
