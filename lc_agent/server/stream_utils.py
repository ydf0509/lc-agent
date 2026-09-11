"""SSE stream event processing utilities.

Converts LangGraph astream_events v2 events into SSE-friendly tuples,
accumulates display state and token usage for persistence.
"""

import json
import time
from typing import Any


def _get_checkpoint_ns(event: dict) -> str:
    """Return the langgraph_checkpoint_ns metadata string (empty = main agent)."""
    return event.get("metadata", {}).get("langgraph_checkpoint_ns", "")


def _extract_subagent_tool_call_id(checkpoint_ns: str) -> str | None:
    """Return tool_call_id if this event is INSIDE a sub-agent's execution.

    Sub-agents inherit the parent's checkpoint_ns and append their own layers,
    producing a multi-segment namespace separated by "|":
      - Main agent tool execution:   "tools:{task_uuid}"          (single segment)
      - Sub-agent internal event:    "tools:{task_uuid}|agent"    (multiple segments)
      - Sub-agent internal tool:     "tools:{uuid}|...|tools:{uuid2}" (multiple segments)

    A regular graph node that embeds a compiled agent is also a nested graph,
    but it starts with its node name instead of the parent task tool:
      - Regular nested agent:        "agent:{graph_uuid}|tools:{uuid}"

    Only namespaces rooted at ``tools:{task_uuid}`` represent a sub-agent
    launched through a task tool. Other nested graphs must continue to use
    normal tool events so they can be rendered in the main conversation.

    Returns None for main-agent namespaces and ordinary nested graph events.
    Returns the task_uuid from the root "tools:" segment for task sub-agents.
    """
    segments = checkpoint_ns.split("|")
    if len(segments) <= 1 or not segments[0].startswith("tools:"):
        # Main-agent events and ordinary nested graph events are not task
        # sub-agent events.
        return None
    return segments[0].split(":", 1)[1]


def _extract_tools_task_id(checkpoint_ns: str) -> str | None:
    """Extract the LangGraph task UUID from the first 'tools:{uuid}' segment.

    Unlike _extract_subagent_tool_call_id, this works for both single-segment
    (main-agent tool call) and multi-segment (sub-agent internal) namespaces.
    Used to build the sub_thread_id key that matches engine.py.
    """
    for seg in checkpoint_ns.split("|"):
        if seg.startswith("tools:"):
            return seg.split(":", 1)[1]
    return None


def _extract_task_subagent_type(tool_name: str, tool_input: Any, subagent_tool_names: set[str] | None) -> str | None:
    if not subagent_tool_names or tool_name not in subagent_tool_names:
        return None
    if tool_name != "task":
        return tool_name
    if not isinstance(tool_input, dict):
        return None
    subagent_type = tool_input.get("subagent_type")
    if not isinstance(subagent_type, str) or not subagent_type.strip():
        return None
    return subagent_type.strip()


def _is_subagent_tool_end(
    tool_name: str,
    tool_input: Any,
    subagent_tool_names: set[str] | None,
    active_subagent_tool_call_ids: set[str] | None,
    tool_call_id: str,
) -> bool:
    if not subagent_tool_names or tool_name not in subagent_tool_names:
        return False
    if tool_name != "task":
        return True
    if isinstance(tool_input, dict) and tool_input:
        return _extract_task_subagent_type(tool_name, tool_input, subagent_tool_names) is not None
    return bool(active_subagent_tool_call_ids and tool_call_id in active_subagent_tool_call_ids)


def format_sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event frame.

    Returns a string like:
        event: token
        data: {"type":"token","content":"hello"}

    """
    payload = json.dumps({"type": event_type, **data}, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


SSE_HEARTBEAT = ": heartbeat\n\n"


def convert_stream_event(
    event: dict,
    subagent_tool_names: set[str] | None = None,
    subagent_display_map: dict[str, str] | None = None,
    active_subagent_tool_call_ids: set[str] | None = None,
) -> list[tuple[str, dict]]:
    """Convert an astream_events v2 event into SSE event tuples.

    Returns a list of (event_type, payload_dict) for each client-visible
    event produced by this single LangGraph event. May return an empty list
    if the event has no client-visible representation.
    """
    results: list[tuple[str, dict]] = []
    checkpoint_ns = _get_checkpoint_ns(event)
    sa_tool_call_id = _extract_subagent_tool_call_id(checkpoint_ns)
    is_in_subagent = sa_tool_call_id is not None
    kind = event.get("event", "")

    if kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if chunk:
            additional = getattr(chunk, "additional_kwargs", None) or {}
            reasoning = additional.get("reasoning_content") or additional.get("reasoning")
            text = ""
            if hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, list):
                    content = "".join(
                        p.get("text", "") if isinstance(p, dict) else str(p) for p in content
                    )
                text = content
            if is_in_subagent:
                if reasoning:
                    results.append(("subagent_thinking", {"tool_call_id": sa_tool_call_id, "content": reasoning}))
                if text:
                    results.append(("subagent_token", {"tool_call_id": sa_tool_call_id, "content": text}))
            else:
                if reasoning:
                    results.append(("thinking", {"content": reasoning}))
                if text:
                    results.append(("token", {"content": text}))

    elif kind == "on_tool_start":
        tool_name = event.get("name", "")
        tool_input = event.get("data", {}).get("input", {})
        if not isinstance(tool_input, (dict, list, str, int, float, bool, type(None))):
            tool_input = str(tool_input)
        # NOTE: LangGraph's ToolNode runs ALL tools inside "tools:{tc_id}" checkpoint_ns,
        # so is_in_subagent is True even for the main agent calling a sub-agent tool.
        # We MUST check by tool name first to correctly classify sub-agent invocations.
        subagent_type = _extract_task_subagent_type(tool_name, tool_input, subagent_tool_names)
        if subagent_type:
            # Main agent calling a sub-agent tool (is_in_subagent is False here
            # because the main-agent ToolNode has a single-segment checkpoint_ns).
            # Use _extract_tools_task_id (works for single-segment too) to get the
            # LangGraph task UUID, which matches the tc_id engine.py registers.
            tool_input_dict = tool_input if isinstance(tool_input, dict) else {}
            sa_tc_id = (
                _extract_tools_task_id(checkpoint_ns)  # LangGraph task UUID (single-segment OK)
                or event.get("run_id", "")             # fallback
            )
            display_args = (
                {k: v for k, v in tool_input_dict.items() if k != "tool_call_id"}
                if isinstance(tool_input, dict) else tool_input
            )
            display_name = (subagent_display_map or {}).get(subagent_type, subagent_type)
            query = ""
            if isinstance(tool_input_dict, dict):
                query = str(tool_input_dict.get("description") or tool_input_dict.get("query") or tool_input)
            else:
                query = str(tool_input)
            results.append(("tool_call", {
                "name": display_name,
                "tool_call_id": sa_tc_id,
                "run_id": sa_tc_id,
                "args": display_args,
                "is_subagent": True,
            }))
            start_payload = {
                "name": display_name,
                "tool_call_id": sa_tc_id,
                "query": query,
            }
            if subagent_type:
                start_payload["subagent_type"] = subagent_type
            results.append(("subagent_start", start_payload))
        elif is_in_subagent:
            # Sub-agent calling its own internal tool
            results.append(("subagent_tool_call", {
                "tool_call_id": sa_tool_call_id,
                "name": tool_name,
                "args": tool_input,
            }))
        else:
            # Regular main-agent tool call
            results.append(("tool_call", {
                "name": tool_name,
                "tool_call_id": _extract_tools_task_id(checkpoint_ns) or event.get("run_id", ""),
                "args": tool_input,
            }))

    elif kind == "on_tool_end":
        tool_name = event.get("name", "")
        tool_call_id = _extract_tools_task_id(checkpoint_ns) or event.get("run_id", "")
        output = event.get("data", {}).get("output", "")
        if hasattr(output, "content"):
            result_str = output.content if isinstance(output.content, str) else str(output.content)
        else:
            result_str = str(output)
        tool_input = event.get("data", {}).get("input", {})
        if _is_subagent_tool_end(tool_name, tool_input, subagent_tool_names, active_subagent_tool_call_ids, tool_call_id):
            # Main agent's sub-agent tool finished (single-segment checkpoint_ns)
            sa_tc_id_end = (
                _extract_tools_task_id(checkpoint_ns)  # LangGraph task UUID (matches on_tool_start)
                or event.get("run_id", "")             # fallback
            )
            is_error = result_str.startswith("[Sub-agent error:")
            status = "error" if is_error else "done"
            results.append(("subagent_done", {
                "tool_call_id": sa_tc_id_end,
                "result_preview": result_str[:150],
                "status": status,
                "is_error": is_error,
            }))
        elif is_in_subagent:
            # Sub-agent's internal tool finished
            is_error = result_str.startswith("[Tool error:") or result_str.startswith("Tool error:")
            status = "error" if is_error else "done"
            results.append(("subagent_tool_result", {
                "tool_call_id": sa_tool_call_id,
                "name": tool_name,
                "result": result_str,
                "status": status,
                "is_error": is_error,
            }))
        else:
            # Regular main-agent tool finished
            results.append(("tool_result", {
                "name": tool_name,
                "tool_call_id": _extract_tools_task_id(checkpoint_ns) or event.get("run_id", ""),
                "result": result_str,
            }))

    elif kind == "on_tool_error":
        tool_name = event.get("name", "")
        tool_call_id = (
            _extract_tools_task_id(checkpoint_ns)
            or event.get("data", {}).get("tool_call_id")
            or event.get("run_id", "")
        )
        tool_input = event.get("data", {}).get("input", {})
        error = event.get("data", {}).get("error", "")
        error_str = str(error) if error else "Tool execution error"
        if _is_subagent_tool_end(tool_name, tool_input, subagent_tool_names, active_subagent_tool_call_ids, tool_call_id):
            sa_tc_id_err = (
                _extract_tools_task_id(checkpoint_ns)
                or event.get("run_id", "")
            )
            results.append(("subagent_done", {
                "tool_call_id": sa_tc_id_err,
                "result_preview": error_str[:150],
                "status": "error",
                "is_error": True,
            }))
        elif is_in_subagent:
            results.append(("subagent_tool_result", {
                "tool_call_id": sa_tool_call_id,
                "name": tool_name,
                "result": error_str,
                "status": "error",
                "is_error": True,
            }))
        else:
            results.append(("tool_result", {
                "name": tool_name,
                "tool_call_id": tool_call_id,
                "result": error_str,
                "status": "error",
                "is_error": True,
            }))

    elif kind == "on_custom_event":
        custom_name = event.get("name", "")
        data = event.get("data", {})
        tool_call_id = _extract_tools_task_id(checkpoint_ns) or event.get("run_id", "")

        if custom_name == "command_output":
            content = data.get("content", "")
            if content:
                results.append(("tool_output_chunk", {
                    "tool_call_id": tool_call_id,
                    "content": content,
                }))
        elif custom_name == "command_process_info":
            results.append(("tool_process_info", {
                "tool_call_id": tool_call_id,
                "pid": data.get("pid"),
                "command": data.get("command", ""),
            }))
        elif custom_name == "file_edit_diff":
            results.append(("tool_file_diff", {
                "tool_call_id": tool_call_id,
                "file": data.get("file", ""),
                "start_line": data.get("start_line", 1),
                "context_before": data.get("context_before", []),
                "removed": data.get("removed", []),
                "added": data.get("added", []),
                "context_after": data.get("context_after", []),
            }))
        elif custom_name == "file_write_preview":
            results.append(("tool_file_preview", {
                "tool_call_id": tool_call_id,
                "file": data.get("file", ""),
                "mode": data.get("mode", "rewrite"),
                "preview_lines": data.get("preview_lines", []),
                "total_lines": data.get("total_lines", 0),
                "start_line": data.get("start_line", 1),
            }))
        elif custom_name == "file_change_record":
            results.append(("file_change", {
                "session_id": data.get("session_id", ""),
                "round_number": data.get("round_number"),
                "file_path": data.get("file_path", ""),
                "change_type": data.get("change_type", ""),
                "old_string": data.get("old_string"),
                "new_string": data.get("new_string"),
                "move_destination": data.get("move_destination"),
                "line_start": data.get("line_start"),
                "context_before": data.get("context_before"),
                "context_after": data.get("context_after"),
                "tool_call_id": tool_call_id,
            }))
        elif custom_name == "file_change_git_snapshot":
            results.append(("file_change_git_snapshot", {
                "session_id": data.get("session_id", ""),
                "git_base_hash": data.get("git_base_hash", ""),
            }))

    return results


def accumulate_display_state(
    event: dict,
    content_parts: list[str],
    tool_calls: list[dict[str, Any]],
    in_thinking: bool,
    subagent_tool_names: set[str] | None = None,
    thread_id: str | None = None,
    subagent_display_map: dict[str, str] | None = None,
    active_subagent_tool_call_ids: set[str] | None = None,
) -> bool:
    """Mirror the client display markers so history can replay the same layout.

    Mutates content_parts and tool_calls in place. Returns updated in_thinking flag.
    """
    kind = event.get("event", "")
    checkpoint_ns = _get_checkpoint_ns(event)
    sa_tool_call_id = _extract_subagent_tool_call_id(checkpoint_ns)
    is_in_subagent = sa_tool_call_id is not None

    if kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if not chunk:
            return in_thinking

        if not is_in_subagent:
            additional = getattr(chunk, "additional_kwargs", None) or {}
            reasoning = additional.get("reasoning_content") or additional.get("reasoning")
            if reasoning:
                if not in_thinking:
                    content_parts.append("<!--THINK_START-->")
                    in_thinking = True
                content_parts.append(reasoning)

            if hasattr(chunk, "content") and chunk.content:
                if in_thinking:
                    content_parts.append("<!--THINK_END-->")
                    in_thinking = False
                text = chunk.content
                if isinstance(text, list):
                    text = "".join(
                        p.get("text", "") if isinstance(p, dict) else str(p) for p in text
                    )
                content_parts.append(text)

    elif kind == "on_tool_start":
        tool_name = event.get("name", "")
        # PRIORITY: check by name first — LangGraph's ToolNode sets checkpoint_ns to
        # "tools:{tc_id}" for ALL tool calls, so is_in_subagent would be True even for
        # the main agent calling a sub-agent tool.  Name-based detection is reliable.
        tool_input = event.get("data", {}).get("input", {})
        subagent_type = _extract_task_subagent_type(tool_name, tool_input, subagent_tool_names)
        if subagent_type:
            # Main agent calling a sub-agent tool (single-segment checkpoint_ns here)
            if in_thinking:
                content_parts.append("<!--THINK_END-->")
                in_thinking = False
            tool_input_dict = tool_input if isinstance(tool_input, dict) else {}
            sa_tc_id = (
                _extract_tools_task_id(checkpoint_ns)  # LangGraph task UUID (matches engine.py)
                or event.get("run_id", "")             # fallback
            )
            display_args = (
                {k: v for k, v in tool_input_dict.items() if k != "tool_call_id"}
                if isinstance(tool_input, dict) else tool_input
            )
            sub_session_id = f"{thread_id}--sa--{sa_tc_id}" if thread_id else ""
            display_name = (subagent_display_map or {}).get(subagent_type, subagent_type)
            tool_idx = len(tool_calls)
            tool_calls.append({
                "name": display_name,
                "runId": sa_tc_id,
                "args": display_args,
                "status": "running",
                "is_subagent": True,
                "sub_session_id": sub_session_id,
                "startTime": int(time.time() * 1000),
            })
            content_parts.append(f"\n<!--TOOL:{tool_idx}-->\n")
        elif not is_in_subagent:
            # Regular main-agent tool call (not a sub-agent tool)
            if in_thinking:
                content_parts.append("<!--THINK_END-->")
                in_thinking = False
            tool_idx = len(tool_calls)
            tool_call_id = _extract_tools_task_id(checkpoint_ns) or event.get("run_id", "")
            tool_input = event.get("data", {}).get("input", {})
            if not isinstance(tool_input, (dict, list, str, int, float, bool, type(None))):
                tool_input = str(tool_input)
            if not any(tc.get("runId") == tool_call_id for tc in tool_calls):
                tool_calls.append({
                    "name": tool_name,
                    "runId": tool_call_id,
                    "args": tool_input,
                    "status": "running",
                    "startTime": int(time.time() * 1000),
                })
                content_parts.append(f"\n<!--TOOL:{tool_idx}-->\n")
        # else: sub-agent's internal tool call (is_in_subagent=True, not a subagent tool) — skip

    elif kind == "on_tool_end":
        tool_name = event.get("name", "")
        tool_input = event.get("data", {}).get("input", {})
        tool_call_id = _extract_tools_task_id(checkpoint_ns) or event.get("run_id", "")
        if _is_subagent_tool_end(tool_name, tool_input, subagent_tool_names, active_subagent_tool_call_ids, tool_call_id):
            # Main agent's sub-agent tool finished
            raw_output = event.get("data", {}).get("output", "")
            if hasattr(raw_output, "content"):
                result_str = raw_output.content if isinstance(raw_output.content, str) else str(raw_output.content)
            else:
                result_str = str(raw_output)
            sa_tc_id = (
                _extract_tools_task_id(checkpoint_ns)  # LangGraph task UUID (matches on_tool_start)
                or event.get("run_id", "")             # fallback
            )
            for tc in tool_calls:
                if tc.get("runId") == sa_tc_id and tc.get("is_subagent"):
                    start_time = tc.get("startTime")
                    tc["status"] = "error" if result_str.startswith("[Sub-agent error:") else "done"
                    tc["result"] = result_str
                    tc["duration"] = int(time.time() * 1000) - start_time if start_time else None
                    tc["resultLength"] = len(result_str)
                    break
        elif not is_in_subagent:
            # Regular main-agent tool finished
            raw_output = event.get("data", {}).get("output", "")
            if hasattr(raw_output, "content"):
                result_str = raw_output.content if isinstance(raw_output.content, str) else str(raw_output.content)
            else:
                result_str = str(raw_output)
            tool_call_id = _extract_tools_task_id(checkpoint_ns) or event.get("run_id", "")
            tool_call = next(
                (tc for tc in tool_calls if tc.get("runId") == tool_call_id), None,
            )
            if tool_call:
                start_time = tool_call.get("startTime")
                tool_call["result"] = result_str
                tool_call["status"] = "done"
                tool_call["duration"] = int(time.time() * 1000) - start_time if start_time else None
                tool_call["resultLength"] = len(result_str)
        # else: sub-agent's internal tool result (is_in_subagent=True, not a subagent tool) — skip

    elif kind == "on_tool_error":
        tool_name = event.get("name", "")
        tool_input = event.get("data", {}).get("input", {})
        tool_call_id = (
            _extract_tools_task_id(checkpoint_ns)
            or event.get("data", {}).get("tool_call_id")
            or event.get("run_id", "")
        )
        error = event.get("data", {}).get("error", "")
        error_str = str(error) if error else "Tool execution error"
        if _is_subagent_tool_end(tool_name, tool_input, subagent_tool_names, active_subagent_tool_call_ids, tool_call_id):
            sa_tc_id = (
                _extract_tools_task_id(checkpoint_ns)
                or event.get("run_id", "")
            )
            for tc in tool_calls:
                if tc.get("runId") == sa_tc_id and tc.get("is_subagent"):
                    start_time = tc.get("startTime")
                    tc["status"] = "error"
                    tc["result"] = error_str
                    tc["duration"] = int(time.time() * 1000) - start_time if start_time else None
                    tc["resultLength"] = len(error_str)
                    break
        elif not is_in_subagent:
            tool_call = next(
                (tc for tc in tool_calls if tc.get("runId") == tool_call_id), None,
            )
            if tool_call:
                start_time = tool_call.get("startTime")
                tool_call["result"] = error_str
                tool_call["status"] = "error"
                tool_call["duration"] = int(time.time() * 1000) - start_time if start_time else None
                tool_call["resultLength"] = len(error_str)

    elif kind == "on_custom_event":
        # 文件 diff / 写入预览只走 SSE 推送时，刷新后历史里就没有了。
        # 这里把它们挂到同一 tool_call 上，随 tool_calls 一起入库，
        # 历史接口原样返回，前端刷新后直接渲染当时的 diff。
        # 注：custom 事件在子 Agent 内部执行时带多段 ns，
        # _extract_tools_task_id 取的是第一段（父 task 工具），不是内部工具
        # 自己的 id —— 内层调用目前走 subagent_tracker 存子会话，
        # 所以这里只挂主 Agent 自己的工具（单段 ns），避免挂错位置。
        custom_name = event.get("name", "")
        data = event.get("data", {})
        if not isinstance(data, dict):
            return in_thinking
        if custom_name not in ("file_edit_diff", "file_write_preview"):
            return in_thinking
        if is_in_subagent:
            # 子 Agent 内部工具的 custom 事件：ns 第一段是父 task 工具，
            # 挂到主 tool_calls 会错位；内层调用走子会话持久化，这里跳过
            # （与 on_tool_start/end 跳过内层调用的逻辑一致）。
            return in_thinking
        tool_call_id = _extract_tools_task_id(checkpoint_ns) or event.get("run_id", "")
        if tool_call_id:
            tool_call = next(
                (tc for tc in tool_calls if tc.get("runId") == tool_call_id), None,
            )
            if tool_call is not None:
                if custom_name == "file_edit_diff":
                    tool_call["fileDiff"] = {
                        "file": data.get("file", ""),
                        "start_line": data.get("start_line", 1),
                        "context_before": data.get("context_before", []) or [],
                        "removed": data.get("removed", []) or [],
                        "added": data.get("added", []) or [],
                        "context_after": data.get("context_after", []) or [],
                    }
                elif custom_name == "file_write_preview":
                    tool_call["filePreview"] = {
                        "file": data.get("file", ""),
                        "mode": data.get("mode", "rewrite"),
                        "preview_lines": data.get("preview_lines", []) or [],
                        "total_lines": data.get("total_lines", 0),
                        "start_line": data.get("start_line", 1),
                    }

    return in_thinking


def resolve_model_identity(
    event: dict,
    default_model_id: str = "",
    model_map: dict | None = None,
) -> str:
    """Resolve the configured model_id for an on_chat_model_end event.

    Priority (token_stats.md §4.1):
    1. reported name (response_metadata.model_name / metadata.ls_model_name)
       matched against the config map — by model_id first, then raw_model_id
       (a proxy may report the upstream name instead of our alias);
    2. the current request's model_id (default_model_id);
    3. "unknown" — a row with a token count is worth more than no row.
    """
    output = event.get("data", {}).get("output")
    resp_meta = getattr(output, "response_metadata", None) or {}
    reported = resp_meta.get("model_name") or resp_meta.get("model") or ""
    if not reported:
        reported = (event.get("metadata") or {}).get("ls_model_name") or ""

    if model_map:
        info = model_map.get(reported) or model_map.get(default_model_id)
        if info is not None:
            return getattr(info, "model_id", "") or default_model_id

    if default_model_id:
        return default_model_id
    if model_map and reported in model_map:
        return reported
    return reported or "unknown"


def accumulate_usage(
    event: dict,
    usage_rounds: list[dict],
    *,
    default_model_id: str = "",
    model_map: dict | None = None,
) -> None:
    """Extract token usage from on_chat_model_end events.

    Appends a usage dict to usage_rounds if the event is on_chat_model_end.
    Sub-agent LLM calls are NOT skipped anymore — they are tagged
    role="sub" with sub_session_id so usage_recorder can attribute them
    (token_stats.md §4.1).
    """
    kind = event.get("event", "")
    if kind != "on_chat_model_end":
        return

    checkpoint_ns = _get_checkpoint_ns(event)
    sub_id = _extract_subagent_tool_call_id(checkpoint_ns)

    output = event.get("data", {}).get("output")
    if not output:
        usage_rounds.append({
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0,
            "role": "sub" if sub_id else "main",
            "sub_session_id": sub_id or "",
            "model_id": "unknown",
            "raw_model_id": "",
            "provider": "",
        })
        return

    meta = getattr(output, "usage_metadata", None)
    if meta is None and hasattr(output, "response_metadata"):
        resp_meta = output.response_metadata or {}
        meta = resp_meta.get("token_usage") or resp_meta.get("usage")

    model_id = resolve_model_identity(event, default_model_id, model_map)
    info = (model_map or {}).get(model_id) if model_map else None

    if meta:
        def _get(obj: Any, key: str, default: int = 0) -> int:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        input_t = _get(meta, "input_tokens", 0) or _get(meta, "prompt_tokens", 0)
        output_t = _get(meta, "output_tokens", 0) or _get(meta, "completion_tokens", 0)
        total_t = _get(meta, "total_tokens", 0) or (input_t + output_t)

        if isinstance(meta, dict):
            details = meta.get("input_token_details") or {}
        else:
            details = getattr(meta, "input_token_details", None) or {}

        def _d(key: str) -> int:
            if not details:
                return 0
            return details.get(key, 0) if isinstance(details, dict) else getattr(details, key, 0)

        cache_read = _d("cache_read")
        cache_write = _d("cache_creation")

        if isinstance(meta, dict):
            out_details = meta.get("output_token_details") or {}
        else:
            out_details = getattr(meta, "output_token_details", None) or {}
        if out_details:
            reasoning = out_details.get("reasoning", 0) if isinstance(out_details, dict) else getattr(out_details, "reasoning", 0)
        else:
            reasoning = 0

        usage_rounds.append({
            "input_tokens": input_t or 0,
            "output_tokens": output_t or 0,
            "total_tokens": total_t or 0,
            "cache_read_tokens": cache_read or 0,
            "cache_write_tokens": cache_write or 0,
            "reasoning_tokens": reasoning or 0,
            "role": "sub" if sub_id else "main",
            "sub_session_id": sub_id or "",
            "model_id": model_id,
            "raw_model_id": getattr(info, "raw_model_id", "") if info else "",
            "provider": getattr(info, "provider", "") if info else "",
        })
    else:
        usage_rounds.append({
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0,
            "role": "sub" if sub_id else "main",
            "sub_session_id": sub_id or "",
            "model_id": model_id,
            "raw_model_id": getattr(info, "raw_model_id", "") if info else "",
            "provider": getattr(info, "provider", "") if info else "",
        })


def categorize_error(error: Exception) -> dict:
    """Categorize an exception into structured Chinese error info for the frontend."""
    msg = str(error)
    msg_lower = msg.lower()

    if any(k in msg_lower for k in (
        "401", "unauthorized", "authentication", "api key",
        "incorrect api", "invalid key", "auth failed", "credentials",
    )):
        return {
            "title": "API 密钥认证失败",
            "detail": "AI 模型的 API 密钥无效或未授权，请求被拒绝。",
            "suggestions": ["检查配置文件中的 API Key 是否正确", "确认 API Key 是否有对应模型的访问权限", "如已更换密钥，请更新配置后重试"],
            "error_code": "AUTH_FAILED",
        }

    if any(k in msg_lower for k in ("429", "rate limit", "too many requests", "rate_limit")):
        return {
            "title": "请求频率超限",
            "detail": "向 AI 模型的请求频率超过限制，已被暂时限流。",
            "suggestions": ["等待一段时间后重试", "降低请求并发数", "联系服务商提升配额"],
            "error_code": "RATE_LIMITED",
        }

    if any(k in msg_lower for k in ("model not found", "does not exist", "model `")):
        return {
            "title": "模型不存在或不可用",
            "detail": f"请求的 AI 模型不存在或当前不可用。\n{msg}",
            "suggestions": ["检查选择的模型名称是否正确", "确认该模型在 API 服务商处可用", "尝试切换其他模型"],
            "error_code": "MODEL_NOT_FOUND",
        }

    if any(k in msg_lower for k in (
        "connection refused", "connection error", "connection failed",
        "cannot connect", "connectionreset", "connection_reset",
        "connect failed", "no route to host", "name or service not known",
        "getaddrinfo failed",
    )):
        return {
            "title": "模型服务器连接失败",
            "detail": "无法连接到 AI 模型服务器，请检查网络或服务器状态。",
            "suggestions": ["检查服务器地址和端口是否正确", "确认 AI 模型网关服务是否在运行", "检查防火墙或网络代理设置"],
            "error_code": "CONNECTION_FAILED",
        }

    if any(k in msg_lower for k in ("timeout", "timed out", "deadline exceeded")):
        return {
            "title": "请求超时",
            "detail": "AI 模型响应超时，可能是模型负载过高或网络不稳定。",
            "suggestions": ["稍后重试", "尝试减少输入内容长度", "检查网络连接"],
            "error_code": "TIMEOUT",
        }

    if any(k in msg_lower for k in ("content filter", "content_filter", "safety", "blocked")):
        return {
            "title": "内容被安全策略拦截",
            "detail": "请求内容被 AI 模型的安全审查机制拦截。",
            "suggestions": ["修改输入内容后重试", "避免使用敏感或违规词汇"],
            "error_code": "CONTENT_FILTERED",
        }

    if any(k in msg_lower for k in ("insufficient", "quota", "balance", "billing", "payment")):
        return {
            "title": "账户配额不足",
            "detail": "API 账户配额或余额不足，无法继续请求。",
            "suggestions": ["检查 API 账户余额", "联系服务商增加配额"],
            "error_code": "INSUFFICIENT_QUOTA",
        }

    if any(k in msg_lower for k in ("500", "502", "503", "504", "service unavailable", "internal server error")):
        return {
            "title": "AI 模型服务暂时不可用",
            "detail": "AI 模型服务端返回错误，可能是服务负载过高或正在维护。",
            "suggestions": ["等待几秒后重试", "如持续不可用，联系服务商或管理员"],
            "error_code": "SERVER_UNAVAILABLE",
        }

    return {
        "title": "AI 模型接口请求失败",
        "detail": msg,
        "suggestions": ["请稍后重试，如问题持续请联系管理员"],
        "error_code": "UNKNOWN_ERROR",
    }
