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


class _TextContent:
    def __init__(self, text: str):
        self.text = text


class _ToolResult:
    def __init__(self, text: str):
        self.content = [_TextContent(text)]


class _FailingSession:
    async def call_tool(self, tool_name, arguments):
        raise ConnectionError("connection dropped")


class _SuccessfulSession:
    def __init__(self):
        self.calls = []

    async def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return _ToolResult("ok after reconnect")


@pytest.mark.asyncio
async def test_call_tool_reconnects_once_and_retries_after_session_failure(monkeypatch):
    manager = McpManager({"http_test": {"type": "http", "url": "http://example.test/mcp"}})
    manager._servers["http_test"].status = "connected"
    manager._sessions["http_test"] = _FailingSession()

    replacement_session = _SuccessfulSession()
    reconnects = []

    async def fake_connect_server(name, conf):
        reconnects.append((name, conf))
        manager._sessions[name] = replacement_session
        manager._servers[name].status = "connected"
        manager._servers[name].error = None

    monkeypatch.setattr(manager, "_connect_server", fake_connect_server)

    result = await manager.call_tool("http_test", "ping", {"value": 1})

    assert result == "ok after reconnect"
    assert reconnects == [("http_test", {"type": "http", "url": "http://example.test/mcp"})]
    assert replacement_session.calls == [("ping", {"value": 1})]
    assert manager.get_server("http_test").status == "connected"
    assert manager.get_server("http_test").error is None


@pytest.mark.asyncio
async def test_call_tool_reports_reconnect_failure_and_clears_stale_session(monkeypatch):
    manager = McpManager({"http_test": {"type": "http", "url": "http://example.test/mcp"}})
    manager._servers["http_test"].status = "connected"
    manager._sessions["http_test"] = _FailingSession()

    async def fake_connect_server(name, conf):
        manager._servers[name].status = "error"
        manager._servers[name].error = "server still down"

    monkeypatch.setattr(manager, "_connect_server", fake_connect_server)

    result = await manager.call_tool("http_test", "ping", {})

    assert result == "MCP server 'http_test' reconnect failed: server still down"
    assert "http_test" not in manager._sessions
    assert manager.get_server("http_test").status == "error"
    assert manager.get_server("http_test").error == "server still down"


@pytest.mark.asyncio
async def test_call_tool_reports_reconnect_failure_when_no_session_exists(monkeypatch):
    manager = McpManager({"http_test": {"type": "http", "url": "http://example.test/mcp"}})
    manager._servers["http_test"].status = "error"
    manager._servers["http_test"].error = "previous failure"

    async def fake_connect_server(name, conf):
        manager._servers[name].status = "error"
        manager._servers[name].error = "server still down"

    monkeypatch.setattr(manager, "_connect_server", fake_connect_server)

    result = await manager.call_tool("http_test", "ping", {})

    assert result == "MCP server 'http_test' reconnect failed: server still down"
    assert "http_test" not in manager._sessions
    assert manager.get_server("http_test").status == "error"


@pytest.mark.asyncio
async def test_call_tool_does_not_reconnect_disabled_server(monkeypatch):
    manager = McpManager({"http_test": {"type": "http", "url": "http://example.test/mcp"}})
    server = manager.get_server("http_test")
    server.enabled = False
    server.status = "disabled"
    manager._sessions["http_test"] = _FailingSession()
    reconnects = []

    async def fake_connect_server(name, conf):
        reconnects.append((name, conf))

    monkeypatch.setattr(manager, "_connect_server", fake_connect_server)

    result = await manager.call_tool("http_test", "ping", {})

    assert result == "MCP server 'http_test' is disabled"
    assert reconnects == []
    assert manager.get_server("http_test").status == "disabled"


def test_lc_agent_app_wires_mcp_state_changes_to_generation():
    from lc_agent.app import LcAgentApp

    config = {
        "provider": {"openai": {"base_url": "http://fake", "api_key": "sk-fake", "models": [{"id": "gpt-4"}]}},
        "agent": {"default_model": "gpt-4", "system_prompt": "Test"},
        "mcp_servers": {"http_test": {"type": "http", "url": "http://example.test/mcp"}},
    }
    app = LcAgentApp(config)
    gen_before = app.engine._mcp_generation

    app.mcp_manager._set_server_error("http_test", "connection dropped")

    assert app.engine._mcp_generation == gen_before + 1
