# lc_agent/app.py
from __future__ import annotations

import uvicorn
from fastapi import WebSocket, WebSocketDisconnect

from lc_agent.core.engine import AgentEngine
from lc_agent.server.app import create_app
from lc_agent.server.websocket import ChatWebSocketHandler


class LcAgentApp:
    """Main application orchestrator — creates engine, server, and runs."""

    def __init__(self, config: dict, host: str = "127.0.0.1", port: int = 8000):
        self.config = config
        self.host = host
        self.port = port
        self.engine = AgentEngine(config)
        self.fastapi_app = create_app(config)
        self.fastapi_app.state.engine = self.engine
        self._ws_handler = ChatWebSocketHandler(self.engine)
        self._setup_websocket_route()

    def _setup_websocket_route(self):
        @self.fastapi_app.websocket("/ws/chat/{thread_id}")
        async def websocket_chat(websocket: WebSocket, thread_id: str):
            tid = await self._ws_handler.connect(websocket, thread_id)
            try:
                while True:
                    data = await websocket.receive_json()
                    await self._ws_handler.handle_message(websocket, tid, data)
            except WebSocketDisconnect:
                await self._ws_handler.disconnect(tid)

        @self.fastapi_app.websocket("/ws/chat")
        async def websocket_chat_auto(websocket: WebSocket):
            tid = await self._ws_handler.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_json()
                    await self._ws_handler.handle_message(websocket, tid, data)
            except WebSocketDisconnect:
                await self._ws_handler.disconnect(tid)

    def run(self):
        """Start the server (blocking)."""
        from lc_agent import __version__

        print(f"\n  lc_agent v{__version__}")
        print(f"  Web UI: http://{self.host}:{self.port}")
        print(f"  API Docs: http://{self.host}:{self.port}/api/docs\n")
        uvicorn.run(self.fastapi_app, host=self.host, port=self.port)
