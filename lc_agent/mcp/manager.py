from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpServerStatus:
    name: str
    command: str
    status: str = "disconnected"
    tools: list[str] = field(default_factory=list)
    error: str | None = None


class McpManager:
    """Manages MCP server connections and tool discovery."""

    def __init__(self, config: dict[str, dict]):
        self._config = config
        self._servers: dict[str, McpServerStatus] = {}

        for name, conf in config.items():
            self._servers[name] = McpServerStatus(
                name=name,
                command=conf.get("command", ""),
            )

    @property
    def servers(self) -> list[McpServerStatus]:
        return list(self._servers.values())

    def get_server(self, name: str) -> McpServerStatus | None:
        return self._servers.get(name)

    async def connect_all(self):
        """Attempt to connect to all configured MCP servers."""
        for name, conf in self._config.items():
            await self._connect_server(name, conf)

    async def _connect_server(self, name: str, conf: dict):
        """Connect to a single MCP server."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            env = {**os.environ, **conf.get("env", {})}
            params = StdioServerParameters(
                command=conf["command"],
                args=conf.get("args", []),
                env=env,
            )

            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools]
                    self._servers[name].status = "connected"
                    self._servers[name].tools = tool_names

        except Exception as e:
            self._servers[name].status = "error"
            self._servers[name].error = str(e)

    def get_tools_for_server(self, server_name: str) -> list[str]:
        """Get tool names for a given server."""
        server = self._servers.get(server_name)
        return server.tools if server else []
