"""SSE stream event processing utilities.

Converts LangGraph astream_events v2 events into SSE-friendly tuples,
accumulates display state and token usage for persistence.
"""

import json
import time
from typing import Any


def format_sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event frame.

    Returns a string like:
        event: token
        data: {"type":"token","content":"hello"}

    """
    payload = json.dumps({"type": event_type, **data}, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


SSE_HEARTBEAT = ": heartbeat\n\n"


def convert_stream_event(event: dict) -> list[tuple[str, dict]]:
    """Convert an astream_events v2 event into SSE event tuples.

    Returns a list of (event_type, payload_dict) for each client-visible
    event produced by this single LangGraph event. May return an empty list
    if the event has no client-visible representation.
    """
    results: list[tuple[str, dict]] = []
    kind = event.get("event", "")

    if kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if chunk:
            additional = getattr(chunk, "additional_kwargs", None) or {}
            reasoning = additional.get("reasoning_content") or additional.get("reasoning")
            if reasoning:
                results.append(("thinking", {"content": reasoning}))
            if hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, list):
                    content = "".join(
                        p.get("text", "") if isinstance(p, dict) else str(p) for p in content
                    )
                results.append(("token", {"content": content}))

    elif kind == "on_tool_start":
        tool_name = event.get("name", "")
        tool_input = event.get("data", {}).get("input", {})
        if not isinstance(tool_input, (dict, list, str, int, float, bool, type(None))):
            tool_input = str(tool_input)

        if tool_name == "task" and isinstance(tool_input, dict) and "subagent_type" in tool_input:
            results.append(("sub_agent_call", {
                "parent_tool_run_id": event.get("run_id", ""),
                "sub_agent_id": tool_input.get("subagent_type", ""),
                "sub_agent_name": tool_input.get("subagent_type", ""),
                "task_description": str(tool_input.get("description", "")),
                "status": "running",
                "depth": 1,
            }))
        else:
            results.append(("tool_call", {
                "name": tool_name,
                "run_id": event.get("run_id", ""),
                "args": tool_input,
            }))

    elif kind == "on_tool_end":
        tool_name = event.get("name", "")
        output = event.get("data", {}).get("output", "")
        if isinstance(output, dict):
            result_str = str(output.get("content", str(output)))
        elif hasattr(output, "content"):
            result_str = output.content if isinstance(output.content, str) else str(output.content)
        else:
            result_str = str(output)

        if tool_name == "task":
            results.append(("sub_agent_done", {
                "parent_tool_run_id": event.get("run_id", ""),
                "status": "done",
                "summary": result_str[:200],
                "final_result": result_str,
            }))
        else:
            results.append(("tool_result", {
                "name": tool_name,
                "result": result_str,
            }))

    return results


def accumulate_display_state(
    event: dict,
    content_parts: list[str],
    tool_calls: list[dict[str, Any]],
    in_thinking: bool,
) -> bool:
    """Mirror the client display markers so history can replay the same layout.

    Mutates content_parts and tool_calls in place. Returns updated in_thinking flag.
    """
    kind = event.get("event", "")

    if kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if not chunk:
            return in_thinking

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
        if in_thinking:
            content_parts.append("<!--THINK_END-->")
            in_thinking = False

        tool_idx = len(tool_calls)
        tool_input = event.get("data", {}).get("input", {})
        if not isinstance(tool_input, (dict, list, str, int, float, bool, type(None))):
            tool_input = str(tool_input)
        tool_calls.append({
            "name": event.get("name", ""),
            "runId": event.get("run_id", ""),
            "args": tool_input,
            "status": "running",
            "startTime": int(time.time() * 1000),
        })
        content_parts.append(f"\n<!--TOOL:{tool_idx}-->\n")

    elif kind == "on_tool_end":
        raw_output = event.get("data", {}).get("output", "")
        if hasattr(raw_output, "content"):
            result_str = raw_output.content if isinstance(raw_output.content, str) else str(raw_output.content)
        else:
            result_str = str(raw_output)
        run_id = event.get("run_id", "")
        name = event.get("name", "")
        tool_call = None
        if run_id:
            tool_call = next(
                (tc for tc in tool_calls if tc.get("runId") == run_id), None,
            )
        if tool_call is None:
            tool_call = next(
                (tc for tc in tool_calls if tc.get("name") == name and tc.get("status") == "running"),
                None,
            )
        if tool_call:
            start_time = tool_call.get("startTime")
            tool_call["result"] = result_str
            tool_call["status"] = "done"
            tool_call["duration"] = int(time.time() * 1000) - start_time if start_time else None
            tool_call["resultLength"] = len(result_str)

    return in_thinking


def accumulate_usage(event: dict, usage_rounds: list[dict]) -> None:
    """Extract token usage from on_chat_model_end events.

    Appends a usage dict to usage_rounds if the event is on_chat_model_end.
    """
    kind = event.get("event", "")
    if kind != "on_chat_model_end":
        return

    output = event.get("data", {}).get("output")
    if not output:
        usage_rounds.append({"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cache_read_tokens": 0})
        return

    meta = getattr(output, "usage_metadata", None)
    if meta is None and hasattr(output, "response_metadata"):
        resp_meta = output.response_metadata or {}
        meta = resp_meta.get("token_usage") or resp_meta.get("usage")

    if meta:
        def _get(obj: Any, key: str, default: int = 0) -> int:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        input_t = _get(meta, "input_tokens", 0) or _get(meta, "prompt_tokens", 0)
        output_t = _get(meta, "output_tokens", 0) or _get(meta, "completion_tokens", 0)
        total_t = _get(meta, "total_tokens", 0) or (input_t + output_t)

        cache_read = 0
        if isinstance(meta, dict):
            details = meta.get("input_token_details") or {}
            cache_read = details.get("cache_read", 0) if isinstance(details, dict) else getattr(details, "cache_read", 0)
        else:
            details = getattr(meta, "input_token_details", None)
            if details:
                cache_read = getattr(details, "cache_read", 0) if not isinstance(details, dict) else details.get("cache_read", 0)

        reasoning = 0
        if isinstance(meta, dict):
            out_details = meta.get("output_token_details") or {}
            reasoning = out_details.get("reasoning", 0) if isinstance(out_details, dict) else getattr(out_details, "reasoning", 0)
        else:
            out_details = getattr(meta, "output_token_details", None)
            if out_details:
                reasoning = getattr(out_details, "reasoning", 0) if not isinstance(out_details, dict) else out_details.get("reasoning", 0)

        usage_rounds.append({
            "input_tokens": input_t or 0,
            "output_tokens": output_t or 0,
            "total_tokens": total_t or 0,
            "cache_read_tokens": cache_read or 0,
            "reasoning_tokens": reasoning or 0,
        })
    else:
        usage_rounds.append({"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cache_read_tokens": 0})


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
