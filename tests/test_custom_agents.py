import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import AsyncMock, MagicMock
from lc_agent.app import LcAgentApp
from lc_agent.server.websocket import ChatWebSocketHandler


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
async def test_api_agents_includes_custom(app_instance):
    """GET /api/agents should include custom agents with source flag."""
    mock_graph = MagicMock()
    app_instance.add_agent("api_agent", mock_graph, description="API test")

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance.fastapi_app),
        base_url="http://test"
    ) as client:
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        custom = [a for a in agents if a["id"] == "api_agent"]
        assert len(custom) == 1
        assert custom[0].get("source") == "code"


@pytest.mark.asyncio
async def test_api_custom_agent_not_deletable(app_instance):
    """DELETE on custom agent should return 403."""
    mock_graph = MagicMock()
    app_instance.add_agent("protected", mock_graph)

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance.fastapi_app),
        base_url="http://test"
    ) as client:
        resp = await client.delete("/api/agents/protected")
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_websocket_uses_custom_agent(app_instance):
    """WebSocket should use pre-built graph for custom agent."""
    mock_graph = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="custom response")}}

    mock_graph.astream_events = fake_stream
    app_instance.add_agent("ws_agent", mock_graph, description="WS test")

    handler = ChatWebSocketHandler(app_instance.engine)
    ws = AsyncMock()

    data = {"type": "message", "content": "hello", "preset_id": "ws_agent"}
    await handler.handle_message(ws, "thread-1", data)

    calls = ws.send_json.call_args_list
    token_calls = [c for c in calls if c[0][0].get("type") == "token"]
    assert len(token_calls) >= 1
    assert "custom response" in token_calls[0][0][0]["content"]
