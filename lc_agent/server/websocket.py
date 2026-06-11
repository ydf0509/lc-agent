# lc_agent/server/websocket.py
import uuid
from typing import Any

from fastapi import WebSocket

from lc_agent.core.engine import AgentEngine


class ChatWebSocketHandler:
    """Handles WebSocket connections for streaming chat."""

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self.active_connections: dict[str, WebSocket] = {}

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

    async def handle_message(self, websocket: WebSocket, thread_id: str, data: dict):
        """Process incoming message and stream response."""
        msg_type = data.get("type", "message")

        if msg_type == "message":
            content = data.get("content", "")
            try:
                async for event in self.engine.chat_stream(content, thread_id):
                    await self._send_event(websocket, event)
                await websocket.send_json({"type": "done"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

        elif msg_type == "interrupt_response":
            decision = data.get("decision", {})
            await websocket.send_json({"type": "ack", "message": "interrupt handled"})

    async def _send_event(self, websocket: WebSocket, event: dict):
        """Convert LangGraph astream_events v2 to client-friendly format."""
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
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
            await websocket.send_json({
                "type": "tool_result",
                "name": event.get("name", ""),
                "result": str(output)[:2000],
            })
