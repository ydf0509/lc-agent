# lc_agent/app.py

from contextlib import asynccontextmanager
from collections.abc import Callable
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from langchain_agentskills import SkillsToolkit
from langchain_agentskills.loaders import CompositeSkillLoader, DirectorySkillLoader

from lc_agent.config import (
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_DATABASE_URL,
    get_config,
    get_config_value,
    set_config,
)
from lc_agent.config.schema import MemoryConfig
from lc_agent.core.auth import AuthService
from lc_agent.core.checkpointer import build_checkpointer, is_postgres_url
from lc_agent.core.engine import AgentEngine
from lc_agent.core.memory import aclose_memory_store, create_sqlite_memory_store
from lc_agent.core.permissions import PermissionsService
from lc_agent.db.engine import get_async_session, init_db
from lc_agent.db.models_auth import User
from lc_agent.mcp.manager import McpManager
from lc_agent.server.app import create_app, mount_static_files
from lc_agent.server.automation import AutomationScheduler
from lc_agent.server import sse as sse_module
from lc_agent.skills.filtered_loader import FilteredSkillLoader
from lc_agent.skills.script_executor import patch_windows_script_executor
from lc_agent.utils.loggers import app_logger, mcp_logger


def _resolve_sqlite_url(url: str, root: Path) -> str:
    prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
    for prefix in prefixes:
        if not url.startswith(prefix):
            continue
        path_part = url[len(prefix):]
        if path_part in (":memory:", ""):
            return url
        path = Path(path_part)
        if path.is_absolute():
            return url
        return f"{prefix}{(root / path).resolve().as_posix()}"
    return url


def _resolve_file_path(path: str, root: Path) -> str:
    if path == ":memory:":
        return path
    file_path = Path(path)
    if file_path.is_absolute():
        return str(file_path)
    return str((root / file_path).resolve())


class LcAgentApp:
    """Main application orchestrator — creates engine, server, and runs."""

    def __init__(self, config: dict | None = None, host: str = "127.0.0.1", port: int = 8000):
        if config is None:
            config = get_config()
        else:
            set_config(config)
        self.config = config
        project_root = Path(config.get("_project_root") or Path.cwd())
        database_config = self.config.setdefault("database", {})
        database_config["url"] = _resolve_sqlite_url(
            database_config.get("url", DEFAULT_DATABASE_URL),
            project_root,
        )
        database_config["checkpoint_path"] = _resolve_file_path(
            database_config.get("checkpoint_path", DEFAULT_CHECKPOINT_PATH),
            project_root,
        )
        self.host = host
        self.port = port
        self._db_url = database_config["url"]
        self._checkpoint_path = database_config["checkpoint_path"]
        # A PostgreSQL URL wins over checkpoint_path; both are kept so existing
        # SQLite configs keep working without edits. A relative SQLite path in
        # checkpoint_url is resolved like checkpoint_path, not against the CWD.
        checkpoint_url_raw = database_config.get("checkpoint_url", "").strip()
        if checkpoint_url_raw and not is_postgres_url(checkpoint_url_raw):
            checkpoint_url_raw = _resolve_file_path(checkpoint_url_raw, project_root)
        self._checkpoint_url = checkpoint_url_raw or self._checkpoint_path
        self._checkpointer_bundle = None
        permissions_path = get_config_value(config, "permissions.path", "./permissions.jsonc")
        self._permissions_service = PermissionsService(permissions_path=Path(permissions_path))
        self.engine = AgentEngine(config)
        skills_dirs = list(config.get("skills", ["./skills"]))
        contrib_dir = Path(__file__).parent / "skills" / "contrib_skills"
        if contrib_dir.is_dir():
            skills_dirs.insert(0, str(contrib_dir))
        existing_dirs = [
            str(Path(d).expanduser().resolve())
            for d in skills_dirs
            if Path(d).is_dir()
        ]
        if existing_dirs:
            inner_loaders = [DirectorySkillLoader(d) for d in existing_dirs]
            inner = inner_loaders[0] if len(inner_loaders) == 1 else CompositeSkillLoader(inner_loaders)
            self.filtered_loader = FilteredSkillLoader(inner, global_skill_dirs=existing_dirs)
            self.skills_toolkit = SkillsToolkit(loaders=[self.filtered_loader])
            patch_windows_script_executor(self.skills_toolkit)
        else:
            self.filtered_loader = None
            self.skills_toolkit = None
        mcp_config = config.get("mcpServers", {})
        self.mcp_manager = McpManager(mcp_config, on_state_change=self._on_mcp_state_change)
        self.fastapi_app = create_app(config, lifespan=self._lifespan)
        self.fastapi_app.state.mcp_manager = self.mcp_manager
        self.fastapi_app.state.skills_toolkit = self.skills_toolkit
        self.fastapi_app.state.filtered_loader = self.filtered_loader
        self.engine._skills_toolkit = self.skills_toolkit
        self.engine._mcp_manager = self.mcp_manager
        self.fastapi_app.state.engine = self.engine
        self.fastapi_app.state.permissions = self._permissions_service
        self.engine._permissions_service = self._permissions_service
        self.fastapi_app.state.db_url = self._db_url
        self.fastapi_app.state.checkpoint_path = self._checkpoint_path
        sse_module.configure(self.engine, self._db_url)
        self.automation_scheduler = AutomationScheduler(self.engine, self._db_url, self.fastapi_app)
        self.fastapi_app.state.automation_scheduler = self.automation_scheduler
        mount_static_files(self.fastapi_app)

    def _on_mcp_state_change(self):
        self.engine._mcp_generation += 1

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """FastAPI lifespan: startup and shutdown logic."""
        import asyncio

        memory_store = None
        try:
            await init_db(self._db_url)
            await self._init_auth(app)
            try:
                self._checkpointer_bundle = await build_checkpointer(self._checkpoint_url)
                self.engine._checkpointer = self._checkpointer_bundle.saver
            except Exception:
                app_logger.exception("Checkpoint saver setup failed, using None")

            memory_config = self.config.get("memory")
            if memory_config is None:
                memory_config = MemoryConfig().model_dump()
            if get_config_value(memory_config, "enabled", False):
                memory_type = get_config_value(memory_config, "type", "sqlite")
                if memory_type != "sqlite":
                    raise ValueError("Only sqlite long-term memory is supported")
                memory_path = _resolve_file_path(
                    get_config_value(memory_config, "path", "./lc_agent_memory.db"),
                    Path(self.config.get("_project_root") or Path.cwd()),
                )
                memory_store = await create_sqlite_memory_store(memory_path, memory_config=memory_config)
                self.engine._store = memory_store

            await self._load_presets_from_db()
            await self.automation_scheduler.start()

            async def _connect_mcp_background():
                try:
                    await self.mcp_manager.connect_all()
                    connected = [s for s in self.mcp_manager.servers if s.status == "connected"]
                    if connected:
                        mcp_logger.info("Connected MCP servers: %s", [s.name for s in connected])
                except Exception:
                    mcp_logger.exception("Background MCP connection error")

            asyncio.create_task(_connect_mcp_background())
            yield
        finally:
            await self.automation_scheduler.stop()
            if self._checkpointer_bundle is not None:
                await self._checkpointer_bundle.aclose()
                self._checkpointer_bundle = None
                self.engine._checkpointer = None
            if memory_store is not None:
                await aclose_memory_store(memory_store)
                self.engine._store = None
            await self.mcp_manager.shutdown()

    async def _init_auth(self, app: FastAPI) -> None:
        """Initialize auth service and ensure at least one admin exists."""
        auth_config = self.config.get("auth", {})
        secret = auth_config.get("secret", "")
        if not secret:
            app_logger.warning("auth.secret not configured, authentication disabled")
            return
        if len(secret) < 16:
            raise ValueError("Auth secret must be at least 16 characters")

        token_expire_days = auth_config.get("token_expire_days", 7)
        auth_service = AuthService(secret=secret, token_expire_days=token_expire_days)
        app.state.auth_service = auth_service

        from lc_agent.db.models import SessionMeta
        from sqlalchemy import select

        db = get_async_session(self._db_url)
        try:
            result = await db.execute(select(User).where(User.role == "admin"))
            admin = result.scalar_one_or_none()
            if admin is None:
                password = "123456"
                admin = User(
                    username="admin",
                    password_hash=auth_service.hash_password(password),
                    role="admin",
                )
                db.add(admin)

                await db.execute(
                    SessionMeta.__table__.update().where(SessionMeta.user_id == "").values(user_id=admin.id)
                )

                await db.commit()
                app_logger.warning("Created initial admin user with default password; change it immediately")
            else:
                app_logger.info("Admin user exists: %s", admin.username)
        finally:
            await db.close()

    async def _load_presets_from_db(self):
        """Load user-created presets from database on startup."""
        from lc_agent.db.engine import get_async_session
        from lc_agent.db.models import AgentPresetDB
        from lc_agent.db.repository import PromptRepository
        from lc_agent.core.models import AgentPreset, SubAgentLink
        from sqlalchemy import select

        session = get_async_session(self._db_url)
        try:
            prompt_repo = PromptRepository(session)
            stmt = select(AgentPresetDB)
            result = await session.execute(stmt)
            for row in result.scalars().all():
                extra = await prompt_repo.resolve_extra_prompts(row.id)
                preset = AgentPreset(
                    id=row.id,
                    name=row.name,
                    display_name=row.display_name,
                    system_prompt=row.system_prompt,
                    default_model=row.default_model,
                    default_delegation_description=row.default_delegation_description or "",
                    can_be_subagent=row.can_be_subagent,
                    allowed_tool_groups=row.allowed_tool_groups,
                    allowed_mcp_servers=row.allowed_mcp_servers,
                    allowed_skills=row.allowed_skills,
                    llm_params=row.llm_params,
                    subagents=[SubAgentLink.model_validate(item) for item in row.subagents] if row.subagents else None,
                    enable_general_purpose_subagent=row.enable_general_purpose_subagent,
                    project_mode=row.project_mode,
                    project_root=row.project_root,
                    project_extra_dirs=row.project_extra_dirs,
                    extra_skill_dirs=row.extra_skill_dirs,
                    extra_system_prompts=extra,
                )
                self.engine._presets[preset.id] = preset
            loaded = len(self.engine._presets)
            if loaded:
                app_logger.info("Loaded %s user presets from database", loaded)
        except Exception:
            app_logger.exception("Failed to load presets from DB")
        finally:
            await session.close()

    def add_agent(
        self,
        name: str,
        graph=None,
        description: str = "",
        delegation_description: str = "",
        display_name: str | None = None,
        graph_factory: Callable[[str, dict[str, Any] | None], Any] | None = None,
    ):
        """Register a code-defined graph or a lazy graph factory as a named agent.

        Args:
            name: Unique agent identifier (ASCII slug recommended)
            graph: A compiled LangGraph (must have ainvoke and astream_events)
            graph_factory: Builds a graph from the selected model and runtime LLM
                parameters after startup resources such as MCP schemas are ready.
            description: Human-readable description
            delegation_description: Default delegation guidance for parent agents
            display_name: Optional human-readable display name (can be non-ASCII)
        """
        if name in self.engine._agents or name in self.engine._custom_presets:
            raise ValueError(f"Agent '{name}' already registered")
        if (graph is None) == (graph_factory is None):
            raise ValueError("Provide exactly one of graph or graph_factory")

        from lc_agent.core.models import AgentPreset

        if graph is not None:
            self.engine._agents[name] = graph
            self.engine._agent_mcp_gen[name] = self.engine._mcp_generation
        else:
            self.engine.register_code_agent_factory(name, graph_factory)
        preset = AgentPreset(
            id=name,
            name=name,
            display_name=display_name,
            system_prompt=description or f"Custom agent: {name}",
            default_model="custom",
            default_delegation_description=delegation_description,
            can_be_subagent=bool(delegation_description.strip()),
            allowed_tool_groups=[],
            allowed_mcp_servers=[],
            allowed_skills=[],
            source="code",
            default_enabled=False,
        )
        self.engine._custom_presets[name] = preset

    def run(self):
        """Start the server (blocking)."""
        from lc_agent import __version__

        app_logger.info("lc_agent v%s", __version__)
        app_logger.info("Web UI: http://%s:%s", self.host, self.port)
        app_logger.info("API Docs: http://%s:%s/api/docs", self.host, self.port)
        uvicorn.run(self.fastapi_app, host=self.host, port=self.port)
