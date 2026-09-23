"""SSE streaming endpoints for chat.

Replaces WebSocket communication with POST → SSE streaming + REST control endpoints.
API design aligns with LangGraph /threads/{id}/runs/stream pattern.
"""

import asyncio
import logging
import time
import traceback
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from lc_agent.db.engine import get_business_async_session
from lc_agent.core.engine import AgentEngine
from lc_agent.core.http_trace import (
    HttpTraceCollector,
    bind_http_trace_collector,
    init_subagent_collector_registry,
    reset_http_trace_collector,
)
from lc_agent.server import persistence, stream_utils
from lc_agent.server.subagent_tracker import SubAgentRunTracker
from lc_agent.server.usage_recorder import build_model_map, record_usage
from lc_agent.utils.loggers import server_logger

router = APIRouter(prefix="/api/threads", tags=["chat-sse"])

logger = logging.getLogger(__name__)

_cancel_flags: dict[str, bool] = {}
_run_locks: dict[str, asyncio.Lock] = {}

_engine: AgentEngine | None = None


def configure(engine: AgentEngine) -> None:
    """Initialize the SSE module with engine. Called once at app startup."""
    global _engine
    _engine = engine


def _get_engine() -> AgentEngine:
    if _engine is None:
        raise RuntimeError("SSE module not configured. Call sse.configure() first.")
    return _engine


def _extract_existing_subsession_ids(tool_calls: list[dict[str, Any]]) -> set[str]:
    return {
        sub_session_id
        for tool_call in tool_calls
        if isinstance((sub_session_id := tool_call.get("sub_session_id")), str) and sub_session_id
    }


def _mark_stale_running_subagent_tool_calls_interrupted(
    tool_calls: list[dict[str, Any]],
    active_subagent_tool_call_ids: set[str],
) -> None:
    for tool_call in tool_calls:
        if not tool_call.get("is_subagent"):
            continue
        if tool_call.get("status") != "running":
            continue
        run_id = tool_call.get("runId") or tool_call.get("run_id")
        if isinstance(run_id, str) and run_id in active_subagent_tool_call_ids:
            continue
        tool_call["status"] = "interrupted"


def _enrich_action_requests_display_names(
    action_requests: list[dict[str, Any]],
    subagent_display_map: dict[str, str],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for action_request in action_requests:
        args = action_request.get("args")
        subagent_type = args.get("subagent_type") if isinstance(args, dict) else None
        if isinstance(subagent_type, str) and subagent_type in subagent_display_map:
            enriched.append({**action_request, "display_name": subagent_display_map[subagent_type]})
        elif action_request.get("name") in subagent_display_map:
            enriched.append({**action_request, "display_name": subagent_display_map[action_request["name"]]})
        else:
            enriched.append(action_request)
    return enriched


# --- Request Models ---


class RunStreamRequest(BaseModel):
    input: list[dict[str, Any]] | None = None
    command: dict[str, Any] | None = None
    preset_id: str = "chat"
    model: str = ""
    llm_params: dict[str, Any] | None = None
    replace_from_message_id: str | None = None
    history: list[dict[str, Any]] | None = None


# --- Endpoints ---


async def _authenticate_sse(request: Request):
    """Authenticate SSE request. Returns User or None. Returns None if auth not configured."""
    auth_service = getattr(request.app.state, "auth_service", None)
    if auth_service is None:
        return None  # Auth not configured, allow all (backward compat)

    from lc_agent.server.auth_middleware import _extract_token
    token = _extract_token(request)
    if not token:
        return None

    payload = auth_service.decode_token(token)
    if payload is None:
        return None

    from lc_agent.db.models_auth import User
    from sqlalchemy import select
    db = get_business_async_session()
    try:
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        return result.scalar_one_or_none()
    finally:
        await db.close()


async def _check_sse_auth(request: Request, thread_id: str) -> JSONResponse | None:
    """Return JSONResponse if access denied, None if allowed."""
    user = await _authenticate_sse(request)
    auth_service = getattr(request.app.state, "auth_service", None)
    if auth_service is not None and user is None:
        return JSONResponse(status_code=401, content={"detail": "认证失败"})

    if user is not None:
        from lc_agent.db.models import SessionMeta
        from sqlalchemy import select as sa_select
        _db = get_business_async_session()
        try:
            result = await _db.execute(sa_select(SessionMeta).where(SessionMeta.id == thread_id))
            session_meta = result.scalar_one_or_none()
            if session_meta:
                # 会话按账号隔离：admin 也不例外。
                # 未配 auth 的单机模式（__anonymous__）保持原样。
                if user.id == "__anonymous__":
                    pass
                elif not session_meta.user_id:
                    # 无主会话（user_id=""）：只有单机模式可进，登录用户一律拒绝
                    return JSONResponse(status_code=403, content={"detail": "权限不足"})
                elif session_meta.user_id != user.id:
                    return JSONResponse(status_code=403, content={"detail": "权限不足"})
        finally:
            await _db.close()

    return None


async def _check_sse_agent_access(request: Request, preset_id: str) -> JSONResponse | None:
    user = await _authenticate_sse(request)
    if user is None or user.role == "admin" or preset_id == "chat":
        return None

    from lc_agent.db.models_auth import UserAgentAccess
    from sqlalchemy import select

    db = get_business_async_session()
    try:
        result = await db.execute(
            select(UserAgentAccess).where(
                UserAgentAccess.user_id == user.id,
                UserAgentAccess.agent_id == preset_id,
            )
        )
        if result.scalar_one_or_none() is None:
            return JSONResponse(status_code=403, content={"detail": "无权使用此智能体"})
    finally:
        await db.close()

    return None


def _get_lock(thread_id: str) -> asyncio.Lock:
    if thread_id not in _run_locks:
        _run_locks[thread_id] = asyncio.Lock()
    return _run_locks[thread_id]


@router.post("/{thread_id}/runs/stream")
async def run_stream(thread_id: str, req: RunStreamRequest, request: Request):
    """Unified entry: send message or resume interrupt, returning SSE stream."""
    auth_error = await _check_sse_auth(request, thread_id)
    if auth_error is not None:
        return auth_error

    agent_access_error = await _check_sse_agent_access(request, req.preset_id)
    if agent_access_error is not None:
        return agent_access_error

    lock = _get_lock(thread_id)
    if lock.locked():
        _cancel_flags[thread_id] = True
        try:
            await asyncio.wait_for(lock.acquire(), timeout=10)
            lock.release()
        except asyncio.TimeoutError:
            async def timeout_stream():
                yield stream_utils.format_sse_event("error", {
                    "title": "请求超时",
                    "detail": "等待前一个请求完成超时，请稍后重试。",
                    "suggestions": ["稍后再次发送消息"],
                    "error_code": "LOCK_TIMEOUT",
                    "tech_detail": "Timed out waiting for previous run to complete",
                    "message": "Timed out waiting for previous run to complete",
                })

            return StreamingResponse(
                timeout_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )

    if req.command is not None:
        return await _resume_stream(thread_id, req, request)
    return await _send_stream(thread_id, req, request)


@router.post("/{thread_id}/runs/cancel")
async def cancel_run(thread_id: str, request: Request):
    """Cancel the currently active run for this thread."""
    user = await _authenticate_sse(request)
    auth_service = getattr(request.app.state, "auth_service", None)
    if auth_service is not None and user is None:
        return JSONResponse(status_code=401, content={"detail": "认证失败"})

    _cancel_flags[thread_id] = True
    return {"ok": True, "thread_id": thread_id}


@router.get("/{thread_id}/state")
async def get_thread_state(thread_id: str, request: Request, preset_id: str = "chat", model: str = ""):
    """Check thread state — primarily for pending interrupts."""
    auth_error = await _check_sse_auth(request, thread_id)
    if auth_error is not None:
        return auth_error

    agent_access_error = await _check_sse_agent_access(request, preset_id)
    if agent_access_error is not None:
        return agent_access_error

    engine = _get_engine()
    agent = engine._get_or_build_agent(preset_id, model)
    if agent is None:
        return {"has_interrupts": False, "error": "agent_not_found"}

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": engine.recursion_limit}
    try:
        graph_state = await agent.aget_state(config)
        interrupts = []
        if graph_state.tasks:
            for task in graph_state.tasks:
                for intr in (task.interrupts or ()):
                    interrupts.append({
                        "value": intr.value,
                        "id": getattr(intr, "id", None),
                    })
        return {"has_interrupts": bool(interrupts), "interrupts": interrupts}
    except Exception as e:
        return {"has_interrupts": False, "error": str(e)}


# --- Internal Stream Implementations ---


def _extract_text_from_blocks(content: list[dict[str, Any]]) -> str:
    """从 content blocks 提取纯文本（用于标题生成等场景）。"""
    parts = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "text_file":
                parts.append(block.get("name", ""))
    return " ".join(parts)


async def _send_stream(thread_id: str, req: RunStreamRequest, request: Request):
    """Handle new message: save to DB, stream agent response as SSE."""
    engine = _get_engine()
    content = req.input or []

    # 空输入校验
    if not content:
        async def error_stream():
            yield stream_utils.format_sse_event("error", {
                "title": "消息为空",
                "detail": "消息内容不能为空",
                "suggestions": ["请输入文本或附加图片/文件"],
                "error_code": "EMPTY_INPUT",
                "message": "Empty input",
            })

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    preset_id = req.preset_id
    model_id = req.model
    llm_params = req.llm_params
    lock = _get_lock(thread_id)
    _cancel_flags[thread_id] = False
    user = await _authenticate_sse(request)

    try:
        msg_count = await persistence.get_session_message_count(thread_id)
        is_first = msg_count == 0
        if is_first:
            preliminary_title = _extract_text_from_blocks(content)[:30].strip()
            await persistence.ensure_session(
                thread_id, preliminary_title, preset_id, model_id,
                user_id=user.id if user else "",
            )

        if req.replace_from_message_id:
            await persistence.truncate_from_message(thread_id, req.replace_from_message_id)
            await engine.reset_thread(thread_id)

        await persistence.save_ui_message(thread_id, "user", content)
        round_number = await persistence.get_session_user_message_count(thread_id)
    except Exception as e:
        traceback.print_exc()
        error = e

        async def error_stream():
            error_info = stream_utils.categorize_error(error)
            error_info["tech_detail"] = str(error)
            error_info["message"] = str(error)
            yield stream_utils.format_sse_event("error", error_info)

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    async def event_stream():
        nonlocal is_first
        await lock.acquire()
        try:
            usage_rounds: list[dict] = []
            usage_run_id = str(uuid.uuid4())
            usage_model_map = build_model_map(engine)
            round_start_time = time.time()
            stream_start_time = time.time()
            content_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            in_thinking = False
            last_event_time = time.time()
            active_subagent_tool_call_ids: set[str] = set()
            # Pre-warm project context cache so the pre-build below can use async git snapshot.
            try:
                _pre_preset = engine._resolve_preset(preset_id)
                if _pre_preset.project_mode and _pre_preset.project_root:
                    import asyncio as _aio
                    from pathlib import Path as _PP
                    from lc_agent.core.engine_helpers.project_context import _build_project_context_text
                    _pre_root = str(_PP(_pre_preset.project_root).expanduser().resolve())
                    if _pre_root not in engine._project_ctx_text_cache:
                        engine._project_ctx_text_cache[_pre_root] = await _aio.to_thread(
                            _build_project_context_text, _pre_root
                        )
            except Exception as _e:
                logger.warning("Failed to pre-warm project context cache: %s", _e)

            # Ensure the agent is built (and subagent tools are cached) before streaming
            try:
                engine._get_or_build_agent(preset_id, model_id, llm_params=llm_params)
            except Exception as _e:
                logger.warning("Failed to pre-build agent for subagent tool name lookup: %s", _e)
            subagent_display_map = engine.get_subagent_display_name_map(
                preset_id, model_id=model_id or "", llm_params=llm_params,
            )
            subagent_tool_names = engine.get_subagent_tool_names(
                preset_id, model_id=model_id or "", llm_params=llm_params,
            )
            subagent_tracker = SubAgentRunTracker(
                parent_thread_id=thread_id,
                user_id=user.id if user else "",
                subagent_display_map=subagent_display_map,
                tool_calls=tool_calls,
                usage_rounds=usage_rounds,
            )

            # Initialize sub-agent HTTP trace collector registry for this stream
            init_subagent_collector_registry()

            if is_first:
                preliminary_title = _extract_text_from_blocks(content)[:30].strip()
                yield stream_utils.format_sse_event("title_update", {
                    "thread_id": thread_id,
                    "title": preliminary_title,
                })

            stream_kwargs: dict[str, Any] = {}
            if model_id:
                stream_kwargs["model_id"] = model_id
            if llm_params:
                stream_kwargs["llm_params"] = llm_params
            if req.replace_from_message_id:
                stream_kwargs["history"] = req.history or []

            from lc_agent.tools.system_tools._file_change_tracker import bind_session_for_file_tracking
            bind_session_for_file_tracking(thread_id, round_number=round_number)

            from lc_agent.core.model_resolve import find_model
            model_info = find_model(model_id, engine.config) if model_id else None
            provider = model_info.provider if model_info else None
            resolved_model = (model_info.raw_model_id or model_id) if model_info else model_id
            trace_collector = HttpTraceCollector(provider=provider, model=resolved_model)
            trace_token = bind_http_trace_collector(trace_collector)

            try:
                stream = engine.chat_stream(
                    content,
                    thread_id,
                    preset_id,
                    user_id=user.id if user else "anonymous",
                    **stream_kwargs,
                )
                async for event in stream:
                    if _cancel_flags.get(thread_id):
                        for evt_type, evt_data in subagent_tracker.finalize_open_runs(status="cancelled"):
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                        await subagent_tracker.drain()
                        # 已产生的 token 消耗照常入账（取消≠免费）
                        await record_usage(
                            usage_rounds,
                            session_id=thread_id,
                            user_id=user.id if user else "",
                            agent_id=preset_id,
                            source="chat",
                            run_id=usage_run_id,
                        )
                        yield stream_utils.format_sse_event("cancelled", {})
                        return

                    if await request.is_disconnected():
                        _cancel_flags[thread_id] = True
                        for evt_type, evt_data in subagent_tracker.finalize_open_runs(status="cancelled"):
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                        await subagent_tracker.drain()
                        await record_usage(
                            usage_rounds,
                            session_id=thread_id,
                            user_id=user.id if user else "",
                            agent_id=preset_id,
                            source="chat",
                            run_id=usage_run_id,
                        )
                        return

                    in_thinking = stream_utils.accumulate_display_state(
                        event, content_parts, tool_calls, in_thinking,
                        subagent_tool_names=subagent_tool_names,
                        thread_id=thread_id,
                        subagent_display_map=subagent_display_map,
                        active_subagent_tool_call_ids=active_subagent_tool_call_ids,
                    )

                    for evt_type, evt_data in stream_utils.convert_stream_event(
                        event,
                        subagent_tool_names=subagent_tool_names,
                        subagent_display_map=subagent_display_map,
                        active_subagent_tool_call_ids=active_subagent_tool_call_ids,
                    ):
                        if evt_type == "subagent_start":
                            tool_call_id = evt_data.get("tool_call_id")
                            if isinstance(tool_call_id, str):
                                active_subagent_tool_call_ids.add(tool_call_id)
                        elif evt_type == "subagent_done":
                            tool_call_id = evt_data.get("tool_call_id")
                            if isinstance(tool_call_id, str):
                                active_subagent_tool_call_ids.discard(tool_call_id)
                        elif evt_type == "file_change":
                            asyncio.create_task(persistence.save_file_change(
                                evt_data.get("session_id", thread_id),
                                evt_data.get("file_path", ""),
                                evt_data.get("change_type", ""),
                                old_string=evt_data.get("old_string"),
                                new_string=evt_data.get("new_string"),
                                tool_call_id=evt_data.get("tool_call_id"),
                                move_destination=evt_data.get("move_destination"),
                                round_number=evt_data.get("round_number"),
                                line_start=evt_data.get("line_start"),
                                context_before=evt_data.get("context_before"),
                                context_after=evt_data.get("context_after"),
                            ))
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                            last_event_time = time.time()
                            continue
                        elif evt_type == "file_change_git_snapshot":
                            asyncio.create_task(persistence.save_git_base_hash(
                                evt_data.get("session_id", thread_id),
                                evt_data.get("git_base_hash", ""),
                            ))
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                            last_event_time = time.time()
                            continue
                        evt_type, evt_data = subagent_tracker.handle_event(evt_type, evt_data)
                        yield stream_utils.format_sse_event(evt_type, evt_data)
                        last_event_time = time.time()

                    prev_len = len(usage_rounds)
                    stream_utils.accumulate_usage(
                        event, usage_rounds,
                        default_model_id=model_id or "",
                        model_map=usage_model_map,
                    )
                    if len(usage_rounds) > prev_len:
                        usage_rounds[-1]["duration_ms"] = int((time.time() - round_start_time) * 1000)
                        round_start_time = time.time()
                        if not stream_utils.is_summarize_usage_row(usage_rounds[-1]):
                            yield stream_utils.format_sse_event("llm_usage", usage_rounds[-1])

                    if time.time() - last_event_time > 15:
                        yield stream_utils.SSE_HEARTBEAT
                        last_event_time = time.time()
            finally:
                if in_thinking:
                    content_parts.append("<!--THINK_END-->")
                reset_http_trace_collector(trace_token)

            interrupt_sent = False
            try:
                agent = engine._get_or_build_agent(preset_id, model_id, llm_params=llm_params)
                state_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": engine.recursion_limit}
                graph_state = await agent.aget_state(state_config)
                if graph_state.tasks:
                    all_interrupts = []
                    for task in graph_state.tasks:
                        for intr in (task.interrupts or ()):
                            all_interrupts.append({
                                "value": intr.value,
                                "id": getattr(intr, "id", None),
                            })
                    if all_interrupts:
                        interrupt_payload: dict[str, Any] = {
                            "message": "Tool requires approval",
                            "data": all_interrupts,
                        }
                        first_value = all_interrupts[0].get("value")
                        if isinstance(first_value, dict):
                            if "action_requests" in first_value:
                                reqs = first_value["action_requests"]
                                # Enrich with display_name for sub-agent tools
                                if subagent_display_map:
                                    reqs = _enrich_action_requests_display_names(reqs, subagent_display_map)
                                interrupt_payload["action_requests"] = reqs
                            if "review_configs" in first_value:
                                interrupt_payload["review_configs"] = first_value["review_configs"]
                        yield stream_utils.format_sse_event("interrupt", interrupt_payload)
                        interrupt_sent = True
            except Exception:
                server_logger.exception("Failed to check interrupt state")

            http_traces = trace_collector.snapshot()
            if http_traces:
                for i in range(len(http_traces)):
                    marker = f"\n<!--HTTP:{i}-->\n"
                    content_parts.append(marker)
                    yield stream_utils.format_sse_event("content", {"content": marker})

            done_payload: dict[str, Any] = {}
            chat_usage = stream_utils.split_chat_usage_rounds(usage_rounds)
            if chat_usage:
                done_payload["usage"] = chat_usage
            if http_traces:
                done_payload["http_traces"] = http_traces

            await subagent_tracker.drain()
            await record_usage(
                usage_rounds,
                session_id=thread_id,
                user_id=user.id if user else "",
                agent_id=preset_id,
                source="chat",
                run_id=usage_run_id,
            )

            if content_parts or tool_calls or usage_rounds or http_traces:
                await persistence.save_ui_message(
                    thread_id, "assistant",
                    [{"type": "text", "text": "".join(content_parts)}],
                    tool_calls=tool_calls or None,
                    usage={
                        "rounds": chat_usage,
                        "tool_call_count": len(tool_calls),
                        "total_duration_ms": int((time.time() - stream_start_time) * 1000),
                    },
                    http_traces=http_traces or None,
                )

            yield stream_utils.format_sse_event("done", done_payload)

            asyncio.create_task(persistence.increment_session_message_count(thread_id))

            if is_first:
                asyncio.create_task(
                    _generate_and_yield_title(thread_id, _extract_text_from_blocks(content), preset_id, model_id,
                                              user_id=user.id if user else "")
                )

        except Exception as e:
            traceback.print_exc()
            if "subagent_tracker" in locals():
                for evt_type, evt_data in subagent_tracker.finalize_open_runs(status="error"):
                    yield stream_utils.format_sse_event(evt_type, evt_data)
                await subagent_tracker.drain()
            await record_usage(
                usage_rounds,
                session_id=thread_id,
                user_id=user.id if user else "",
                agent_id=preset_id,
                source="chat",
                run_id=usage_run_id,
            )
            error_info = stream_utils.categorize_error(e)
            error_info["tech_detail"] = str(e)
            error_info["message"] = str(e)
            yield stream_utils.format_sse_event("error", error_info)
        finally:
            lock.release()
            _cancel_flags.pop(thread_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _resume_stream(thread_id: str, req: RunStreamRequest, request: Request):
    """Handle interrupt resume: stream continued agent response as SSE."""
    engine = _get_engine()
    preset_id = req.preset_id
    model_id = req.model
    llm_params = req.llm_params
    lock = _get_lock(thread_id)
    _cancel_flags[thread_id] = False
    user = await _authenticate_sse(request)

    # Restore project context so tool path/cwd constraints are active during resume.
    try:
        _resume_preset = engine._resolve_preset(preset_id)
        _resume_root = _resume_preset.project_root if _resume_preset.project_mode else None
        if _resume_root:
            from pathlib import Path as _RP
            _resume_root = str(_RP(_resume_root).expanduser().resolve())
        from lc_agent.tools.system_tools._config import set_active_project
        set_active_project(_resume_root, _resume_preset.project_extra_dirs if _resume_preset.project_mode else None)
    except Exception:
        pass  # Non-fatal; resume proceeds without project context if preset resolution fails

    resume_value = req.command.get("resume", {}) if req.command else {}

    async def event_stream():
        await lock.acquire()
        try:
            # Resume continues the existing round: round = current user message count.
            round_number = await persistence.get_session_user_message_count(thread_id)
            from lc_agent.tools.system_tools._file_change_tracker import bind_session_for_file_tracking
            bind_session_for_file_tracking(thread_id, round_number=round_number)

            usage_rounds: list[dict] = []
            usage_run_id = str(uuid.uuid4())
            usage_model_map = build_model_map(engine)
            round_start_time = time.time()
            stream_start_time = time.time()
            content_parts: list[str] = []
            in_thinking = False
            last_event_time = time.time()
            active_subagent_tool_call_ids: set[str] = set()

            existing_tool_calls, existing_trace_count = await persistence.load_resume_context(thread_id)
            tool_calls: list[dict[str, Any]] = list(existing_tool_calls)
            # Pre-warm project context cache before pre-build
            try:
                _rp = engine._resolve_preset(preset_id)
                if _rp.project_mode and _rp.project_root:
                    import asyncio as _aio
                    from pathlib import Path as _PP2
                    from lc_agent.core.engine_helpers.project_context import _build_project_context_text
                    _rroot = str(_PP2(_rp.project_root).expanduser().resolve())
                    if _rroot not in engine._project_ctx_text_cache:
                        engine._project_ctx_text_cache[_rroot] = await _aio.to_thread(
                            _build_project_context_text, _rroot
                        )
            except Exception as _e:
                logger.warning("Failed to pre-warm project context cache (resume): %s", _e)
            # Ensure the agent is built (and subagent tools are cached) before streaming
            try:
                engine._get_or_build_agent(preset_id, model_id, llm_params=llm_params)
            except Exception as _e:
                logger.warning("Failed to pre-build agent for subagent tool name lookup: %s", _e)
            subagent_display_map = engine.get_subagent_display_name_map(
                preset_id, model_id=model_id or "", llm_params=llm_params,
            )
            subagent_tool_names = engine.get_subagent_tool_names(
                preset_id, model_id=model_id or "", llm_params=llm_params,
            )
            subagent_tracker = SubAgentRunTracker(
                parent_thread_id=thread_id,
                user_id=user.id if user else "",
                subagent_display_map=subagent_display_map,
                tool_calls=tool_calls,
                existing_subsession_ids=_extract_existing_subsession_ids(tool_calls),
                usage_rounds=usage_rounds,
            )
            from langgraph.types import Command

            agent = engine._get_or_build_agent(preset_id, model_id, llm_params=llm_params)
            if agent is None:
                yield stream_utils.format_sse_event("error", {
                    "title": "缺少 AI 代理配置",
                    "detail": "没有找到用于恢复对话的 AI 代理配置，可能是配置已变更。",
                    "suggestions": ["刷新页面后重试", "重新选择 AI 助手并开始新对话"],
                    "error_code": "AGENT_NOT_FOUND",
                    "tech_detail": "No agent found for resume",
                })
                return

            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": engine.recursion_limit}

            from lc_agent.core.model_resolve import find_model
            model_info = find_model(model_id, engine.config) if model_id else None
            provider = model_info.provider if model_info else None
            resolved_model = (model_info.raw_model_id or model_id) if model_info else model_id
            trace_collector = HttpTraceCollector(
                provider=provider, model=resolved_model, seq_offset=existing_trace_count,
            )
            trace_token = bind_http_trace_collector(trace_collector)

            try:
                stream_kwargs: dict[str, Any] = {"config": config, "version": "v2"}
                if engine._should_use_memory_context(preset_id):
                    from lc_agent.core.memory import AgentRuntimeContext, normalize_memory_user_id

                    stream_kwargs["context"] = AgentRuntimeContext(
                        user_id=normalize_memory_user_id(user.id if user else "anonymous"),
                    )
                async for event in agent.astream_events(
                    Command(resume=resume_value),
                    **stream_kwargs,
                ):
                    if _cancel_flags.get(thread_id):
                        for evt_type, evt_data in subagent_tracker.finalize_open_runs(status="cancelled"):
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                        await subagent_tracker.drain()
                        # 已产生的 token 消耗照常入账（取消≠免费）
                        await record_usage(
                            usage_rounds,
                            session_id=thread_id,
                            user_id=user.id if user else "",
                            agent_id=preset_id,
                            source="chat",
                            run_id=usage_run_id,
                        )
                        yield stream_utils.format_sse_event("cancelled", {})
                        return

                    if await request.is_disconnected():
                        _cancel_flags[thread_id] = True
                        for evt_type, evt_data in subagent_tracker.finalize_open_runs(status="cancelled"):
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                        await subagent_tracker.drain()
                        await record_usage(
                            usage_rounds,
                            session_id=thread_id,
                            user_id=user.id if user else "",
                            agent_id=preset_id,
                            source="chat",
                            run_id=usage_run_id,
                        )
                        return

                    in_thinking = stream_utils.accumulate_display_state(
                        event, content_parts, tool_calls, in_thinking,
                        subagent_tool_names=subagent_tool_names,
                        thread_id=thread_id,
                        subagent_display_map=subagent_display_map,
                        active_subagent_tool_call_ids=active_subagent_tool_call_ids,
                    )

                    for evt_type, evt_data in stream_utils.convert_stream_event(
                        event,
                        subagent_tool_names=subagent_tool_names,
                        subagent_display_map=subagent_display_map,
                        active_subagent_tool_call_ids=active_subagent_tool_call_ids,
                    ):
                        if evt_type == "subagent_start":
                            tool_call_id = evt_data.get("tool_call_id")
                            if isinstance(tool_call_id, str):
                                active_subagent_tool_call_ids.add(tool_call_id)
                        elif evt_type == "subagent_done":
                            tool_call_id = evt_data.get("tool_call_id")
                            if isinstance(tool_call_id, str):
                                active_subagent_tool_call_ids.discard(tool_call_id)
                        elif evt_type == "file_change":
                            asyncio.create_task(persistence.save_file_change(
                                evt_data.get("session_id", thread_id),
                                evt_data.get("file_path", ""),
                                evt_data.get("change_type", ""),
                                old_string=evt_data.get("old_string"),
                                new_string=evt_data.get("new_string"),
                                tool_call_id=evt_data.get("tool_call_id"),
                                move_destination=evt_data.get("move_destination"),
                                round_number=evt_data.get("round_number"),
                                line_start=evt_data.get("line_start"),
                                context_before=evt_data.get("context_before"),
                                context_after=evt_data.get("context_after"),
                            ))
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                            last_event_time = time.time()
                            continue
                        elif evt_type == "file_change_git_snapshot":
                            asyncio.create_task(persistence.save_git_base_hash(
                                evt_data.get("session_id", thread_id),
                                evt_data.get("git_base_hash", ""),
                            ))
                            yield stream_utils.format_sse_event(evt_type, evt_data)
                            last_event_time = time.time()
                            continue
                        evt_type, evt_data = subagent_tracker.handle_event(evt_type, evt_data)
                        yield stream_utils.format_sse_event(evt_type, evt_data)
                        last_event_time = time.time()

                    prev_len = len(usage_rounds)
                    stream_utils.accumulate_usage(
                        event, usage_rounds,
                        default_model_id=model_id or "",
                        model_map=usage_model_map,
                    )
                    if len(usage_rounds) > prev_len:
                        usage_rounds[-1]["duration_ms"] = int((time.time() - round_start_time) * 1000)
                        round_start_time = time.time()
                        if not stream_utils.is_summarize_usage_row(usage_rounds[-1]):
                            yield stream_utils.format_sse_event("llm_usage", usage_rounds[-1])

                    if time.time() - last_event_time > 15:
                        yield stream_utils.SSE_HEARTBEAT
                        last_event_time = time.time()
            finally:
                if in_thinking:
                    content_parts.append("<!--THINK_END-->")
                reset_http_trace_collector(trace_token)

            interrupt_sent = False
            try:
                graph_state = await agent.aget_state(config)
                if graph_state.tasks:
                    all_interrupts = []
                    for task in graph_state.tasks:
                        for intr in (task.interrupts or ()):
                            all_interrupts.append({
                                "value": intr.value,
                                "id": getattr(intr, "id", None),
                            })
                    if all_interrupts:
                        interrupt_payload: dict[str, Any] = {
                            "message": "Tool requires approval",
                            "data": all_interrupts,
                        }
                        first_value = all_interrupts[0].get("value")
                        if isinstance(first_value, dict):
                            if "action_requests" in first_value:
                                reqs = first_value["action_requests"]
                                if subagent_display_map:
                                    reqs = _enrich_action_requests_display_names(reqs, subagent_display_map)
                                interrupt_payload["action_requests"] = reqs
                            if "review_configs" in first_value:
                                interrupt_payload["review_configs"] = first_value["review_configs"]
                        yield stream_utils.format_sse_event("interrupt", interrupt_payload)
                        interrupt_sent = True
            except Exception:
                server_logger.exception("Failed to check interrupt state after resume")

            if isinstance(resume_value, dict):
                permanently_allow = resume_value.get("permanently_allow")
                if permanently_allow and hasattr(request.app.state, "permissions"):
                    # Only admin can permanently allow tools
                    if user and user.role == "admin":
                        request.app.state.permissions.allow_tool(permanently_allow)

            _mark_stale_running_subagent_tool_calls_interrupted(
                tool_calls,
                active_subagent_tool_call_ids,
            )

            http_traces = trace_collector.snapshot()
            if http_traces:
                for i in range(len(http_traces)):
                    marker = f"\n<!--HTTP:{existing_trace_count + i}-->\n"
                    content_parts.append(marker)
                    yield stream_utils.format_sse_event("content", {"content": marker})
            done_payload: dict[str, Any] = {"is_resume": True}
            resume_chat_usage = stream_utils.split_chat_usage_rounds(usage_rounds)
            if resume_chat_usage:
                done_payload["usage"] = resume_chat_usage
            if http_traces:
                done_payload["http_traces"] = http_traces

            await subagent_tracker.drain()
            await record_usage(
                usage_rounds,
                session_id=thread_id,
                user_id=user.id if user else "",
                agent_id=preset_id,
                source="chat",
                run_id=usage_run_id,
            )

            new_content = "".join(content_parts)
            if new_content or tool_calls or usage_rounds or http_traces:
                await persistence.append_to_last_assistant_message(
                    thread_id, new_content,
                    all_tool_calls=tool_calls or None,
                    usage_rounds=resume_chat_usage or None,
                    http_traces=http_traces or None,
                    resume_duration_ms=int((time.time() - stream_start_time) * 1000),
                )

            yield stream_utils.format_sse_event("done", done_payload)

        except Exception as e:
            traceback.print_exc()
            if "subagent_tracker" in locals():
                for evt_type, evt_data in subagent_tracker.finalize_open_runs(status="error"):
                    yield stream_utils.format_sse_event(evt_type, evt_data)
                await subagent_tracker.drain()
            await record_usage(
                usage_rounds,
                session_id=thread_id,
                user_id=user.id if user else "",
                agent_id=preset_id,
                source="chat",
                run_id=usage_run_id,
            )
            error_info = stream_utils.categorize_error(e)
            error_info["tech_detail"] = str(e)
            error_info["message"] = str(e)
            yield stream_utils.format_sse_event("error", error_info)
        finally:
            lock.release()
            _cancel_flags.pop(thread_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_and_yield_title(
    thread_id: str,
    first_message: str,
    preset_id: str,
    model_id: str,
    user_id: str = "",
) -> None:
    """Background task: generate title and save to DB.

    Note: since the SSE stream is already closed by the time this runs,
    the title update will be delivered on the next state query or page refresh.
    """
    engine = _get_engine()
    title_usage: list[dict] = []
    title = await persistence.generate_title(
        engine, thread_id, first_message, preset_id, model_id, usage_sink=title_usage,
    )
    if title_usage:
        try:
            await record_usage(
                title_usage,
                session_id=thread_id,
                user_id=user_id,
                agent_id=preset_id,
                source="title",
                run_id=str(uuid.uuid4()),
            )
        except Exception:
            server_logger.exception("Failed to record title usage")
    if title:
        await persistence.save_title(thread_id, title)
