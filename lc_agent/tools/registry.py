# lc_agent/tools/registry.py
from __future__ import annotations

import functools
import re
from typing import Any, Callable, overload

from langchain_core.tools import BaseTool, StructuredTool

_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class ToolRegistry:
    """Central registry for all tools, supporting groups and filtering."""

    _instance: ToolRegistry | None = None
    _global_tools: dict[str, dict[str, Any]] = {}
    _group_descriptions: dict[str, str] = {}
    _disabled_groups: set[str] = set()

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
        Also excludes runtime-disabled groups.
        """
        if allowed_groups is None:
            tools = self.get_all_tools()
        elif not allowed_groups:
            return []
        else:
            tools = self.get_tools_by_groups(allowed_groups)

        if self._disabled_groups:
            tools = [
                t for t in tools
                if self._global_tools.get(t.name, {}).get("group") not in self._disabled_groups
            ]
        return tools

    def get_group_names(self) -> list[str]:
        """Return unique list of all registered group names."""
        groups = set()
        for entry in self._global_tools.values():
            if entry["group"]:
                groups.add(entry["group"])
        return sorted(groups)

    def get_group_info(self) -> list[dict[str, str]]:
        """Return group id + description pairs."""
        groups = {}
        for entry in self._global_tools.values():
            g = entry["group"]
            if g and g not in groups:
                groups[g] = self._group_descriptions.get(g, g)
        return [{"id": gid, "description": desc} for gid, desc in sorted(groups.items())]

    def register(self, func: Callable, group: str = "", group_description: str = "") -> BaseTool:
        """Register a function as a tool.

        Args:
            func: The function to register as a tool.
            group: ASCII group identifier, used as prefix in tool name.
                   Must match ^[a-zA-Z0-9_-]+$ if provided.
            group_description: Human-readable group description for UI display.
                   If not provided, defaults to the group value.
        """
        if group and not _TOOL_NAME_PATTERN.match(group):
            raise ValueError(
                f"Tool group '{group}' must match ^[a-zA-Z0-9_-]+$. "
                f"Use ASCII for 'group' and put display name in 'group_description'."
            )

        if group:
            name = f"{group}__{func.__name__}"
        else:
            name = func.__name__

        if group and group_description:
            self._group_descriptions[group] = group_description

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
def tool(*, group: str = "", group_description: str = "") -> Callable[[Callable], Callable]: ...


def tool(func: Callable | None = None, *, group: str = "", group_description: str = ""):
    """Decorator to register a function as an agent tool.

    Usage:
        @tool
        def my_func(...): ...

        @tool(group="file_mgmt", group_description="文件管理")
        def my_func(...): ...
    """
    registry = ToolRegistry()

    def decorator(fn: Callable) -> Callable:
        registry.register(fn, group=group, group_description=group_description)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
