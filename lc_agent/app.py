# lc_agent/app.py
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain_agentskills import SkillsToolkit
from langchain_agentskills.loaders import CompositeSkillLoader, DirectorySkillLoader

from lc_agent.core.engine import AgentEngine
from lc_agent.db.engine import init_db
from lc_agent.mcp.manager import McpManager
from lc_agent.server.app import create_app, mount_static_files
from lc_agent.server.websocket import ChatWebSocketHandler
from lc_agent.skills.filtered_loader import FilteredSkillLoader


class LcAgentApp:
    """Main application orchestrator — creates engine, server, and runs."""

    def __init__(self, config: dict, host: str = "127.0.0.1", port: int = 8000):
        self.config = config
        self.host = host
        self.port = port
        self._db_url = config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
        self._checkpoint_path = config.get("database", {}).get("checkpoint_path", "./lc_agent_checkpoints.db")
        self.engine = AgentEngine(config)
        skills_dirs = config.get("skills", ["./skills"])
        existing_dirs = [d for d in skills_dirs if Path(d).is_dir()]
        if existing_dirs:
            inner_loaders = [DirectorySkillLoader(d) for d in existing_dirs]
            inner = inner_loaders[0] if len(inner_loaders) == 1 else CompositeSkillLoader(inner_loaders)
            self.filtered_loader = FilteredSkillLoader(inner)
            self.skills_toolkit = SkillsToolkit(loaders=[self.filtered_loader])
        else:
            self.filtered_loader = None
            self.skills_toolkit = None
        mcp_config = config.get("mcp_servers", {})
        self.mcp_manager = McpManager(mcp_config, on_state_change=self._on_mcp_state_change)
        self.fastapi_app = create_app(config, lifespan=self._lifespan)
        self.fastapi_app.state.mcp_manager = self.mcp_manager
        self.fastapi_app.state.skills_toolkit = self.skills_toolkit
        self.fastapi_app.state.filtered_loader = self.filtered_loader
        self.engine._skills_toolkit = self.skills_toolkit
        self.engine._mcp_manager = self.mcp_manager
        self.fastapi_app.state.engine = self.engine
        self._ws_handler = ChatWebSocketHandler(self.engine, db_url=self._db_url)
        self._setup_websocket_route()
        mount_static_files(self.fastapi_app)

    def _on_mcp_state_change(self):
        self.engine._mcp_generation += 1

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """FastAPI lifespan: startup and shutdown logic."""
        import asyncio

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

        await self._load_presets_from_db()

        async def _connect_mcp_background():
            try:
                await self.mcp_manager.connect_all()
                connected = [s for s in self.mcp_manager.servers if s.status == "connected"]
                if connected:
                    print(f"[MCP] Connected: {[s.name for s in connected]}")
            except Exception as e:
                print(f"[MCP] Background connection error: {e}")

        asyncio.create_task(_connect_mcp_background())
        try:
            yield
        finally:
            await self.mcp_manager.shutdown()

    def _setup_websocket_route(self):
        import asyncio

        async def _ws_loop(websocket: WebSocket, tid: str):
            streaming_task: asyncio.Task | None = None
            try:
                while True:
                    if streaming_task and not streaming_task.done():
                        recv_coro = websocket.receive_json()
                        recv_task = asyncio.ensure_future(recv_coro)
                        done, _ = await asyncio.wait(
                            [recv_task, streaming_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if recv_task in done:
                            data = recv_task.result()
                            if data.get("type") == "cancel":
                                self._ws_handler._cancel_flags[tid] = True
                        if streaming_task in done:
                            streaming_task = None
                            if recv_task not in done:
                                recv_task.cancel()
                                try:
                                    await recv_task
                                except (asyncio.CancelledError, Exception):
                                    pass
                    else:
                        data = await websocket.receive_json()
                        msg_type = data.get("type", "message")
                        if msg_type == "cancel":
                            continue
                        streaming_task = asyncio.create_task(
                            self._ws_handler.handle_message(websocket, tid, data)
                        )
            except WebSocketDisconnect:
                if streaming_task and not streaming_task.done():
                    streaming_task.cancel()
                await self._ws_handler.disconnect(tid)
            except Exception as e:
                print(f"[WS] Loop error: {e}")
                if streaming_task and not streaming_task.done():
                    streaming_task.cancel()
                await self._ws_handler.disconnect(tid)

        @self.fastapi_app.websocket("/ws/chat/{thread_id}")
        async def websocket_chat(websocket: WebSocket, thread_id: str):
            tid = await self._ws_handler.connect(websocket, thread_id)
            await _ws_loop(websocket, tid)

        @self.fastapi_app.websocket("/ws/chat")
        async def websocket_chat_auto(websocket: WebSocket):
            tid = await self._ws_handler.connect(websocket)
            await _ws_loop(websocket, tid)

    async def _load_presets_from_db(self):
        """Load user-created presets from database on startup."""
        from lc_agent.db.engine import get_async_session
        from lc_agent.db.models import AgentPresetDB
        from lc_agent.core.models import AgentPreset
        from sqlalchemy import select

        session = get_async_session(self._db_url)
        try:
            stmt = select(AgentPresetDB)
            result = await session.execute(stmt)
            for row in result.scalars().all():
                preset = AgentPreset(
                    id=row.id,
                    name=row.name,
                    system_prompt=row.system_prompt,
                    default_model=row.default_model,
                    allowed_tool_groups=row.allowed_tool_groups,
                    allowed_mcp_servers=row.allowed_mcp_servers,
                    allowed_skills=row.allowed_skills,
                    dangerous_tools=row.dangerous_tools,
                )
                self.engine._presets[preset.id] = preset
            loaded = len(self.engine._presets)
            if loaded:
                print(f"[Agents] Loaded {loaded} user presets from database")
        except Exception as e:
            print(f"[Warning] Failed to load presets from DB: {e}")
        finally:
            await session.close()

    def add_agent(self, name: str, graph, description: str = ""):
        """Register a pre-built CompiledStateGraph as a named agent.

        Args:
            name: Unique agent identifier
            graph: A compiled LangGraph (must have ainvoke and astream_events)
            description: Human-readable description
        """
        if name in self.engine._agents:
            raise ValueError(f"Agent '{name}' already registered")

        from lc_agent.core.models import AgentPreset

        self.engine._agents[name] = graph
        self.engine._agent_mcp_gen[name] = self.engine._mcp_generation
        preset = AgentPreset(
            id=name,
            name=name,
            system_prompt=description or f"Custom agent: {name}",
            default_model="custom",
            source="code",
        )
        self.engine._custom_presets[name] = preset

    def run(self):
        """Start the server (blocking)."""
        from lc_agent import __version__

        print(f"\n  lc_agent v{__version__}")
        print(f"  Web UI: http://{self.host}:{self.port}")
        print(f"  API Docs: http://{self.host}:{self.port}/api/docs\n")
        uvicorn.run(self.fastapi_app, host=self.host, port=self.port)
