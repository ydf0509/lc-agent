import pytest
from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas


def test_create_langchain_tools_basic():
    """Should create StructuredTool from MCP schema."""
    schemas = [
        {
            "name": "read_file",
            "description": "Read a file from disk",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"],
            },
        }
    ]

    tools = create_langchain_tools_from_schemas("filesystem", schemas)
    assert len(tools) == 1
    assert tools[0].name == "mcp__filesystem__read_file"
    assert "Read a file" in tools[0].description


def test_create_langchain_tools_empty():
    """Empty schemas should return empty list."""
    tools = create_langchain_tools_from_schemas("test", [])
    assert tools == []


def test_tool_has_correct_group():
    """Tool name should follow mcp__{server}__{tool} convention."""
    schemas = [{"name": "list_repos", "description": "List repos", "input_schema": {"type": "object", "properties": {}}}]
    tools = create_langchain_tools_from_schemas("github", schemas)
    assert tools[0].name == "mcp__github__list_repos"
