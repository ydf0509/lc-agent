# Phase 4b: MCP Server Management + Skills Management

## Goal

Enable lc_agent to integrate MCP (Model Context Protocol) servers as tool sources, and discover SKILL.md files as injectable system prompt extensions. Both are configuration-driven with UI toggles.

## MCP Server Integration

### Configuration

```jsonc
{
  "mcp_servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "{env:GITHUB_TOKEN}"}
    }
  }
}
```

### Runtime Behavior

1. On startup, initialize MCP client connections for each configured server
2. MCP servers expose tools via the MCP protocol — these become LangChain-compatible tools
3. Tools from MCP servers are registered in ToolRegistry with group = `mcp__{server_name}`
4. Agent preset `allowed_mcp_servers: ["filesystem"]` controls which MCP tools are available
5. Three-value semantics: null = all, [] = none, ["name"] = specific

### API

- `GET /api/mcp` — list configured MCP servers with status (connected/error/disabled)
- MCP tools appear in existing `GET /api/tools` and `GET /api/tools/groups`

### Frontend

- Right Panel MCP section shows server list with connection status badge
- No toggle needed for Phase 4b (controlled by agent preset)

## Skills Management

### Configuration

```jsonc
{
  "skills": {
    "directory": "./skills"  // default
  }
}
```

### SKILL.md Format

```markdown
---
name: coding-assistant
description: Expert coding guidance with best practices
---

# Coding Assistant

You are an expert software developer. Follow these principles:
- Write clean, tested code
- Use SOLID principles
...
```

### Runtime Behavior

1. On startup, scan configured directory for `**/SKILL.md` files
2. Parse YAML frontmatter for `name` and `description`
3. Store discovered skills in a SkillRegistry
4. When building agent, inject enabled skills' content into system prompt
5. Three-value semantics via `allowed_skills` on AgentPreset

### API

- `GET /api/skills` — list discovered skills (name, description, enabled status)

### Frontend

- Right Panel Skills section shows skill list with name + description
- No toggle needed for Phase 4b (controlled by agent preset)

## Scope Exclusions

- No dynamic MCP server addition from UI (config-only)
- No skill creation from UI
- No MCP server restart/reconnect from UI
- No skill content editing from UI
