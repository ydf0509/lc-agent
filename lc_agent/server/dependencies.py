# lc_agent/server/dependencies.py
from fastapi import Request

from lc_agent.core.engine import AgentEngine
from lc_agent.tools.registry import ToolRegistry


def get_engine(request: Request) -> AgentEngine:
    """Dependency to get the AgentEngine from app state."""
    return request.app.state.engine


def get_registry(request: Request) -> ToolRegistry:
    """Dependency to get the ToolRegistry singleton."""
    return ToolRegistry()
