# lc_agent/app.py
from __future__ import annotations

import uvicorn
from fastapi import WebSocket, WebSocketDisconnect

from lc_agent.core.engine import AgentEngine
from lc_agent.db.engine import init_db
from lc_agent.server.app import create_app
from lc_agent.server.websocket import ChatWebSocketHandler


class LcAgentApp:
    """Main application orchestrator — creates engine, server, and runs."""

    def __init__(self, config: dict, host: str = "127.0.0.1", port: int = 8000):
        self.config = config
        self.host = host
        self.port = port
        self._db_url = config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
        self._checkpoint_path = config.get("database", {}).get("checkpoint_path", "./lc_agent_checkpoints.db")
        self.engine = AgentEngine(config)
        from lc_agent.skills.scanner import SkillScanner
        skills_dir = config.get("skills", {}).get("directory", "./skills")
        self.skill_scanner = SkillScanner(skills_dir)
        self.skill_scanner.scan()
        from lc_agent.mcp.manager import McpManager
        mcp_config = config.get("mcp_servers", {})
        self.mcp_manager = McpManager(mcp_config)
        self.fastapi_app = create_app(config)
        self.fastapi_app.state.mcp_manager = self.mcp_manager
        self.fastapi_app.state.skill_scanner = self.skill_scanner
        self.engine._skill_scanner = self.skill_scanner
        self.fastapi_app.state.engine = self.engine
        self._ws_handler = ChatWebSocketHandler(self.engine)
        self._setup_websocket_route()

        @self.fastapi_app.on_event("startup")
        async def startup():
            await init_db(self._db_url)
            try:
                from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
                import aiosqlite
                conn = await aiosqlite.connect(self._checkpoint_path)
                saver = AsyncSqliteSaver(conn)
                await saver.setup()
                self.engine._checkpointer = saver
            except Exception as e:
                print(f"[Warning] Checkpoint saver setup failed, using None: {e}")

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
