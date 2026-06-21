---
name: restart-bfzs
description: >-
  Rebuild lc-agent frontend and restart the bfzs Python server.
  Use when the user asks to restart, rebuild, or redeploy the bfzs application,
  or after making significant code changes to the framework or frontend.
---

# Restart bfzs Server

Run the unified restart script to build frontend and start the server.

## Quick Start

### 禁止无脑重启python服务
如果只修改了前端代码，不要无脑重启python服务。只需要npm run build编译前端。
```powershell
cd /d/codes/lc-agent/frontend && npm run build
```

```powershell
powershell -ExecutionPolicy Bypass -File "D:\codes\lc-agent\.agents\skills\restart-bfzs\scripts\restart.ps1"
# working_directory: D:\codes\lc-agent
# block_until_ms: 0 (background — server is long-running)
```

## Verify Startup

After backgrounding, poll the terminal output until you see:
- `Uvicorn running on http://127.0.0.1:8001` — server ready
- `[MCP] Connected:` — MCP integrations online

## Script Details

The script (`scripts/restart.ps1`) performs three steps:
1. **Build frontend** — `npm run build` in `D:\codes\lc-agent\frontend`
2. **Stop existing server** — kills any process on port 8001
3. **Start bfzs server** — runs `python -u -m bfzs.main --port 8001`

### Parameters

| Param   | Default     | Description        |
|---------|-------------|--------------------|
| -Port   | 8001        | Server listen port |
| -Host_  | 127.0.0.1   | Server bind address|

## Notes

- Python interpreter: `D:\ProgramData\miniconda3\envs\py312\python.exe`
- Frontend build output: `D:\codes\lc-agent\lc_agent\web\dist\`
- Working directory for bfzs: `D:\codes\lc-agent-bfzs`
- The script sets `PYTHONUNBUFFERED=1` for immediate log output
