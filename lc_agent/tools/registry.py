# lc_agent/tools/registry.py
from __future__ import annotations

import functools
from typing import Any, Callable, overload

from langchain_core.tools import BaseTool, StructuredTool


class ToolRegistry:
    """Central registry for all tools, supporting groups and filtering."""

    _instance: ToolRegistry | None = None
    _global_tools: dict[str, dict[str, Any]] = {}

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_all_tools(self) -> list[BaseTool]:
        """Return all registered tools as LangChain BaseTool instances."""
        return [entry["tool"] for entry in self._global_tools.values()]

    def get_tools_by_groups(self, groups: list[str]) -> list[BaseTool]:
        """Return tools belonging to specified groups."""
        return [
            entry["tool"]
            for entry in self._global_tools.values()
            if entry["group"] in groups
        ]

    def get_filtered_tools(self, allowed_groups: list[str] | None) -> list[BaseTool]:
        """Filter tools by allowed groups (three-value semantics).

        None = all allowed, [] = none allowed, ["a","b"] = only those groups.
        """
        if allowed_groups is None:
            return self.get_all_tools()
        if not allowed_groups:
            return []
        return self.get_tools_by_groups(allowed_groups)

    def get_group_names(self) -> list[str]:
        """Return unique list of all registered group names."""
        groups = set()
        for entry in self._global_tools.values():
            if entry["group"]:
                groups.add(entry["group"])
        return sorted(groups)

    def register(self, func: Callable, group: str = "") -> BaseTool:
        """Register a function as a tool."""
        name = f"{group}__{func.__name__}" if group else func.__name__
        lc_tool = StructuredTool.from_function(
            func=func,
            name=name,
            description=func.__doc__ or f"Tool: {name}",
        )
        self._global_tools[name] = {"tool": lc_tool, "group": group, "func": func}
        return lc_tool


@overload
def tool(func: Callable) -> Callable: ...


@overload
def tool(*, group: str = "") -> Callable[[Callable], Callable]: ...


def tool(func: Callable | None = None, *, group: str = ""):
    """Decorator to register a function as an agent tool.

    Usage:
        @tool
        def my_func(...): ...

        @tool(group="utils")
        def my_func(...): ...
    """
    registry = ToolRegistry()

    def decorator(fn: Callable) -> Callable:
        registry.register(fn, group=group)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
