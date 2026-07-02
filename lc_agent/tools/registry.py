# lc_agent/tools/registry.py
from __future__ import annotations

import asyncio
import functools
import inspect
import re
from typing import Any, Callable, Literal, overload

from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.tools.base import ArgsSchema

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

    def register(
        self,
        func: Callable,
        *,
        name: str = "",
        group: str = "",
        group_description: str = "",
        description: str | None = None,
        return_direct: bool = False,
        args_schema: ArgsSchema | None = None,
        infer_schema: bool = True,
        response_format: Literal["content", "content_and_artifact"] = "content",
        parse_docstring: bool = False,
        error_on_invalid_docstring: bool = True,
        extras: dict[str, Any] | None = None,
    ) -> BaseTool:
        """Register a function as a tool.

        Accepts all official langchain_core @tool parameters plus lc-agent
        extensions (group, group_description).

        Args:
            func: The function to register.
            name: Explicit tool name.  Priority: name > group__func_name > func_name.
            group: ASCII group id for filtering.  Must match ^[a-zA-Z0-9_-]+$.
            group_description: Human-readable group label for the UI.
            description: Override tool description (otherwise uses docstring).
            return_direct: Return result directly without continuing agent loop.
            args_schema: Custom Pydantic schema for tool input.
            infer_schema: Infer schema from function signature.
            response_format: ``"content"`` or ``"content_and_artifact"``.
            parse_docstring: Parse param descriptions from Google-style docstring.
            error_on_invalid_docstring: Raise on bad docstring when parse_docstring=True.
            extras: Provider-specific extra fields (e.g. Anthropic cache_control).
        """
        if group and not _TOOL_NAME_PATTERN.match(group):
            raise ValueError(
                f"Tool group '{group}' must match ^[a-zA-Z0-9_-]+$. "
                f"Use ASCII for 'group' and put display name in 'group_description'."
            )
        if name and not _TOOL_NAME_PATTERN.match(name):
            raise ValueError(
                f"Tool name '{name}' must match ^[a-zA-Z0-9_-]+$."
            )

        if name:
            resolved_name = name
        elif group:
            resolved_name = f"{group}__{func.__name__}"
        else:
            resolved_name = func.__name__

        if resolved_name in self._global_tools:
            existing = self._global_tools[resolved_name]["func"]
            raise ValueError(
                f"Tool name '{resolved_name}' already registered by "
                f"{existing.__module__}.{existing.__qualname__}. "
                f"Use a different name or group to avoid collision."
            )

        if group and group_description:
            self._group_descriptions[group] = group_description

        from_fn_kwargs: dict[str, Any] = {
            "name": resolved_name,
            "description": description or func.__doc__ or f"Tool: {resolved_name}",
            "return_direct": return_direct,
            "infer_schema": infer_schema,
            "response_format": response_format,
            "parse_docstring": parse_docstring,
            "error_on_invalid_docstring": error_on_invalid_docstring,
        }
        if args_schema is not None:
            from_fn_kwargs["args_schema"] = args_schema

        if inspect.iscoroutinefunction(func):
            from_fn_kwargs["coroutine"] = func
        else:
            from_fn_kwargs["func"] = func

        lc_tool = StructuredTool.from_function(**from_fn_kwargs)

        if extras:
            lc_tool.metadata = {**(lc_tool.metadata or {}), "extras": extras}

        self._global_tools[resolved_name] = {"tool": lc_tool, "group": group, "func": func}
        return lc_tool


# ---------------------------------------------------------------------------
# @tool decorator — fully compatible with langchain_core.tools.convert.tool
# ---------------------------------------------------------------------------

@overload
def tool(name_or_callable: Callable, /) -> Callable: ...

@overload
def tool(
    name_or_callable: str,
    *,
    description: str | None = ...,
    return_direct: bool = ...,
    args_schema: ArgsSchema | None = ...,
    infer_schema: bool = ...,
    response_format: Literal["content", "content_and_artifact"] = ...,
    parse_docstring: bool = ...,
    error_on_invalid_docstring: bool = ...,
    extras: dict[str, Any] | None = ...,
    group: str = ...,
    group_description: str = ...,
) -> Callable[[Callable], Callable]: ...

@overload
def tool(
    *,
    name: str = ...,
    description: str | None = ...,
    return_direct: bool = ...,
    args_schema: ArgsSchema | None = ...,
    infer_schema: bool = ...,
    response_format: Literal["content", "content_and_artifact"] = ...,
    parse_docstring: bool = ...,
    error_on_invalid_docstring: bool = ...,
    extras: dict[str, Any] | None = ...,
    group: str = ...,
    group_description: str = ...,
) -> Callable[[Callable], Callable]: ...


def tool(
    name_or_callable: str | Callable | None = None,
    *,
    name: str = "",
    description: str | None = None,
    return_direct: bool = False,
    args_schema: ArgsSchema | None = None,
    infer_schema: bool = True,
    response_format: Literal["content", "content_and_artifact"] = "content",
    parse_docstring: bool = False,
    error_on_invalid_docstring: bool = True,
    extras: dict[str, Any] | None = None,
    group: str = "",
    group_description: str = "",
):
    """Register a function as an agent tool.

    Fully compatible with ``langchain_core.tools.convert.tool`` parameter
    names and calling conventions, with additional ``group`` / ``group_description``
    extensions for lc-agent's tool-group system.

    Supported calling patterns (same as official @tool)::

        @tool                                   # bare decorator
        def my_func(...): ...

        @tool("custom_name")                    # positional string → name
        def my_func(...): ...

        @tool(name="ask_user")                  # keyword name
        def ask_user_impl(...): ...

        @tool(description="...", parse_docstring=True)
        def my_func(...): ...

    lc-agent extensions::

        @tool(group="file_mgmt", group_description="文件管理")
        def my_func(...): ...

    Name resolution: name (kwarg) > name_or_callable (str) > group__func > func.
    """
    registry = ToolRegistry()

    resolved_name = name
    if not resolved_name and isinstance(name_or_callable, str):
        resolved_name = name_or_callable

    def decorator(fn: Callable) -> Callable:
        registry.register(
            fn,
            name=resolved_name,
            group=group,
            group_description=group_description,
            description=description,
            return_direct=return_direct,
            args_schema=args_schema,
            infer_schema=infer_schema,
            response_format=response_format,
            parse_docstring=parse_docstring,
            error_on_invalid_docstring=error_on_invalid_docstring,
            extras=extras,
        )

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper

    if callable(name_or_callable):
        return decorator(name_or_callable)
    return decorator
