"""Converts MCP tool schemas into LangChain StructuredTool instances."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model


def _build_pydantic_model(tool_name: str, input_schema: dict) -> type[BaseModel]:
    """Dynamically create a Pydantic model from JSON Schema."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    fields: dict[str, Any] = {}
    for prop_name, prop_def in properties.items():
        python_type = _json_type_to_python(prop_def.get("type", "string"))
        description = prop_def.get("description", "")
        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            fields[prop_name] = (python_type | None, Field(default=None, description=description))

    if not fields:
        fields["placeholder"] = (str | None, Field(default=None, description="no params"))

    model_name = f"McpInput_{tool_name}"
    return create_model(model_name, **fields)


def _json_type_to_python(json_type: str) -> type:
    """Map JSON Schema type to Python type."""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, str)


def create_langchain_tools_from_schemas(
    server_name: str,
    tool_schemas: list[dict],
    invoke_fn: Any = None,
) -> list[StructuredTool]:
    """Convert MCP tool schemas to LangChain StructuredTool list.

    Args:
        server_name: MCP server name for namespacing
        tool_schemas: List of {name, description, input_schema}
        invoke_fn: Optional async callable(tool_name, args) -> result
    """
    tools = []
    for schema in tool_schemas:
        name = schema["name"]
        description = schema.get("description", "")
        input_schema = schema.get("input_schema", {"type": "object", "properties": {}})

        args_model = _build_pydantic_model(name, input_schema)
        full_name = f"mcp__{server_name}__{name}"

        if invoke_fn:
            async def _invoke(invoke=invoke_fn, tool_name=name, **kwargs):
                filtered = {k: v for k, v in kwargs.items() if v is not None}
                return await invoke(tool_name, filtered)

            tool = StructuredTool.from_function(
                func=None,
                coroutine=_invoke,
                name=full_name,
                description=f"[MCP:{server_name}] {description}",
                args_schema=args_model,
            )
        else:
            def _placeholder(full=full_name, **kwargs):
                return f"MCP tool {full} not connected"

            tool = StructuredTool.from_function(
                func=_placeholder,
                name=full_name,
                description=f"[MCP:{server_name}] {description}",
                args_schema=args_model,
            )

        tools.append(tool)

    return tools


def mcp_tool_names_to_display(server_name: str, tool_names: list[str]) -> list[dict]:
    """Convert MCP tool names to display format."""
    return [
        {"name": f"mcp__{server_name}__{name}", "group": f"mcp__{server_name}", "description": f"MCP tool: {name}"}
        for name in tool_names
    ]
