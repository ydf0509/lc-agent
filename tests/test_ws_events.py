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
    chunk.additional_kwargs = {}

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
        chunk = MagicMock()
        chunk.content = "hi"
        chunk.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

    handler.engine.chat_stream = fake_stream

    data = {"type": "message", "content": "hello", "preset_id": "my_agent"}
    await handler.handle_message(ws, "thread-1", data)

    calls = ws.send_json.call_args_list
    types = [c[0][0]["type"] for c in calls]
    assert "token" in types
    assert "done" in types


@pytest.mark.asyncio
async def test_handle_message_passes_selected_model(handler):
    """handle_message should pass the frontend selected model to chat_stream."""
    ws = AsyncMock()
    captured = {}

    async def fake_stream(msg, tid, pid, model_id=""):
        captured["model_id"] = model_id
        chunk = MagicMock()
        chunk.content = "hi"
        chunk.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

    handler.engine.chat_stream = fake_stream

    data = {
        "type": "message",
        "content": "hello",
        "preset_id": "my_agent",
        "model": "ark-deepseek-v4-flash",
    }
    await handler.handle_message(ws, "thread-1", data)

    assert captured["model_id"] == "ark-deepseek-v4-flash"


@pytest.mark.asyncio
async def test_first_message_sends_title_update_immediately(handler):
    """First message should send title_update with user content before streaming."""
    ws = AsyncMock()

    async def fake_stream(msg, tid, pid):
        chunk = MagicMock()
        chunk.content = "response"
        chunk.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

    handler.engine.chat_stream = fake_stream

    data = {"type": "message", "content": "用户的第一条消息", "preset_id": "__chat__"}
    await handler.handle_message(ws, "thread-new", data)

    calls = ws.send_json.call_args_list
    types = [c[0][0]["type"] for c in calls]

    # title_update should be the FIRST message sent
    assert types[0] == "title_update", f"First message should be title_update, got: {types}"
    title_msg = calls[0][0][0]
    assert title_msg["thread_id"] == "thread-new"
    assert title_msg["title"] == "用户的第一条消息"


@pytest.mark.asyncio
async def test_second_message_does_not_send_title_update(handler):
    """Second message should NOT send another title_update."""
    ws = AsyncMock()

    async def fake_stream(msg, tid, pid):
        chunk = MagicMock()
        chunk.content = "ok"
        chunk.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

    handler.engine.chat_stream = fake_stream

    # First message
    handler._message_counts["thread-existing"] = 1
    data = {"type": "message", "content": "第二条消息"}
    await handler.handle_message(ws, "thread-existing", data)

    calls = ws.send_json.call_args_list
    types = [c[0][0]["type"] for c in calls]
    assert "title_update" not in types


@pytest.mark.asyncio
async def test_title_truncated_to_30_chars(handler):
    """Long messages should be truncated to 30 chars for title."""
    ws = AsyncMock()

    async def fake_stream(msg, tid, pid):
        chunk = MagicMock()
        chunk.content = "x"
        chunk.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

    handler.engine.chat_stream = fake_stream

    long_msg = "这是一条非常非常长的消息用来测试标题截断功能是否正确工作不超过30字"
    data = {"type": "message", "content": long_msg}
    await handler.handle_message(ws, "thread-long", data)

    calls = ws.send_json.call_args_list
    title_msg = calls[0][0][0]
    assert title_msg["type"] == "title_update"
    assert len(title_msg["title"]) <= 30


@pytest.mark.asyncio
async def test_handle_message_llm_error(handler):
    """LLM errors should send error event, not crash."""
    ws = AsyncMock()

    async def failing_stream(msg, tid, pid):
        raise RuntimeError("API key invalid")
        yield  # noqa: unreachable - makes it a generator

    handler.engine.chat_stream = failing_stream

    data = {"type": "message", "content": "hi"}
    await handler.handle_message(ws, "thread-1", data)

    calls = ws.send_json.call_args_list
    error_calls = [c for c in calls if c[0][0].get("type") == "error"]
    assert len(error_calls) == 1
    assert "API key invalid" in error_calls[0][0][0]["message"]


@pytest.mark.asyncio
async def test_handle_message_persists_user_and_assistant_ui_messages(handler):
    from lc_agent.db.engine import get_async_session, init_db, reset_engine
    from lc_agent.db.repository import ChatUiMessageRepository

    reset_engine()
    await init_db("sqlite+aiosqlite:///:memory:")
    ws = AsyncMock()

    async def fake_stream(msg, tid, pid):
        chunk = MagicMock()
        chunk.content = "先查资料。"
        chunk.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
        yield {
            "event": "on_tool_start",
            "name": "nbrag_search",
            "run_id": "run-1",
            "data": {"input": {"query": "funboost"}},
        }
        yield {
            "event": "on_tool_end",
            "name": "nbrag_search",
            "run_id": "run-1",
            "data": {"output": "funboost 是任务队列框架"},
        }
        output = MagicMock()
        output.usage_metadata = {
            "input_tokens": 10,
            "output_tokens": 6,
            "total_tokens": 16,
            "input_token_details": {"cache_read": 2},
        }
        yield {"event": "on_chat_model_end", "data": {"output": output}}
        chunk2 = MagicMock()
        chunk2.content = "适合异步任务。"
        chunk2.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk2}}

    handler.engine.chat_stream = fake_stream

    await handler.handle_message(ws, "thread-persist", {"type": "message", "content": "funboost怎么样"})

    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        records = await ChatUiMessageRepository(session).list_by_session("thread-persist")

    assert [r.role for r in records] == ["user", "assistant"]
    assert records[0].content == "funboost怎么样"
    assert "<!--TOOL:0-->" in records[1].content
    assert records[1].tool_calls[0]["name"] == "nbrag_search"
    assert records[1].tool_calls[0]["runId"] == "run-1"
    assert records[1].tool_calls[0]["result"] == "funboost 是任务队列框架"
    assert records[1].usage["rounds"][0]["total_tokens"] == 16
