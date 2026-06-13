# lc_agent/server/websocket.py
import asyncio
import uuid
from typing import Any

from fastapi import WebSocket

from lc_agent.core.engine import AgentEngine


class ChatWebSocketHandler:
    """Handles WebSocket connections for streaming chat."""

    def __init__(self, engine: AgentEngine):
        self.engine = engine
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
            import time
            content = data.get("content", "")
            preset_id = data.get("preset_id", "__chat__")
            self._cancel_flags[thread_id] = False
            usage_rounds: list[dict] = []
            round_start_time = time.time()

            is_first = self._message_counts.get(thread_id, 0) == 0
            if is_first:
                preliminary_title = content[:30].strip()
                await websocket.send_json({
                    "type": "title_update",
                    "thread_id": thread_id,
                    "title": preliminary_title,
                })
                asyncio.create_task(self._save_title(thread_id, preliminary_title))

            try:
                async for event in self.engine.chat_stream(content, thread_id, preset_id):
                    if self._cancel_flags.get(thread_id):
                        await websocket.send_json({"type": "cancelled"})
                        return
                    await self._send_event(websocket, event)
                    prev_len = len(usage_rounds)
                    self._accumulate_usage(event, usage_rounds)
                    if len(usage_rounds) > prev_len:
                        usage_rounds[-1]["duration_ms"] = int((time.time() - round_start_time) * 1000)
                        round_start_time = time.time()

                done_payload: dict = {"type": "done"}
                if usage_rounds:
                    done_payload["usage"] = usage_rounds
                await websocket.send_json(done_payload)

                self._message_counts[thread_id] = self._message_counts.get(thread_id, 0) + 1
                if self._message_counts[thread_id] == 1:
                    asyncio.create_task(
                        self._generate_and_push_title(websocket, thread_id, content, preset_id)
                    )
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

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

                config = {"configurable": {"thread_id": thread_id}}
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

    async def _save_title(self, thread_id: str, title: str):
        """Save title to DB without pushing to client."""
        try:
            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository
            session = get_async_session()
            try:
                repo = SessionRepository(session)
                await repo.update(thread_id, title=title)
            finally:
                await session.close()
        except Exception:
            pass

    async def _generate_and_push_title(self, websocket: WebSocket, thread_id: str, first_message: str, preset_id: str = "__chat__"):
        """Generate title from first message using the agent's model, save to DB, and push to client."""
        try:
            model_id = ""
            if preset_id in self.engine.BUILTIN_IDS:
                for bp in self.engine.get_builtin_presets():
                    if bp.id == preset_id:
                        model_id = bp.default_model
                        break
            else:
                preset = self.engine._presets.get(preset_id) or self.engine._custom_presets.get(preset_id)
                if preset:
                    model_id = preset.default_model
            title = await self.engine.generate_title(first_message, model_id)

            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository
            session = get_async_session()
            try:
                repo = SessionRepository(session)
                await repo.update(thread_id, title=title)
            finally:
                await session.close()

            await websocket.send_json({"type": "title_update", "thread_id": thread_id, "title": title})
        except Exception as e:
            print(f"[WS] Title generation failed: {e}")

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
            tool_input = event.get("data", {}).get("input", {})
            await websocket.send_json({
                "type": "tool_call",
                "name": event.get("name", ""),
                "run_id": event.get("run_id", ""),
                "args": tool_input,
            })

        elif kind == "on_tool_end":
            output = event.get("data", {}).get("output", "")
            result_str = str(output)
            await websocket.send_json({
                "type": "tool_result",
                "name": event.get("name", ""),
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
