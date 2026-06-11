# lc_agent/__init__.py
"""lc_agent — LangChain Agent framework with built-in Web UI."""

__version__ = "0.1.0"

from lc_agent.app import LcAgentApp
from lc_agent.config.loader import load_config
from lc_agent.tools.registry import ToolRegistry, tool

__all__ = [
    "LcAgentApp",
    "load_config",
    "ToolRegistry",
    "tool",
    "__version__",
]
