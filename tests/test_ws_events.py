import pytest
from unittest.mock import AsyncMock, MagicMock

from lc_agent.server.websocket import ChatWebSocketHandler
from lc_agent.core.engine import AgentEngine


@pytest.fixture
def handler():
    engine = MagicMock(spec=AgentEngine)
    return ChatWebSocketHandler(engine)


@pytest.mark.asyncio
async def test_send_event_token(handler):
    """on_chat_model_stream should send token event."""
    ws = AsyncMock()
    chunk = MagicMock()
    chunk.content = "Hello"

    event = {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
    await handler._send_event(ws, event)

    ws.send_json.assert_called_once_with({"type": "token", "content": "Hello"})


@pytest.mark.asyncio
async def test_send_event_tool_call(handler):
    """on_tool_start should send tool_call with args."""
    ws = AsyncMock()
    event = {
        "event": "on_tool_start",
        "name": "get_weather",
        "run_id": "abc-123",
        "data": {"input": {"city": "Beijing"}},
    }
    await handler._send_event(ws, event)

    ws.send_json.assert_called_once()
    call_args = ws.send_json.call_args[0][0]
    assert call_args["type"] == "tool_call"
    assert call_args["name"] == "get_weather"
    assert call_args["args"] == {"city": "Beijing"}


@pytest.mark.asyncio
async def test_send_event_tool_result(handler):
    """on_tool_end should send tool_result."""
    ws = AsyncMock()
    event = {
        "event": "on_tool_end",
        "name": "get_weather",
        "data": {"output": "Sunny, 25°C"},
    }
    await handler._send_event(ws, event)

    ws.send_json.assert_called_once()
    call_args = ws.send_json.call_args[0][0]
    assert call_args["type"] == "tool_result"
    assert call_args["name"] == "get_weather"
    assert "Sunny" in call_args["result"]


@pytest.mark.asyncio
async def test_send_event_ignores_irrelevant(handler):
    """Non-relevant events should not send anything."""
    ws = AsyncMock()
    event = {"event": "on_chain_start", "data": {}}
    await handler._send_event(ws, event)

    ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_passes_preset_id(handler):
    """handle_message should pass preset_id from data to chat_stream."""
    ws = AsyncMock()

    async def fake_stream(msg, tid, pid):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="hi")}}

    handler.engine.chat_stream = fake_stream

    data = {"type": "message", "content": "hello", "preset_id": "my_agent"}
    await handler.handle_message(ws, "thread-1", data)

    # Should have sent at least a token event and a done event
    calls = ws.send_json.call_args_list
    types = [c[0][0]["type"] for c in calls]
    assert "token" in types
    assert "done" in types
