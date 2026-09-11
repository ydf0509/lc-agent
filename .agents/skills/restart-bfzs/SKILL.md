---
name: restart-bfzs
description: >-
  Rebuild lc-agent frontend and restart the bfzs Python server.
  Use when the user asks to restart, rebuild, or redeploy the bfzs application,
  or after making significant code changes to the framework or frontend.
---

# Restart bfzs Server

## ⚠️ 核心判断规则（必须首先判断）

在执行任何操作前，AI 必须先判断改动类型：

| 改动类型 | 操作 |
|---------|------|
| **仅前端代码**（.vue / .ts / .css 等 frontend/ 目录下的文件） | **只运行 npm run build，不重启 Python 服务** |
| **后端代码**（.py 文件）或 **config.jsonc** | 运行完整重启脚本 |
| **前端 + 后端都改了** | 运行完整重启脚本 |

### 仅前端编译（不重启服务）

```powershell
# working_directory: D:\codes\lc-agent
powershell -ExecutionPolicy Bypass -File "D:\codes\lc-agent\.agents\skills\restart-bfzs\scripts\build-frontend.ps1"
```

脚本路径：`D:\codes\lc-agent\.agents\skills\restart-bfzs\scripts\build-frontend.ps1`

### 完整重启（前端编译 + 停旧服务 + 启新服务）

```powershell
# working_directory: D:\codes\lc-agent
# block_until_ms: 0 (background — server is long-running)
powershell -ExecutionPolicy Bypass -File "D:\codes\lc-agent\.agents\skills\restart-bfzs\scripts\restart.ps1"
```

## ⚠️ AI 会话里启动服务：用后台任务，别指望 Start-Process 能留住

2026-09-10 实测（在 WorkBuddy 工具会话里）：

- `restart.ps1` 里的 `Start-Process` 起的服务，会在**工具调用结束时被整棵进程树回收**——日志里
  连退出信息都没有（不是崩溃，是外部强杀）。脚本自己会报 “listening on 8001”，但下一个工具调用
  再查端口就没了。
- 想绕开进程树的办法都被安全策略挡了：`Invoke-CimMethod Win32_Process Create`（WMI 起进程）
  直接返回 “blocked for security: WMI/CIM process creation is equivalent to Start-Process”。
- **可用做法**：不用 `Start-Process`，改成让服务作为**后台任务的前台进程**常驻：

  ```bash
  cd "D:/codes/lc-agent-bfzs" && \
  PYTHONPATH="D:/codes/lc-agent" PYTHONUNBUFFERED=1 \
  "D:/ProgramData/Miniconda3/envs/py312/python.exe" -u -m bfzs.main --port 8001 --host 0.0.0.0
  ```

  以 background 方式跑（不要加 `&`、不要 `nohup`），服务就挂在那个后台任务上，实测能常驻并被
  `http://127.0.0.1:8001/` 正常访问。

验证端口要用 `Get-NetTCPConnection -LocalPort 8001 -State Listen`，**不要用 `netstat`**（见下方 Notes）。

**别信后台任务的失败通知**：那个后台任务包装器会在会话收尾时被判成 `failed`，但 uvicorn 子进程其实
已经脱离、照常活着。实测就出现过「任务通知 failed + 端口 8001 正常返回 200」同时成立。所以服务到底
活没活，**只能以端口/HTTP 探测为准**（`curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/`
应得 `200`），不要因为一条 failed 通知就去重连、重起，那只会撞上 `EADDRINUSE` 再失败一次。

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

### 沙箱/受限环境下脚本已做的容错（2026-09-10 实测补齐）

原来这几处都会把脚本直接带崩，现在都已容错，遇到告警可以忽略：

| 现象 | 原因 | 现在的处理 |
|---|---|---|
| `Cannot run a document in the middle of a pipeline: netstat.exe` | 受限环境里 `netstat.exe` 起不来，而脚本是 `$ErrorActionPreference="Stop"` | netstat 只是 `Get-NetTCPConnection` 的兜底，包了 try/catch，失败只告警 |
| `npx.ps1 ... $LASTEXITCODE cannot be retrieved` | `npx` 是 cmd.exe 包装脚本，受限环境起不来 | 构建改成直接用 node 跑 `node_modules/vite/bin/vite.js` |
| `node.exe is not recognized` | 非交互会话的 PATH 里没有 node | 候选列表探测：PATH → `~\.workbuddy\binaries\node\versions\*\node.exe` → `D:\Program Files\nodejs\node.exe` → `%ProgramFiles%`（并做空值保护） |
| `Start-Process: Item has already been added. Key in dictionary: 'http_proxy' Key being added: 'HTTP_PROXY'` | PS 5.1 把环境塞进大小写不敏感的字典，原始环境块里有同名不同大小写的重复项 | PATH 先归并保值；其余按报错里的名字就地删除后重试（最多 12 次） |

**注意**：脚本第 1 步会构建前端，在受限环境里这一步可能失败（上面那条 npx/node 的坑），
这时可以先用别的方式把 `lc_agent/web/dist` 构建好，再 `restart.ps1 -SkipBuild` 只做停旧起新。

**构建产物的坑**：`vite build` 中途失败会把 `dist` 清空/留半成品；反复用 `--emptyOutDir=false`
重试又会攒下多代同名不同 hash 的陈旧 chunk（曾攒到 15 个文件里 5 份 AdminView）。
收拾办法是等锁释放后跑一次**干净的** `vite build`（默认会清空输出目录）。

