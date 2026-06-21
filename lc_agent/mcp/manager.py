from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class McpServerStatus:
    name: str
    type: str = "local"
    command: str = ""
    url: str = ""
    enabled: bool = True
    status: str = "disconnected"
    tools: list[str] = field(default_factory=list)
    tool_schemas: list[dict] = field(default_factory=list)
    error: str | None = None


class McpManager:
    """Manages persistent MCP server connections and tool invocation."""

    def __init__(self, config: dict[str, dict], on_state_change: Callable[[], None] | None = None):
        self._config = config
        self._on_state_change = on_state_change
        self._servers: dict[str, McpServerStatus] = {}
        self._sessions: dict[str, Any] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._server_contexts: dict[str, tuple[Any, Any]] = {}

        for name, conf in config.items():
            enabled = conf.get("enabled", True)
            server_type = conf.get("type", "local")
            command = conf.get("command", "")
            if isinstance(command, list):
                command = " ".join(command)
            self._servers[name] = McpServerStatus(
                name=name,
                type=server_type,
                command=command,
                url=conf.get("url", ""),
                enabled=enabled,
            )

    @property
    def servers(self) -> list[McpServerStatus]:
        return list(self._servers.values())

    def get_server(self, name: str) -> McpServerStatus | None:
        return self._servers.get(name)

    def _notify_state_change(self) -> None:
        """Notify the owner that MCP state changed without coupling to the engine."""
        if self._on_state_change is None:
            return
        try:
            self._on_state_change()
        except Exception:
            pass

    def _set_server_error(self, name: str, error: str) -> None:
        server = self._servers.get(name)
        if server is None:
            return
        server.status = "error"
        server.error = error
        self._notify_state_change()

    async def _cleanup_server(self, name: str) -> None:
        """Close and forget a single server's persistent connection."""
        self._sessions.pop(name, None)
        self._locks.pop(name, None)
        contexts = self._server_contexts.pop(name, None)
        if contexts is None:
            return

        cm, session_cm = contexts
        try:
            await session_cm.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            await cm.__aexit__(None, None, None)
        except Exception:
            pass

    async def _reconnect_server(self, name: str) -> bool:
        """Reconnect one enabled configured server after a persistent session fails."""
        server = self._servers.get(name)
        conf = self._config.get(name)
        if server is None or conf is None or not server.enabled:
            return False

        await self._cleanup_server(name)
        await self._connect_server(name, conf)
        return name in self._sessions and self._servers[name].status == "connected"

    async def connect_all(self):
        """Connect to all configured MCP servers (persistent)."""
        for name, conf in self._config.items():
            if not conf.get("enabled", True):
                self._servers[name].status = "disabled"
                continue
            await self._connect_server(name, conf)

    async def _connect_server(self, name: str, conf: dict):
        """Establish a persistent connection to a single MCP server."""
        server_type = conf.get("type", "local")
        self._servers[name].status = "connecting"

        try:
            if server_type == "sse":
                await self._connect_sse_persistent(name, conf)
            elif server_type == "http":
                await self._connect_http_persistent(name, conf)
            else:
                await self._connect_stdio_persistent(name, conf)
        except Exception as e:
            self._set_server_error(name, str(e))

    async def _connect_stdio_persistent(self, name: str, conf: dict):
        """Keep a stdio MCP server process alive."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        command_raw = conf.get("command", "")
        if isinstance(command_raw, list):
            cmd = command_raw[0]
            args = command_raw[1:]
        else:
            cmd = command_raw
            args = conf.get("args", [])

        env = {**os.environ, **conf.get("env", {})}
        params = StdioServerParameters(command=cmd, args=args, env=env)

        cm = stdio_client(params)
        transport = await cm.__aenter__()
        read, write = transport

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()
        await session.initialize()

        self._server_contexts[name] = (cm, session_cm)
        self._sessions[name] = session
        self._extract_tools(name, await session.list_tools())

    async def _connect_sse_persistent(self, name: str, conf: dict):
        """Keep an SSE MCP connection alive."""
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        url = conf.get("url", "")
        if not url:
            raise ValueError(f"SSE server '{name}' requires a 'url' field")

        cm = sse_client(url=url)
        transport = await cm.__aenter__()
        read, write = transport

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()
        await session.initialize()

        self._server_contexts[name] = (cm, session_cm)
        self._sessions[name] = session
        self._extract_tools(name, await session.list_tools())

    async def _connect_http_persistent(self, name: str, conf: dict):
        """Keep a StreamableHTTP MCP connection alive."""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        url = conf.get("url", "")
        if not url:
            raise ValueError(f"HTTP server '{name}' requires a 'url' field")

        cm = streamable_http_client(url=url)
        transport = await cm.__aenter__()
        read, write = transport[0], transport[1]

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()
        await session.initialize()

        self._server_contexts[name] = (cm, session_cm)
        self._sessions[name] = session
        self._extract_tools(name, await session.list_tools())

    def _extract_tools(self, name: str, tools_result):
        """Extract tool info from list_tools result."""
        tool_names = [t.name for t in tools_result.tools]
        tool_schemas = [
            {
                "name": t.name,
                "description": getattr(t, "description", "") or "",
                "input_schema": getattr(t, "inputSchema", {}) or {},
            }
            for t in tools_result.tools
        ]
        self._servers[name].status = "connected"
        self._servers[name].tools = tool_names
        self._servers[name].tool_schemas = tool_schemas
        self._servers[name].error = None
        self._locks[name] = asyncio.Lock()
        self._notify_state_change()

    async def _call_tool_once(self, server_name: str, tool_name: str, arguments: dict) -> str:
        session = self._sessions.get(server_name)
        if session is None:
            raise RuntimeError(f"MCP server '{server_name}' not connected")

        lock = self._locks.get(server_name)
        if lock:
            async with lock:
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=60.0,
                )
        else:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=60.0,
            )

        parts = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
            else:
                parts.append(str(content))
        return "\n".join(parts) if parts else "(empty result)"

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Invoke a tool on a connected MCP server, reconnecting once if needed."""
        server = self._servers.get(server_name)
        if server is not None and not server.enabled:
            await self._cleanup_server(server_name)
            server.status = "disabled"
            return f"MCP server '{server_name}' is disabled"

        if self._sessions.get(server_name) is None:
            if server is not None and server_name in self._config:
                if await self._reconnect_server(server_name):
                    try:
                        return await self._call_tool_once(server_name, tool_name, arguments)
                    except Exception as e:
                        self._set_server_error(server_name, str(e))
                        await self._cleanup_server(server_name)
                        return f"MCP tool error after reconnect: {e}"
                reconnect_error = server.error or f"MCP server '{server_name}' not connected"
                return f"MCP server '{server_name}' reconnect failed: {reconnect_error}"
            return f"MCP server '{server_name}' not connected"

        try:
            return await self._call_tool_once(server_name, tool_name, arguments)
        except asyncio.TimeoutError:
            initial_error = f"MCP tool '{tool_name}' timed out after 60s"
        except Exception as e:
            initial_error = f"MCP tool error: {e}"

        self._set_server_error(server_name, initial_error)
        if not await self._reconnect_server(server_name):
            server = self._servers.get(server_name)
            reconnect_error = server.error if server and server.error else initial_error
            return f"MCP server '{server_name}' reconnect failed: {reconnect_error}"

        try:
            return await self._call_tool_once(server_name, tool_name, arguments)
        except asyncio.TimeoutError:
            final_error = f"MCP tool '{tool_name}' timed out after reconnect"
        except Exception as e:
            final_error = f"MCP tool error after reconnect: {e}"

        self._set_server_error(server_name, final_error)
        await self._cleanup_server(server_name)
        return final_error

    def get_tools_for_server(self, server_name: str) -> list[str]:
        """Get tool names for a given server."""
        server = self._servers.get(server_name)
        return server.tools if server else []

    def get_langchain_tools(self) -> list:
        """Get all connected MCP tools as LangChain StructuredTools."""
        from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas

        all_tools = []
        for server in self._servers.values():
            if server.enabled and server.status == "connected" and server.tool_schemas:
                invoke_fn = self._make_invoke_fn(server.name)
                tools = create_langchain_tools_from_schemas(server.name, server.tool_schemas, invoke_fn)
                all_tools.extend(tools)
        return all_tools

    def get_filtered_langchain_tools(self, allowed_servers: list[str] | None) -> list:
        """Get MCP tools filtered by allowed servers (three-value semantics)."""
        from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas

        all_tools = []
        for server in self._servers.values():
            if not server.enabled or server.status != "connected" or not server.tool_schemas:
                continue
            if allowed_servers is not None and server.name not in allowed_servers:
                continue
            invoke_fn = self._make_invoke_fn(server.name)
            tools = create_langchain_tools_from_schemas(server.name, server.tool_schemas, invoke_fn)
            all_tools.extend(tools)
        return all_tools

    def _make_invoke_fn(self, server_name: str):
        """Create an async invoke function bound to a specific server."""
        async def invoke(tool_name: str, arguments: dict) -> str:
            return await self.call_tool(server_name, tool_name, arguments)
        return invoke

    async def shutdown(self):
        """Clean up all persistent connections."""
        for name in list(self._server_contexts):
            await self._cleanup_server(name)
