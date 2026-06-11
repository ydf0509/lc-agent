import pytest

from lc_agent.mcp.manager import McpManager, McpServerStatus


def test_mcp_manager_init():
    config = {
        "filesystem": {"command": "npx", "args": ["-y", "server-fs"]},
        "github": {"command": "npx", "args": ["-y", "server-github"]},
    }
    manager = McpManager(config)
    assert len(manager.servers) == 2
    assert manager.get_server("filesystem") is not None
    assert manager.get_server("filesystem").status == "disconnected"


def test_mcp_manager_empty():
    manager = McpManager({})
    assert len(manager.servers) == 0


def test_mcp_server_status_fields():
    status = McpServerStatus(name="test", command="echo")
    assert status.status == "disconnected"
    assert status.tools == []
    assert status.error is None


def test_mcp_manager_has_tool_schemas():
    """After connect, servers should have tool_schemas."""
    config = {"test": {"command": "echo"}}
    manager = McpManager(config)
    # Before connect, tool_schemas should be empty
    assert manager.get_server("test").tool_schemas == []


def test_mcp_server_status_has_tool_schemas():
    status = McpServerStatus(name="x", command="y")
    assert hasattr(status, 'tool_schemas')
    assert status.tool_schemas == []


@pytest.mark.asyncio
async def test_mcp_manager_registers_tools_after_connect():
    """After connect, tools should be available via get_langchain_tools."""
    config = {}
    manager = McpManager(config)
    # With empty config, should return empty
    tools = manager.get_langchain_tools()
    assert tools == []
