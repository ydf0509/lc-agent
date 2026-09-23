import pytest


def test_tracker_enriches_subagent_tool_call_event():
    from lc_agent.server.subagent_tracker import SubAgentRunTracker

    tool_calls = [{"name": "research_expert", "runId": "task123", "status": "running"}]
    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={"research_expert": "研究专家"},
        tool_calls=tool_calls,
    )

    event_type, payload = tracker.handle_event(
        "tool_call",
        {
            "name": "research_expert",
            "run_id": "task123",
            "args": {"query": "quantum"},
            "is_subagent": True,
        },
    )

    assert event_type == "tool_call"
    assert payload["name"] == "研究专家"
    assert payload["sub_session_id"] == "parent1--sa--task123"
    assert payload["is_subagent"] is True
    assert tool_calls[0]["name"] == "研究专家"
    assert tool_calls[0]["sub_session_id"] == "parent1--sa--task123"
    assert tool_calls[0]["is_subagent"] is True


@pytest.mark.asyncio
async def test_tracker_start_uses_task_payload_display_name(monkeypatch):
    from lc_agent.server import subagent_tracker
    from lc_agent.server.subagent_tracker import SubAgentRunTracker

    async def fake_noop(*args, **kwargs):
        return None

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_noop)

    tool_calls = [{"name": "funboost教程查询智能体", "runId": "task123", "status": "running"}]
    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={"funboost": "funboost教程查询智能体"},
        tool_calls=tool_calls,
    )

    event_type, payload = tracker.handle_event(
        "subagent_start",
        {
            "name": "funboost教程查询智能体",
            "subagent_type": "funboost",
            "tool_call_id": "task123",
            "query": "查询定时任务",
        },
    )

    assert event_type == "subagent_start"
    assert payload["name"] == "funboost教程查询智能体"
    assert payload["tool_call_id"] == "task123"
    assert payload["query"] == "查询定时任务"
    assert payload["sub_session_id"] == "parent1--sa--task123"
    assert tool_calls[0]["name"] == "funboost教程查询智能体"
    assert tool_calls[0]["sub_session_id"] == "parent1--sa--task123"
    assert tool_calls[0]["is_subagent"] is True

    await tracker.drain()


@pytest.mark.asyncio
async def test_tracker_creates_subsession_when_parent_tool_call_is_only_enriched(monkeypatch):
    from lc_agent.server import subagent_tracker
    from lc_agent.server.subagent_tracker import SubAgentRunTracker

    calls = []

    async def fake_create_subsession(*args, **kwargs):
        calls.append("create")

    async def fake_delegation(*args, **kwargs):
        calls.append("delegation")

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_create_subsession)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_delegation)

    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={"research_expert": "研究专家"},
        tool_calls=[{
            "name": "研究专家",
            "runId": "task123",
            "status": "running",
            "is_subagent": True,
            "sub_session_id": "parent1--sa--task123",
        }],
    )

    _, payload = tracker.handle_event(
        "subagent_start",
        {"name": "research_expert", "tool_call_id": "task123", "query": "quantum"},
    )
    await tracker.drain()

    assert payload["sub_session_id"] == "parent1--sa--task123"
    assert calls == ["create", "delegation"]


@pytest.mark.asyncio
async def test_tracker_does_not_recreate_resume_subsession(monkeypatch):
    from lc_agent.server import subagent_tracker
    from lc_agent.server.subagent_tracker import SubAgentRunTracker

    calls = []

    async def fake_create_subsession(*args, **kwargs):
        calls.append("create")

    async def fake_delegation(*args, **kwargs):
        calls.append("delegation")

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_create_subsession)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_delegation)

    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={"research_expert": "研究专家"},
        tool_calls=[{
            "name": "研究专家",
            "runId": "task123",
            "status": "running",
            "is_subagent": True,
            "sub_session_id": "parent1--sa--task123",
        }],
        existing_subsession_ids={"parent1--sa--task123"},
    )

    _, payload = tracker.handle_event(
        "subagent_start",
        {"name": "research_expert", "tool_call_id": "task123", "query": "quantum"},
    )
    await tracker.drain()

    assert payload["sub_session_id"] == "parent1--sa--task123"
    assert calls == []


@pytest.mark.asyncio
async def test_tracker_start_token_done_persists_subsession(monkeypatch):
    from lc_agent.server.subagent_tracker import SubAgentRunTracker
    from lc_agent.server import subagent_tracker

    calls = []

    async def fake_create_subsession(sub_session_id, parent_session_id, tool_call_id, agent_id, title, user_id=""):
        calls.append(("create", sub_session_id, parent_session_id, tool_call_id, agent_id, title, user_id))

    async def fake_delegation(sub_session_id, query):
        calls.append(("delegation", sub_session_id, query))

    async def fake_finalize(sub_session_id, content, tool_calls=None, http_traces=None, usage=None):
        calls.append(("finalize", sub_session_id, content, tool_calls, http_traces, usage))

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_create_subsession)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_delegation)
    monkeypatch.setattr(subagent_tracker.persistence, "finalize_subsession_message", fake_finalize)
    monkeypatch.setattr(subagent_tracker, "pop_subagent_traces", lambda sub_session_id: [{"id": "trace1"}])

    tool_calls = [{"name": "research_expert", "runId": "task123", "status": "running"}]
    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="user1",
        subagent_display_map={"research_expert": "研究专家"},
        tool_calls=tool_calls,
    )

    start_type, start_payload = tracker.handle_event(
        "subagent_start",
        {
            "name": "research_expert",
            "tool_call_id": "task123",
            "query": "quantum",
        },
    )
    assert start_type == "subagent_start"
    assert start_payload["name"] == "研究专家"
    assert start_payload["sub_session_id"] == "parent1--sa--task123"
    assert tool_calls[0]["is_subagent"] is True
    assert tool_calls[0]["sub_session_id"] == "parent1--sa--task123"
    assert tool_calls[0]["name"] == "研究专家"

    assert tracker.handle_event("subagent_token", {"tool_call_id": "task123", "content": "hello"}) == (
        "subagent_token",
        {"tool_call_id": "task123", "content": "hello"},
    )
    assert tracker.handle_event("subagent_token", {"tool_call_id": "task123", "content": " world"}) == (
        "subagent_token",
        {"tool_call_id": "task123", "content": " world"},
    )

    done_type, done_payload = tracker.handle_event(
        "subagent_done",
        {
            "tool_call_id": "task123",
            "result_preview": "ignored fallback",
            "status": "done",
        },
    )
    assert done_type == "subagent_done"
    assert done_payload["tool_call_id"] == "task123"
    assert done_payload["result_preview"] == "hello world"
    assert done_payload["status"] == "done"
    assert done_payload["token_count"] == 2
    assert done_payload["tool_count"] == 0
    assert done_payload["http_traces"] == [{"id": "trace1"}]

    await tracker.drain()
    assert calls[0] == (
        "create",
        "parent1--sa--task123",
        "parent1",
        "task123",
        "研究专家",
        "研究专家: quantum",
        "user1",
    )
    assert calls[1] == ("delegation", "parent1--sa--task123", "quantum")
    assert calls[2] == (
        "finalize",
        "parent1--sa--task123",
        "hello world",
        None,
        [{"id": "trace1"}],
        None,
    )


@pytest.mark.asyncio
async def test_tracker_persists_each_run_in_create_delegation_finalize_order(monkeypatch):
    import asyncio

    from lc_agent.server import subagent_tracker
    from lc_agent.server.subagent_tracker import SubAgentRunTracker

    calls = []
    create_started = asyncio.Event()
    allow_create_finish = asyncio.Event()

    async def fake_create_subsession(sub_session_id, parent_session_id, tool_call_id, agent_id, title, user_id=""):
        calls.append(("create-start", sub_session_id))
        create_started.set()
        await allow_create_finish.wait()
        calls.append(("create-end", sub_session_id))

    async def fake_delegation(sub_session_id, query):
        calls.append(("delegation", sub_session_id))

    async def fake_finalize(sub_session_id, content, tool_calls=None, http_traces=None, usage=None):
        calls.append(("finalize", sub_session_id))

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_create_subsession)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_delegation)
    monkeypatch.setattr(subagent_tracker.persistence, "finalize_subsession_message", fake_finalize)
    monkeypatch.setattr(subagent_tracker, "pop_subagent_traces", lambda sub_session_id: None)

    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={},
        tool_calls=[],
    )

    tracker.handle_event("subagent_start", {"name": "research_expert", "tool_call_id": "task123", "query": "q"})
    await asyncio.wait_for(create_started.wait(), timeout=1)
    tracker.handle_event("subagent_token", {"tool_call_id": "task123", "content": "answer"})
    tracker.handle_event("subagent_done", {"tool_call_id": "task123", "status": "done"})
    await asyncio.sleep(0)

    assert calls == [("create-start", "parent1--sa--task123")]

    allow_create_finish.set()
    await tracker.drain()

    assert calls == [
        ("create-start", "parent1--sa--task123"),
        ("create-end", "parent1--sa--task123"),
        ("delegation", "parent1--sa--task123"),
        ("finalize", "parent1--sa--task123"),
    ]


@pytest.mark.asyncio
async def test_tracker_records_thinking_and_internal_tools(monkeypatch):
    from lc_agent.server.subagent_tracker import SubAgentRunTracker
    from lc_agent.server import subagent_tracker

    finalized = []

    async def fake_noop(*args, **kwargs):
        return None

    async def fake_finalize(sub_session_id, content, tool_calls=None, http_traces=None, usage=None):
        finalized.append((content, tool_calls, http_traces))

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "finalize_subsession_message", fake_finalize)
    monkeypatch.setattr(subagent_tracker, "pop_subagent_traces", lambda sub_session_id: None)

    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={},
        tool_calls=[],
    )
    tracker.handle_event("subagent_start", {"name": "research_expert", "tool_call_id": "task123", "query": "q"})
    tracker.handle_event("subagent_thinking", {"tool_call_id": "task123", "content": "think"})
    tracker.handle_event("subagent_token", {"tool_call_id": "task123", "content": "answer"})
    tracker.handle_event("subagent_tool_call", {"tool_call_id": "task123", "name": "search", "args": {"q": "x"}})
    tracker.handle_event("subagent_tool_result", {"tool_call_id": "task123", "name": "search", "result": "result"})
    _, done_payload = tracker.handle_event("subagent_done", {"tool_call_id": "task123", "status": "done"})

    assert done_payload["tool_count"] == 1
    assert done_payload["token_count"] == 1
    await tracker.drain()

    assert finalized[0][0] == "<!--THINK_START-->think<!--THINK_END-->answer\n<!--TOOL:0-->\n"
    assert finalized[0][1][0]["name"] == "search"
    assert finalized[0][1][0]["status"] == "done"
    assert finalized[0][1][0]["result"] == "result"
    assert finalized[0][1][0]["duration"] >= 0
    assert finalized[0][1][0]["resultLength"] == len("result")
    assert "endTime" not in finalized[0][1][0]


@pytest.mark.asyncio
async def test_tracker_preserves_token_tool_token_order(monkeypatch):
    from lc_agent.server.subagent_tracker import SubAgentRunTracker
    from lc_agent.server import subagent_tracker

    finalized = []

    async def fake_noop(*args, **kwargs):
        return None

    async def fake_finalize(sub_session_id, content, tool_calls=None, http_traces=None, usage=None):
        finalized.append((content, tool_calls, http_traces))

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "finalize_subsession_message", fake_finalize)
    monkeypatch.setattr(subagent_tracker, "pop_subagent_traces", lambda sub_session_id: None)

    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={},
        tool_calls=[],
    )
    tracker.handle_event("subagent_start", {"name": "research_expert", "tool_call_id": "task123", "query": "q"})
    tracker.handle_event("subagent_token", {"tool_call_id": "task123", "content": "before"})
    tracker.handle_event("subagent_tool_call", {"tool_call_id": "task123", "name": "search", "args": {"q": "x"}})
    tracker.handle_event("subagent_tool_result", {"tool_call_id": "task123", "name": "search", "result": "result"})
    tracker.handle_event("subagent_token", {"tool_call_id": "task123", "content": "after"})
    tracker.handle_event("subagent_done", {"tool_call_id": "task123", "status": "done"})

    await tracker.drain()

    assert finalized[0][0] == "before\n<!--TOOL:0-->\nafter"
    assert finalized[0][1][0]["name"] == "search"


@pytest.mark.asyncio
async def test_tracker_done_attaches_sub_usage_rounds(monkeypatch):
    """done 时按 sub_session_id 摘出该子会话 rounds，随 usage 落库并附带在事件里。

    只供子会话页展示 token；主会话总量统计走 record_usage 全量，不受影响。
    """
    from lc_agent.server.subagent_tracker import SubAgentRunTracker
    from lc_agent.server import subagent_tracker

    finalized = []

    async def fake_noop(*args, **kwargs):
        return None

    async def fake_finalize(sub_session_id, content, tool_calls=None, http_traces=None, usage=None):
        finalized.append(usage)

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "finalize_subsession_message", fake_finalize)
    monkeypatch.setattr(subagent_tracker, "pop_subagent_traces", lambda sub_session_id: None)

    usage_rounds = [
        {"role": "main", "sub_session_id": "", "input_tokens": 10},
        {"role": "sub", "sub_session_id": "parent1--sa--task123", "input_tokens": 100,
         "output_tokens": 20, "total_tokens": 120},
        {"role": "sub", "sub_session_id": "parent1--sa--other", "input_tokens": 5},
        {"role": "sub", "sub_session_id": "parent1--sa--task123", "input_tokens": 50,
         "source": "summarize"},
    ]
    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={},
        tool_calls=[],
        usage_rounds=usage_rounds,
    )
    tracker.handle_event("subagent_start", {"name": "r", "tool_call_id": "task123", "query": "q"})
    _, done_payload = tracker.handle_event("subagent_done", {"tool_call_id": "task123", "status": "done"})

    # 只摘出本子会话的非摘要 rounds；主 rounds 和别的子会话、摘要行都不混入
    assert done_payload["usage"]["rounds"] == [usage_rounds[1]]
    assert done_payload["usage"]["tool_call_count"] == 0
    await tracker.drain()
    assert finalized == [done_payload["usage"]]


@pytest.mark.asyncio
async def test_tracker_finalize_open_runs_marks_error(monkeypatch):
    from lc_agent.server.subagent_tracker import SubAgentRunTracker
    from lc_agent.server import subagent_tracker

    finalized = []

    async def fake_noop(*args, **kwargs):
        return None

    async def fake_finalize(sub_session_id, content, tool_calls=None, http_traces=None, usage=None):
        finalized.append((sub_session_id, content, tool_calls, http_traces))

    monkeypatch.setattr(subagent_tracker.persistence, "create_subsession", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "save_subsession_delegation_message", fake_noop)
    monkeypatch.setattr(subagent_tracker.persistence, "finalize_subsession_message", fake_finalize)
    monkeypatch.setattr(subagent_tracker, "pop_subagent_traces", lambda sub_session_id: None)

    tracker = SubAgentRunTracker(
        parent_thread_id="parent1",
        user_id="",
        subagent_display_map={},
        tool_calls=[],
    )
    tracker.handle_event("subagent_start", {"name": "research_expert", "tool_call_id": "task123", "query": "q"})
    tracker.handle_event("subagent_token", {"tool_call_id": "task123", "content": "partial"})

    terminal_events = tracker.finalize_open_runs(status="error")
    assert terminal_events == [
        (
            "subagent_done",
            {
                "tool_call_id": "task123",
                "result_preview": "partial",
                "status": "error",
                "duration": terminal_events[0][1]["duration"],
                "tool_count": 0,
                "token_count": 1,
            },
        )
    ]
    await tracker.drain()
    assert finalized[0][0] == "parent1--sa--task123"
    assert finalized[0][1] == "partial"


@pytest.mark.asyncio
async def test_send_stream_routes_subagent_events_through_tracker(monkeypatch):
    from types import SimpleNamespace

    from lc_agent.server import persistence, sse

    handled_events = []

    class FakeTracker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def handle_event(self, event_type, payload):
            handled_events.append((event_type, payload))
            if event_type == "content":
                return event_type, payload
            return event_type, {**payload, "tracked": True}

        def finalize_open_runs(self, status="error"):
            return []

        async def drain(self):
            return None

    class FakeEngine:
        recursion_limit = 25

        def _get_or_build_agent(self, *args, **kwargs):
            return SimpleNamespace(aget_state=self.aget_state)

        async def aget_state(self, config):
            return SimpleNamespace(tasks=[])

        def get_subagent_tool_names(self, *args, **kwargs):
            return {"task"}

        def get_subagent_display_name_map(self, *args, **kwargs):
            return {"research_expert": "研究专家"}

        def _find_model(self, model_id):
            return None

        async def reset_thread(self, thread_id):
            return None

        async def chat_stream(self, *args, **kwargs):
            yield {
                "event": "on_tool_start",
                "name": "task",
                "run_id": "run123",
                "metadata": {"langgraph_checkpoint_ns": "tools:task123"},
                "data": {"input": {"subagent_type": "research_expert", "description": "quantum"}},
            }
            yield {
                "event": "on_tool_end",
                "name": "task",
                "run_id": "run123",
                "metadata": {"langgraph_checkpoint_ns": "tools:task123"},
                "data": {"output": "research result"},
            }

    async def fake_noop(*args, **kwargs):
        return None

    async def fake_count(*args, **kwargs):
        return 1

    saved_messages = []

    async def fake_save_ui_message(*args, **kwargs):
        saved_messages.append((args, kwargs))

    monkeypatch.setattr(sse, "_engine", FakeEngine())
    monkeypatch.setattr(sse, "SubAgentRunTracker", FakeTracker)
    monkeypatch.setattr(persistence, "get_session_message_count", fake_count)
    monkeypatch.setattr(persistence, "save_ui_message", fake_save_ui_message)
    monkeypatch.setattr(persistence, "truncate_from_message", fake_noop)
    monkeypatch.setattr(persistence, "increment_session_message_count", fake_noop)

    async def fake_disconnected():
        return False

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(auth_service=None)),
        is_disconnected=fake_disconnected,
    )
    req = sse.RunStreamRequest(input=[{"type": "text", "text": "hello"}], preset_id="power", model="")

    response = await sse._send_stream("thread1", req, request)
    body_chunks = []
    async for chunk in response.body_iterator:
        body_chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

    assert handled_events[0][0] == "tool_call"
    assert handled_events[1][0] == "subagent_start"
    assert handled_events[2][0] == "subagent_done"
    assert "tracked" in "".join(body_chunks)
    assert saved_messages



@pytest.mark.asyncio
async def test_resume_stream_routes_subagent_events_through_tracker(monkeypatch):
    from types import SimpleNamespace

    from lc_agent.server import persistence, sse

    handled_events = []

    class FakeTracker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def handle_event(self, event_type, payload):
            handled_events.append((event_type, payload))
            return event_type, {**payload, "tracked": True}

        def finalize_open_runs(self, status="error"):
            return []

        async def drain(self):
            return None

    class FakeAgent:
        async def astream_events(self, *args, **kwargs):
            yield {
                "event": "on_tool_start",
                "name": "task",
                "run_id": "run123",
                "metadata": {"langgraph_checkpoint_ns": "tools:task123"},
                "data": {"input": {"subagent_type": "research_expert", "description": "quantum"}},
            }
            yield {
                "event": "on_tool_end",
                "name": "task",
                "run_id": "run123",
                "metadata": {"langgraph_checkpoint_ns": "tools:task123"},
                "data": {"output": "research result"},
            }

        async def aget_state(self, config):
            return SimpleNamespace(tasks=[])

    class FakeEngine:
        recursion_limit = 25

        def _get_or_build_agent(self, *args, **kwargs):
            return FakeAgent()

        def get_subagent_tool_names(self, *args, **kwargs):
            return {"task"}

        def get_subagent_display_name_map(self, *args, **kwargs):
            return {"research_expert": "研究专家"}

        def _find_model(self, model_id):
            return None

        def _should_use_memory_context(self, preset_id):
            return False

    async def fake_load_resume_context(*args, **kwargs):
        return ([{"name": "research_expert", "runId": "task123", "status": "running"}], 2)

    appended_messages = []

    async def fake_append_to_last_assistant_message(*args, **kwargs):
        appended_messages.append((args, kwargs))

    monkeypatch.setattr(sse, "_engine", FakeEngine())
    monkeypatch.setattr(sse, "SubAgentRunTracker", FakeTracker)
    monkeypatch.setattr(persistence, "load_resume_context", fake_load_resume_context)
    monkeypatch.setattr(persistence, "append_to_last_assistant_message", fake_append_to_last_assistant_message)

    class FakeTraceCollector:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def snapshot(self):
            return [{"url": "https://example.test", "method": "GET"}]

    monkeypatch.setattr(sse, "HttpTraceCollector", FakeTraceCollector)
    monkeypatch.setattr(sse, "bind_http_trace_collector", lambda collector: "token")
    monkeypatch.setattr(sse, "reset_http_trace_collector", lambda token: None)

    async def fake_disconnected():
        return False

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(auth_service=None)),
        is_disconnected=fake_disconnected,
    )
    req = sse.RunStreamRequest(command={"resume": {"decisions": []}}, preset_id="power", model="")

    response = await sse._resume_stream("thread1", req, request)
    body_chunks = []
    async for chunk in response.body_iterator:
        body_chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

    assert handled_events[0][0] == "tool_call"
    assert handled_events[1][0] == "subagent_start"
    assert handled_events[2][0] == "subagent_done"
    assert "tracked" in "".join(body_chunks)
    assert appended_messages
    assert "<!--HTTP:2-->" in appended_messages[0][0][1]


@pytest.mark.asyncio
async def test_resume_stream_marks_stale_running_subagent_tool_calls_interrupted(monkeypatch):
    from types import SimpleNamespace

    from lc_agent.server import persistence, sse

    class FakeTracker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def handle_event(self, event_type, payload):
            return event_type, payload

        def finalize_open_runs(self, status="error"):
            return []

        async def drain(self):
            return None

    class FakeAgent:
        async def astream_events(self, *args, **kwargs):
            if False:
                yield None
            return

        async def aget_state(self, config):
            return SimpleNamespace(tasks=[])

    class FakeEngine:
        recursion_limit = 25

        def _get_or_build_agent(self, *args, **kwargs):
            return FakeAgent()

        def get_subagent_tool_names(self, *args, **kwargs):
            return {"task"}

        def get_subagent_display_name_map(self, *args, **kwargs):
            return {"research_expert": "研究专家"}

        def _find_model(self, model_id):
            return None

        def _should_use_memory_context(self, preset_id):
            return False

    async def fake_load_resume_context(*args, **kwargs):
        return ([{
            "name": "研究专家",
            "runId": "task123",
            "status": "running",
            "is_subagent": True,
            "sub_session_id": "thread1--sa--task123",
        }], 0)

    appended_messages = []

    async def fake_append_to_last_assistant_message(*args, **kwargs):
        appended_messages.append((args, kwargs))

    monkeypatch.setattr(sse, "_engine", FakeEngine())
    monkeypatch.setattr(sse, "SubAgentRunTracker", FakeTracker)
    monkeypatch.setattr(persistence, "load_resume_context", fake_load_resume_context)
    monkeypatch.setattr(persistence, "append_to_last_assistant_message", fake_append_to_last_assistant_message)

    class FakeTraceCollector:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def snapshot(self):
            return []

    monkeypatch.setattr(sse, "HttpTraceCollector", FakeTraceCollector)
    monkeypatch.setattr(sse, "bind_http_trace_collector", lambda collector: "token")
    monkeypatch.setattr(sse, "reset_http_trace_collector", lambda token: None)

    async def fake_disconnected():
        return False

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(auth_service=None)),
        is_disconnected=fake_disconnected,
    )
    req = sse.RunStreamRequest(command={"resume": {"decisions": []}}, preset_id="power", model="")

    response = await sse._resume_stream("thread1", req, request)
    async for _chunk in response.body_iterator:
        pass

    assert appended_messages
    tool_calls = appended_messages[0][1]["all_tool_calls"]
    assert tool_calls[0]["status"] == "interrupted"
