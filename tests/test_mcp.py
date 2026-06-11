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
