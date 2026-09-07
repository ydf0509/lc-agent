import asyncio

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


def test_mcp_manager_infers_http_type_when_url_present():
    manager = McpManager({"remote": {"url": "http://localhost:3000/mcp"}})
    server = manager.get_server("remote")
    assert server is not None
    assert server.type == "http"


@pytest.mark.asyncio
async def test_mcp_manager_connects_url_only_config_as_http(monkeypatch):
    manager = McpManager({"remote": {"url": "http://localhost:3000/mcp"}})
    calls = []

    async def fake_http(name, conf):
        calls.append((name, conf))
        manager._servers[name].status = "connected"

    async def fail_stdio(name, conf):
        raise AssertionError("url-only MCP config should not use stdio")

    monkeypatch.setattr(manager, "_connect_http_persistent", fake_http)
    monkeypatch.setattr(manager, "_connect_stdio_persistent", fail_stdio)

    await manager.connect_all()

    assert calls == [("remote", {"url": "http://localhost:3000/mcp"})]
    assert manager.get_server("remote").status == "connected"


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


@pytest.mark.asyncio
async def test_refresh_server_reconnects_and_replaces_tool_schemas(monkeypatch):
    manager = McpManager({"remote": {"type": "http", "url": "http://example.test/mcp"}})
    server = manager.get_server("remote")
    assert server is not None
    server.status = "connected"
    server.tools = ["old_tool"]
    server.tool_schemas = [{"name": "old_tool", "description": "old", "input_schema": {}}]
    manager._sessions["remote"] = object()
    calls = []

    async def fake_cleanup(name):
        calls.append(("cleanup", name))
        manager._sessions.pop(name, None)

    async def fake_connect(name, conf, **kwargs):
        calls.append(("connect", name, conf, server.tools, server.tool_schemas))
        manager._sessions[name] = object()
        server.status = "connected"
        server.tools = ["new_tool"]
        server.tool_schemas = [{"name": "new_tool", "description": "new", "input_schema": {"q": "string"}}]

    monkeypatch.setattr(manager, "_cleanup_server", fake_cleanup)
    monkeypatch.setattr(manager, "_connect_server", fake_connect)

    refreshed = await manager.refresh_server("remote")

    assert refreshed is server
    assert calls == [
        ("cleanup", "remote"),
        (
            "connect",
            "remote",
            {"type": "http", "url": "http://example.test/mcp"},
            ["old_tool"],
            [{"name": "old_tool", "description": "old", "input_schema": {}}],
        ),
    ]
    assert server.tools == ["new_tool"]
    assert server.tool_schemas[0]["description"] == "new"


@pytest.mark.asyncio
async def test_refresh_server_keeps_previous_schemas_until_reconnected(monkeypatch):
    state_changes = []
    manager = McpManager(
        {"remote": {"type": "http", "url": "http://example.test/mcp"}},
        on_state_change=lambda: state_changes.append("changed"),
    )
    server = manager.get_server("remote")
    assert server is not None
    server.status = "connected"
    server.tools = ["old_tool"]
    server.tool_schemas = [{"name": "old_tool", "description": "old", "input_schema": {}}]
    reconnect_started = asyncio.Event()
    finish_reconnect = asyncio.Event()

    async def fake_cleanup(name):
        manager._sessions.pop(name, None)

    async def fake_connect(name, conf, **kwargs):
        assert kwargs == {"notify_connecting": False}
        reconnect_started.set()
        await finish_reconnect.wait()
        manager._sessions[name] = object()
        manager._extract_tools(name, type("Result", (), {"tools": []})())

    monkeypatch.setattr(manager, "_cleanup_server", fake_cleanup)
    monkeypatch.setattr(manager, "_connect_server", fake_connect)

    refresh_task = asyncio.create_task(manager.refresh_server("remote"))
    await reconnect_started.wait()

    assert server.status == "connected"
    assert server.tools == ["old_tool"]
    assert server.tool_schemas[0]["description"] == "old"
    assert state_changes == []

    finish_reconnect.set()
    await refresh_task
    assert state_changes == ["changed"]


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

    async def fake_connect_server(name, conf, **kwargs):
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

    async def fake_connect_server(name, conf, **kwargs):
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

    async def fake_connect_server(name, conf, **kwargs):
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

    async def fake_connect_server(name, conf, **kwargs):
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
        # Key must be `mcpServers`: that is what LcAgentApp reads, and a
        # misspelled key silently registers zero servers (no callback fires).
        "mcpServers": {"http_test": {"type": "http", "url": "http://example.test/mcp"}},
    }
    app = LcAgentApp(config)
    gen_before = app.engine._mcp_generation

    app.mcp_manager._set_server_error("http_test", "connection dropped")

    assert app.engine._mcp_generation == gen_before + 1
