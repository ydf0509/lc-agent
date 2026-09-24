"""Tests for stream_utils event conversion (replaces old WebSocket handler tests)."""
import pytest
from unittest.mock import MagicMock

from lc_agent.server.stream_utils import (
    convert_stream_event,
    accumulate_display_state,
    accumulate_usage,
    format_sse_event,
    categorize_error,
)


def test_convert_stream_event_token():
    """on_chat_model_stream should produce token event."""
    chunk = MagicMock()
    chunk.content = "Hello"
    chunk.additional_kwargs = {}

    event = {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
    results = convert_stream_event(event)

    assert len(results) == 1
    assert results[0] == ("token", {"content": "Hello"})


def test_convert_stream_event_thinking():
    """on_chat_model_stream with reasoning should produce thinking event."""
    chunk = MagicMock()
    chunk.content = ""
    chunk.additional_kwargs = {"reasoning_content": "Let me think..."}

    event = {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
    results = convert_stream_event(event)

    assert len(results) == 1
    assert results[0] == ("thinking", {"content": "Let me think..."})


def test_convert_stream_event_tool_call():
    """on_tool_start should produce tool_call event."""
    event = {
        "event": "on_tool_start",
        "name": "get_weather",
        "run_id": "abc-123",
        "data": {"input": {"city": "Beijing"}},
    }
    results = convert_stream_event(event)

    assert len(results) == 1
    etype, data = results[0]
    assert etype == "tool_call"
    assert data["name"] == "get_weather"
    assert data["args"] == {"city": "Beijing"}


def test_convert_stream_event_tool_call_uses_langgraph_task_id():
    event = {
        "event": "on_tool_start",
        "name": "ask_user",
        "run_id": "transient-run-id",
        "metadata": {"langgraph_checkpoint_ns": "tools:stable-task-id"},
        "data": {"input": {"question": "选择颜色"}},
    }

    results = convert_stream_event(event)

    assert results == [(
        "tool_call",
        {
            "name": "ask_user",
            "tool_call_id": "stable-task-id",
            "args": {"question": "选择颜色"},
        },
    )]


def test_convert_stream_event_tool_result():
    """on_tool_end should produce tool_result event."""
    event = {
        "event": "on_tool_end",
        "name": "get_weather",
        "data": {"output": "Sunny, 25°C"},
    }
    results = convert_stream_event(event)

    assert len(results) == 1
    etype, data = results[0]
    assert etype == "tool_result"
    assert data["name"] == "get_weather"
    assert "Sunny" in data["result"]


def test_convert_stream_event_tool_result_uses_langgraph_task_id():
    event = {
        "event": "on_tool_end",
        "name": "ask_user",
        "run_id": "different-transient-run-id",
        "metadata": {"langgraph_checkpoint_ns": "tools:stable-task-id"},
        "data": {"output": "用户回答: 红色"},
    }

    results = convert_stream_event(event)

    assert results == [(
        "tool_result",
        {
            "name": "ask_user",
            "tool_call_id": "stable-task-id",
            "result": "用户回答: 红色",
        },
    )]


def test_convert_stream_event_ignores_irrelevant():
    """Non-relevant events should produce no output."""
    event = {"event": "on_chain_start", "data": {}}
    results = convert_stream_event(event)
    assert results == []


def test_convert_stream_event_interrupt_pause_is_waiting_user():
    """ask_user's interrupt() must render as waiting_user, not as a tool error."""
    from langgraph.errors import GraphInterrupt
    from langgraph.types import Interrupt

    pause = GraphInterrupt([Interrupt(value={"type": "ask_user"})])
    event = {
        "event": "on_tool_error",
        "name": "ask_user",
        "run_id": "transient-run-id",
        "metadata": {"langgraph_checkpoint_ns": "tools:stable-task-id"},
        "data": {"error": pause, "input": {"questions": []}},
    }
    results = convert_stream_event(event)

    assert len(results) == 1
    etype, data = results[0]
    assert etype == "tool_result"
    assert data["tool_call_id"] == "stable-task-id"
    assert data["status"] == "waiting_user"
    assert data["is_error"] is False
    assert data["result"] == ""


def test_convert_stream_event_real_tool_error_stays_error():
    """A genuine tool exception must still be reported as an error."""
    event = {
        "event": "on_tool_error",
        "name": "search",
        "run_id": "run-1",
        "metadata": {"langgraph_checkpoint_ns": "tools:stable-task-id"},
        "data": {"error": RuntimeError("boom"), "input": {"q": "test"}},
    }
    results = convert_stream_event(event)

    assert len(results) == 1
    etype, data = results[0]
    assert etype == "tool_result"
    assert data["status"] == "error"
    assert data["is_error"] is True
    assert "boom" in data["result"]


def test_accumulate_display_state_interrupt_pause_sets_waiting_user():
    """Accumulator must not stamp the ask_user card as error on interrupt."""
    from langgraph.errors import GraphInterrupt
    from langgraph.types import Interrupt

    tools: list[dict] = [
        {"name": "ask_user", "runId": "stable-task-id", "status": "running", "startTime": 1}
    ]
    event = {
        "event": "on_tool_error",
        "name": "ask_user",
        "run_id": "transient-run-id",
        "metadata": {"langgraph_checkpoint_ns": "tools:stable-task-id"},
        "data": {
            "error": GraphInterrupt([Interrupt(value={"type": "ask_user"})]),
            "input": {"questions": []},
        },
    }

    accumulate_display_state(event, [], tools, False)

    assert tools[0]["status"] == "waiting_user"
    assert tools[0]["result"] == ""
    assert "duration" not in tools[0]
    assert "resultLength" not in tools[0]


def test_accumulate_display_state_token():
    """Token content should be appended."""
    chunk = MagicMock()
    chunk.content = "Hello"
    chunk.additional_kwargs = {}

    event = {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
    parts: list[str] = []
    tools: list[dict] = []

    in_thinking = accumulate_display_state(event, parts, tools, False)
    assert parts == ["Hello"]
    assert not in_thinking


def test_accumulate_display_state_thinking():
    """Thinking content should add THINK markers."""
    chunk = MagicMock()
    chunk.content = ""
    chunk.additional_kwargs = {"reasoning_content": "hmm"}

    event = {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
    parts: list[str] = []
    tools: list[dict] = []

    in_thinking = accumulate_display_state(event, parts, tools, False)
    assert "<!--THINK_START-->" in parts
    assert "hmm" in parts
    assert in_thinking


def test_accumulate_display_state_tool():
    """Tool start should add tool entry and marker."""
    event = {
        "event": "on_tool_start",
        "name": "search",
        "run_id": "run-1",
        "metadata": {"langgraph_checkpoint_ns": "tools:stable-task-id"},
        "data": {"input": {"q": "test"}},
    }
    parts: list[str] = []
    tools: list[dict] = []

    in_thinking = accumulate_display_state(event, parts, tools, False)
    assert len(tools) == 1
    assert tools[0]["name"] == "search"
    assert tools[0]["runId"] == "stable-task-id"
    assert tools[0]["status"] == "running"
    assert "<!--TOOL:0-->" in "".join(parts)
    assert not in_thinking


def test_accumulate_usage_basic():
    """on_chat_model_end should extract usage data."""
    output = MagicMock()
    output.usage_metadata = {
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "input_token_details": {"cache_read": 20},
        "output_token_details": {"reasoning": 10},
    }

    event = {"event": "on_chat_model_end", "data": {"output": output}}
    rounds: list[dict] = []
    accumulate_usage(event, rounds)

    assert len(rounds) == 1
    assert rounds[0]["input_tokens"] == 100
    assert rounds[0]["output_tokens"] == 50
    assert rounds[0]["cache_read_tokens"] == 20
    assert rounds[0]["reasoning_tokens"] == 10


def test_accumulate_usage_no_output():
    """on_chat_model_end with no output should still append zeros."""
    event = {"event": "on_chat_model_end", "data": {"output": None}}
    rounds: list[dict] = []
    accumulate_usage(event, rounds)

    assert len(rounds) == 1
    assert rounds[0]["input_tokens"] == 0


def test_format_sse_event():
    """Should produce correctly formatted SSE frame."""
    result = format_sse_event("token", {"content": "hi"})
    assert result.startswith("event: token\n")
    assert '"type": "token"' in result
    assert '"content": "hi"' in result
    assert result.endswith("\n\n")


def test_categorize_error_auth():
    """Auth errors should map to AUTH_FAILED."""
    info = categorize_error(RuntimeError("401 Unauthorized"))
    assert info["error_code"] == "AUTH_FAILED"


def test_categorize_error_rate_limit():
    """Rate limit errors should map to RATE_LIMITED."""
    info = categorize_error(RuntimeError("429 Too Many Requests"))
    assert info["error_code"] == "RATE_LIMITED"


def test_categorize_error_quota():
    """Quota errors should map to INSUFFICIENT_QUOTA."""
    info = categorize_error(RuntimeError("insufficient quota"))
    assert info["error_code"] == "INSUFFICIENT_QUOTA"


def test_categorize_error_server():
    """5xx errors should map to SERVER_UNAVAILABLE."""
    info = categorize_error(RuntimeError("502 Bad Gateway"))
    assert info["error_code"] == "SERVER_UNAVAILABLE"


def test_categorize_error_unknown():
    """Unknown errors should map to UNKNOWN_ERROR."""
    info = categorize_error(RuntimeError("something weird"))
    assert info["error_code"] == "UNKNOWN_ERROR"
