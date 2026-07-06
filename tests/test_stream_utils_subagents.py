from lc_agent.server.stream_utils import convert_stream_event


def test_task_tool_start_converts_to_subagent_call_summary():
    event = {
        "event": "on_tool_start",
        "name": "task",
        "run_id": "tool-run-1",
        "data": {"input": {"subagent_type": "research", "description": "研究主题"}},
    }

    converted = convert_stream_event(event)

    assert converted[0][0] == "sub_agent_call"
    payload = converted[0][1]
    assert payload["parent_tool_run_id"] == "tool-run-1"
    assert payload["sub_agent_id"] == "research"
    assert payload["task_description"] == "研究主题"
    assert payload["status"] == "running"


def test_task_tool_end_converts_to_subagent_done_summary():
    event = {
        "event": "on_tool_end",
        "name": "task",
        "run_id": "tool-run-1",
        "data": {
            "output": {
                "content": "研究完成，结果是XXX",
            }
        },
    }

    converted = convert_stream_event(event)

    assert converted[0][0] == "sub_agent_done"
    payload = converted[0][1]
    assert payload["parent_tool_run_id"] == "tool-run-1"
    assert payload["status"] == "done"
    assert payload["summary"] == "研究完成，结果是XXX"
    assert payload["final_result"] == "研究完成，结果是XXX"


def test_non_task_tool_is_not_converted():
    event = {
        "event": "on_tool_start",
        "name": "nbrag_search",
        "run_id": "run-1",
        "data": {"input": {"query": "hello"}},
    }

    converted = convert_stream_event(event)

    assert converted[0][0] == "tool_call"
    assert converted[0][1]["name"] == "nbrag_search"