import pytest
from unittest.mock import AsyncMock, MagicMock
from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset
from lc_agent.server.websocket import ChatWebSocketHandler
from lc_agent.tools.registry import ToolRegistry, tool


@pytest.fixture
def hitl_engine():
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None

    @tool(group="filesystem")
    def delete_file(path: str) -> str:
        """Delete a file."""
        return "deleted"

    config = {
        "provider": {
            "test": {
                "api_key": "test-key",
                "base_url": "http://localhost:11434/v1",
                "models": [{"id": "test-model"}],
            }
        },
        "agent": {
            "system_prompt": "You are helpful.",
            "default_model": "test-model",
        },
    }
    engine = AgentEngine(config)
    yield engine
    ToolRegistry._global_tools = {}
    ToolRegistry._instance = None


def test_build_agent_with_dangerous_tools(hitl_engine):
    """Agent with dangerous_tools should have interrupt_before set."""
    preset = AgentPreset(
        id="test-hitl",
        name="HITL Agent",
        system_prompt="Be careful.",
        default_model="test-model",
        dangerous_tools=["delete_file", "rm_rf"],
    )
    agent = hitl_engine.build_agent(preset)
    assert agent is not None


def test_build_agent_without_dangerous_tools(hitl_engine):
    """Agent without dangerous_tools should not interrupt."""
    preset = AgentPreset(
        id="test-safe",
        name="Safe Agent",
        system_prompt="Be safe.",
        default_model="test-model",
        dangerous_tools=[],
    )
    agent = hitl_engine.build_agent(preset)
    assert agent is not None


@pytest.fixture
def ws_handler():
    engine = MagicMock()
    return ChatWebSocketHandler(engine)


@pytest.mark.asyncio
async def test_interrupt_response_resumes_agent(ws_handler):
    """interrupt_response should invoke graph with Command(resume=...)."""
    ws = AsyncMock()

    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(return_value={"messages": []})

    async def fake_stream_after_resume(*a, **kw):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Approved!")}}

    mock_agent.astream_events = fake_stream_after_resume
    ws_handler.engine._agents = {"test-preset": mock_agent}

    data = {
        "type": "interrupt_response",
        "approved": True,
        "thread_id": "thread-1",
        "preset_id": "test-preset",
    }
    await ws_handler.handle_message(ws, "thread-1", data)

    assert ws.send_json.called
