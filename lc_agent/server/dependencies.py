# lc_agent/server/dependencies.py
from fastapi import Request

from lc_agent.core.engine import AgentEngine
from lc_agent.db.engine import get_async_session as _get_db_session
from lc_agent.tools.registry import ToolRegistry


def get_engine(request: Request) -> AgentEngine:
    """Dependency to get the AgentEngine from app state."""
    return request.app.state.engine


def get_registry(request: Request) -> ToolRegistry:
    """Dependency to get the ToolRegistry singleton."""
    return ToolRegistry()


async def get_db_session(request: Request):
    """Dependency to get an async DB session."""
    db_url = request.app.state.config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
    session = _get_db_session(db_url)
    try:
        yield session
    finally:
        await session.close()
