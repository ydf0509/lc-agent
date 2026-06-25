# lc_agent/server/websocket.py
import asyncio
import time
import uuid
from typing import Any

from fastapi import WebSocket

from lc_agent.core.engine import AgentEngine
from lc_agent.core.http_trace import (
    HttpTraceCollector,
    bind_http_trace_collector,
    reset_http_trace_collector,
)


class ChatWebSocketHandler:
    """Handles WebSocket connections for streaming chat."""

    def __init__(self, engine: AgentEngine, db_url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
        self.engine = engine
        self.db_url = db_url
        self.active_connections: dict[str, WebSocket] = {}
        self._message_counts: dict[str, int] = {}
        self._cancel_flags: dict[str, bool] = {}

    async def connect(self, websocket: WebSocket, thread_id: str | None = None) -> str:
        """Accept WebSocket connection."""
        await websocket.accept()
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        self.active_connections[thread_id] = websocket
        await websocket.send_json({"type": "connected", "thread_id": thread_id})
        return thread_id

    async def disconnect(self, thread_id: str):
        """Clean up on disconnect."""
        self.active_connections.pop(thread_id, None)
        self._cancel_flags.pop(thread_id, None)

    async def handle_message(self, websocket: WebSocket, thread_id: str, data: dict):
        """Process incoming message and stream response."""
        msg_type = data.get("type", "message")

        if msg_type == "cancel":
            self._cancel_flags[thread_id] = True
            return

        if msg_type == "message":
            content = data.get("content", "")
            preset_id = data.get("preset_id", "__chat__")
            model_id = data.get("model", "")
            replace_from_message_id = data.get("replace_from_message_id")
            replay_history = data.get("history") or []
            self._cancel_flags[thread_id] = False
            usage_rounds: list[dict] = []
            round_start_time = time.time()
            stream_start_time = time.time()
            assistant_content_parts: list[str] = []
            assistant_tool_calls: list[dict[str, Any]] = []
            assistant_in_thinking = False

            is_first = self._message_counts.get(thread_id, 0) == 0
            if is_first:
                preliminary_title = content[:30].strip()
                await websocket.send_json({
                    "type": "title_update",
                    "thread_id": thread_id,
                    "title": preliminary_title,
                })
                await self._ensure_session(thread_id, preliminary_title, preset_id, model_id)

            try:
                if replace_from_message_id:
                    await self._truncate_from_message(thread_id, replace_from_message_id)
                    await self.engine.reset_thread(thread_id)
                await self._save_ui_message(thread_id, "user", content)
                stream_kwargs: dict[str, Any] = {}
                if model_id:
                    stream_kwargs["model_id"] = model_id
                if replace_from_message_id:
                    stream_kwargs["history"] = replay_history
                model_info = self.engine._find_model(model_id) if model_id else None
                provider = model_info.provider if model_info else None
                resolved_model = model_info.id if model_info else model_id
                trace_collector = HttpTraceCollector(provider=provider, model=resolved_model)
                trace_token = bind_http_trace_collector(trace_collector)
                try:
                    stream = self.engine.chat_stream(content, thread_id, preset_id, **stream_kwargs)
                    async for event in stream:
                        if self._cancel_flags.get(thread_id):
                            await websocket.send_json({"type": "cancelled"})
                            return
                        assistant_in_thinking = self._accumulate_assistant_display_state(
                            event,
                            assistant_content_parts,
                            assistant_tool_calls,
                            assistant_in_thinking,
                        )
                        await self._send_event(websocket, event)
                        prev_len = len(usage_rounds)
                        self._accumulate_usage(event, usage_rounds)
                        if len(usage_rounds) > prev_len:
                            usage_rounds[-1]["duration_ms"] = int((time.time() - round_start_time) * 1000)
                            round_start_time = time.time()
                            await websocket.send_json({
                                "type": "llm_usage",
                                **usage_rounds[-1],
                            })
                finally:
                    reset_http_trace_collector(trace_token)

                if assistant_in_thinking:
                    assistant_content_parts.append("<!--THINK_END-->")
                    assistant_in_thinking = False

                has_text = any(
                    p for p in assistant_content_parts
                    if p and not p.startswith("<!--") and not p.endswith("-->")
                )
                if not has_text and (assistant_tool_calls or usage_rounds):
                    print(
                        f"[WS] Warning: stream ended with {len(usage_rounds)} LLM rounds, "
                        f"{len(assistant_tool_calls)} tool calls, but no final text answer. "
                        f"Possible cause: model output token limit exhausted by reasoning."
                    )

                http_traces = trace_collector.snapshot()
                # Inject HTTP trace markers into assistant content for inline block rendering
                if http_traces:
                    for i in range(len(http_traces)):
                        marker = f"\n<!--HTTP:{i}-->\n"
                        assistant_content_parts.append(marker)
                        await websocket.send_json({
                            "type": "content",
                            "content": marker,
                        })
                done_payload: dict = {"type": "done"}
                if usage_rounds:
                    done_payload["usage"] = usage_rounds
                if http_traces:
                    done_payload["http_traces"] = http_traces
                if assistant_content_parts or assistant_tool_calls or usage_rounds or http_traces:
                    await self._save_ui_message(
                        thread_id,
                        "assistant",
                        "".join(assistant_content_parts),
                        tool_calls=assistant_tool_calls or None,
                        usage={
                            "rounds": usage_rounds,
                            "tool_call_count": len(assistant_tool_calls),
                            "total_duration_ms": int((time.time() - stream_start_time) * 1000),
                        },
                        http_traces=http_traces or None,
                    )
                await websocket.send_json(done_payload)

                self._message_counts[thread_id] = self._message_counts.get(thread_id, 0) + 1
                asyncio.create_task(self._increment_session_message_count(thread_id))
                if self._message_counts[thread_id] == 1:
                    asyncio.create_task(
                        self._generate_and_push_title(websocket, thread_id, content, preset_id, model_id)
                    )
            except Exception as e:
                print(f"[WS] handle_message error: {e}")
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except Exception:
                    pass

        elif msg_type == "interrupt_response":
            approved = data.get("approved", False)
            preset_id = data.get("preset_id", "__chat__")
            self._cancel_flags[thread_id] = False
            try:
                from langgraph.types import Command

                agent = self.engine._agents.get(preset_id)
                if agent is None:
                    await websocket.send_json({"type": "error", "message": "No agent found for resume"})
                    return

                config = {"configurable": {"thread_id": thread_id}, "recursion_limit": self.engine.recursion_limit}
                resume_value = {"approved": approved}

                async for event in agent.astream_events(
                    Command(resume=resume_value),
                    config=config,
                    version="v2",
                ):
                    if self._cancel_flags.get(thread_id):
                        await websocket.send_json({"type": "cancelled"})
                        return
                    await self._send_event(websocket, event)
                await websocket.send_json({"type": "done"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

    async def _ensure_session(self, thread_id: str, title: str, agent_id: str, model: str):
        """Create session metadata on first websocket message if it does not exist."""
        try:
            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository

            session = get_async_session(self.db_url)
            try:
                repo = SessionRepository(session)
                existing = await repo.get_by_id(thread_id)
                if existing is None:
                    await repo.create(id=thread_id, title=title or "新对话", agent_id=agent_id, model=model, message_count=0)
                else:
                    await repo.update(thread_id, title=title or existing.title, agent_id=agent_id, model=model or existing.model)
            finally:
                await session.close()
        except Exception:
            pass

    async def _increment_session_message_count(self, thread_id: str):
        """Increment persisted session message count after a completed round."""
        try:
            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository

            session = get_async_session(self.db_url)
            try:
                await SessionRepository(session).increment_messages(thread_id)
            finally:
                await session.close()
        except Exception:
            pass

    async def _save_title(self, thread_id: str, title: str):
        """Save title to DB without pushing to client."""
        try:
            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository
            session = get_async_session(self.db_url)
            try:
                repo = SessionRepository(session)
                await repo.update(thread_id, title=title)
            finally:
                await session.close()
        except Exception:
            pass

    async def _generate_and_push_title(
        self,
        websocket: WebSocket,
        thread_id: str,
        first_message: str,
        preset_id: str = "__chat__",
        selected_model_id: str = "",
    ):
        """Generate title from first message using the agent's model, save to DB, and push to client."""
        try:
            model_id = selected_model_id
            if preset_id in self.engine.BUILTIN_IDS:
                for bp in self.engine.get_builtin_presets():
                    if bp.id == preset_id:
                        model_id = model_id or bp.default_model
                        break
            else:
                preset = self.engine._presets.get(preset_id) or self.engine._custom_presets.get(preset_id)
                if preset:
                    model_id = model_id or preset.default_model
            title = await self.engine.generate_title(first_message, model_id)

            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository
            session = get_async_session(self.db_url)
            try:
                repo = SessionRepository(session)
                await repo.update(thread_id, title=title)
            finally:
                await session.close()

            await websocket.send_json({"type": "title_update", "thread_id": thread_id, "title": title})
        except Exception as e:
            print(f"[WS] Title generation failed: {e}")

    async def _save_ui_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        usage: dict[str, Any] | None = None,
        http_traces: list[dict[str, Any]] | None = None,
    ):
        """Persist replay data for the web chat history."""
        try:
            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import ChatUiMessageRepository

            session = get_async_session(self.db_url)
            try:
                repo = ChatUiMessageRepository(session)
                await repo.create(
                    session_id=thread_id,
                    role=role,
                    content=content,
                    tool_calls=tool_calls,
                    usage=usage,
                    http_traces=http_traces,
                )
            finally:
                await session.close()
        except Exception as e:
            print(f"[WS] Failed to persist UI message for {thread_id}: {e}")

    async def _truncate_from_message(self, thread_id: str, message_id: str):
        """Delete persisted UI messages from the edited anchor onward."""
        try:
            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import ChatUiMessageRepository

            session = get_async_session(self.db_url)
            try:
                repo = ChatUiMessageRepository(session)
                await repo.truncate_from_message(thread_id, message_id)
            finally:
                await session.close()
        except Exception as e:
            print(f"[WS] Failed to truncate UI messages for {thread_id}: {e}")

    def _accumulate_assistant_display_state(
        self,
        event: dict,
        content_parts: list[str],
        tool_calls: list[dict[str, Any]],
        in_thinking: bool,
    ) -> bool:
        """Mirror the client display markers so history can replay the same layout."""
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
                content_parts.append(chunk.content)

        elif kind == "on_tool_start":
            if in_thinking:
                content_parts.append("<!--THINK_END-->")
                in_thinking = False

            tool_idx = len(tool_calls)
            tool_calls.append(
                {
                    "name": event.get("name", ""),
                    "runId": event.get("run_id", ""),
                    "args": event.get("data", {}).get("input", {}),
                    "status": "running",
                    "startTime": int(time.time() * 1000),
                }
            )
            content_parts.append(f"\n<!--TOOL:{tool_idx}-->\n")

        elif kind == "on_tool_end":
            output = event.get("data", {}).get("output", "")
            result_str = str(output)
            run_id = event.get("run_id", "")
            name = event.get("name", "")
            tool_call = next(
                (
                    tc
                    for tc in tool_calls
                    if (run_id and tc.get("runId") == run_id)
                    or (not run_id and tc.get("name") == name and tc.get("status") == "running")
                ),
                None,
            )
            if tool_call:
                start_time = tool_call.get("startTime")
                tool_call["result"] = result_str
                tool_call["status"] = "done"
                tool_call["duration"] = int(time.time() * 1000) - start_time if start_time else None
                tool_call["resultLength"] = len(result_str)

        return in_thinking

    def _accumulate_usage(self, event: dict, usage_rounds: list[dict]):
        """Extract token usage from on_chat_model_end events."""
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
            def _get(obj, key, default=0):
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

    async def _send_event(self, websocket: WebSocket, event: dict):
        """Convert LangGraph astream_events v2 to client-friendly format."""
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk:
                additional = getattr(chunk, "additional_kwargs", None) or {}
                reasoning = additional.get("reasoning_content") or additional.get("reasoning")
                if reasoning:
                    await websocket.send_json({"type": "thinking", "content": reasoning})
                if hasattr(chunk, "content") and chunk.content:
                    await websocket.send_json({"type": "token", "content": chunk.content})

        elif kind == "on_tool_start":
            tool_name = event.get("name", "")
            tool_input = event.get("data", {}).get("input", {})

            if tool_name == "write_todos" and isinstance(tool_input, dict):
                todos = tool_input.get("todos", [])
                await websocket.send_json({"type": "todos", "todos": todos})
            else:
                await websocket.send_json({
                    "type": "tool_call",
                    "name": tool_name,
                    "run_id": event.get("run_id", ""),
                    "args": tool_input,
                })

        elif kind == "on_tool_end":
            tool_name = event.get("name", "")
            if tool_name == "write_todos":
                return
            output = event.get("data", {}).get("output", "")
            result_str = str(output)
            await websocket.send_json({
                "type": "tool_result",
                "name": tool_name,
                "result": result_str,
            })

        elif kind == "on_chain_end":
            data_output = event.get("data", {}).get("output", {})
            if isinstance(data_output, dict) and "__interrupt" in str(data_output):
                await websocket.send_json({
                    "type": "interrupt",
                    "message": "Tool requires approval",
                    "data": data_output,
                })
