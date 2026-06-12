---
name: restart-bfzs
description: >-
  Rebuild lc-agent frontend and restart the bfzs Python server.
  Use when the user asks to restart, rebuild, or redeploy the bfzs application,
  or after making significant code changes to the framework or frontend.
---

# Restart bfzs Server

After significant code changes, rebuild the frontend and restart the bfzs server.

## Steps

### 1. Build frontend

```bash
npm run build
# working_directory: D:\codes\lc-agent\frontend
# Expected output: "✓ built in Xms"
```

### 2. Stop existing server

```powershell
$pids = (Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique | Where-Object { $_ -ne 0 }
if ($pids) { $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
Start-Sleep 2
```

### 3. Start bfzs server

```bash
D:\ProgramData\miniconda3\envs\py312\python.exe -m bfzs.main --port 8001
# working_directory: D:\codes\lc-agent-bfzs
# Background this command (block_until_ms: 15000)
```

### 4. Verify startup

Confirm output contains `Uvicorn running on http://127.0.0.1:8001`.

## Notes

- Python interpreter: `D:\ProgramData\miniconda3\envs\py312\python.exe`
- Frontend build output: `D:\codes\lc-agent\lc_agent\web\dist\`
- Default port: 8001 (configurable via `--port`)
- If port is different, adjust the `LocalPort` value in step 2
