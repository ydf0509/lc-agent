<#
.SYNOPSIS
    Build frontend and restart bfzs server on port 8001.
.DESCRIPTION
    1. Builds the Vue frontend via npm
    2. Kills any process occupying port 8001
    3. Starts bfzs server in background with unbuffered output
#>

param(
    [int]$Port = 8001,
    [string]$Host_ = "0.0.0.0",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$RepoDir = "D:\codes\lc-agent"
$FrontendDir = "D:\codes\lc-agent\frontend"
$BfzsDir = "D:\codes\lc-agent-bfzs"
$Python = "D:\ProgramData\miniconda3\envs\py312\python.exe"
$Netstat = Join-Path $env:SystemRoot "System32\netstat.exe"

Write-Host "`n=== [1/3] Stopping existing server on port $Port (free RAM before build) ===" -ForegroundColor Cyan
function Get-PortProcessIds {
    param([int]$TargetPort)

    $ids = @()
    try {
        $tcpConnections = Get-NetTCPConnection -LocalPort $TargetPort -ErrorAction SilentlyContinue
        foreach ($conn in $tcpConnections) {
            # TIME_WAIT 状态的连接进程已死，端口未真正释放，跳过
            if ($conn.State -eq 'TimeWait') { continue }
            $owningPid = $conn.OwningProcess
            # 进程已死但 socket 还未从内核释放（Force-Kill 后短暂残留），跳过
            if ($owningPid -ne 0 -and (Get-Process -Id $owningPid -ErrorAction SilentlyContinue)) {
                $ids += $owningPid
            }
        }
    } catch {
        Write-Host "  Get-NetTCPConnection failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    # netstat 只是 Get-NetTCPConnection 的兜底；受限环境（如沙箱）里 netstat.exe
    # 可能根本起不来，这里必须容错，不能让它把整个重启流程带崩。
    try {
        $netstatLines = & $Netstat -ano 2>$null | Select-String ":$TargetPort"
        foreach ($line in $netstatLines) {
            $parts = ($line.ToString().Trim() -split "\s+")
            if ($parts.Length -ge 5 -and $parts[1] -match ":$TargetPort$") {
                $foundPid = [int]$parts[-1]
                # 只保留进程实际存活的 PID
                if ($foundPid -ne 0 -and (Get-Process -Id $foundPid -ErrorAction SilentlyContinue)) {
                    $ids += $foundPid
                }
            }
        }
    } catch {
        Write-Host "  netstat fallback unavailable: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    $ids | Sort-Object -Unique | Where-Object { $_ -ne 0 }
}

$pids = Get-PortProcessIds -TargetPort $Port
if ($pids) {
    # Phase 1: graceful shutdown (no -Force), lets uvicorn flush DB / WAL
    $pids | ForEach-Object {
        Write-Host "  Sending graceful stop to PID $_"
        Stop-Process -Id $_ -ErrorAction SilentlyContinue
    }
    $graceDeadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $graceDeadline) {
        $alive = $pids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }
        if (-not $alive) { break }
        Start-Sleep 1
    }

    # Phase 2: force-kill anything still alive
    $stubborn = $pids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }
    if ($stubborn) {
        $stubborn | ForEach-Object {
            Write-Host "  Force-killing PID $_" -ForegroundColor Yellow
            # 用 taskkill /T 连子进程（uvicorn worker）一起带走；受限环境里可能不可用，容错
            try {
                & taskkill /F /T /PID $_ 2>$null | Out-Null
            } catch {
                Write-Host "  taskkill unavailable: $($_.Exception.Message)" -ForegroundColor Yellow
            }
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep 6
    }

    $remaining = Get-PortProcessIds -TargetPort $Port
    if ($remaining) {
        throw "Port $Port is still occupied by PID(s): $($remaining -join ', ')"
    }
    Write-Host "  Old server stopped" -ForegroundColor Green
} else {
    Write-Host "  No existing server found" -ForegroundColor Yellow
}

if ($SkipBuild) {
    Write-Host "`n=== [2/3] Skipping frontend build (SkipBuild flag set) ===" -ForegroundColor Yellow
} else {
    Write-Host "`n=== [2/3] Building frontend ===" -ForegroundColor Cyan
    Push-Location $FrontendDir
    try {
        # Skip vue-tsc type checking (IDE handles it); run vite build only to avoid Zone OOM.
        # 不通过 npx/npm：那些是 cmd.exe 包装脚本，受限环境（沙箱）里起不来；
        # 直接用 node 跑 vite 的入口文件，路径稳、不依赖 PATH。
        $env:NODE_OPTIONS = "--max-old-space-size=3072"
        # 依次找：PATH 里的 node → WorkBuddy 托管的多版本 node → 系统安装目录
        $nodeCandidates = @()
        $nodeCmd = Get-Command node -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($nodeCmd) { $nodeCandidates += $nodeCmd.Source }
        $nodeCandidates += (Get-ChildItem "$env:USERPROFILE\.workbuddy\binaries\node\versions\*\node.exe" -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending | ForEach-Object { $_.FullName })
        $nodeCandidates += "D:\Program Files\nodejs\node.exe"
        foreach ($pf in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
            if ($pf) { $nodeCandidates += (Join-Path $pf "nodejs\node.exe") }
        }
        $NodeExe = $nodeCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
        if (-not $NodeExe) { throw "node.exe not found; add node to PATH or edit the candidate paths in this script" }
        $ViteJs = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"
        if (-not (Test-Path $ViteJs)) { throw "vite entry not found: $ViteJs" }
        & $NodeExe $ViteJs build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
        Write-Host "Frontend build OK" -ForegroundColor Green
    } finally {
        $env:NODE_OPTIONS = ""
        Pop-Location
    }
}

Write-Host "`n=== [3/3] Starting bfzs server ===" -ForegroundColor Cyan
$RunLogDir = Join-Path (Join-Path $RepoDir ".tmp") "bfzs-runlogs"
New-Item -ItemType Directory -Force -Path $RunLogDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$stdoutLog = Join-Path $RunLogDir "bfzs-restart-$timestamp.out.log"
$stderrLog = Join-Path $RunLogDir "bfzs-restart-$timestamp.err.log"

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoDir;$env:PYTHONPATH" } else { $RepoDir }

# Start-Process（PS 5.1）把进程环境塞进大小写不敏感的字典。原始环境块里若同时存在
# Path/PATH、http_proxy/HTTP_PROXY 这类同名不同大小写的条目，就直接抛
# "Item has already been added"。PATH 必须保留值（子进程要用），所以先归并 PATH，
# 其余冲突项在下面按报错名字就地删除后重试。
$processPath = [System.Environment]::GetEnvironmentVariable('Path', 'Process')
if (-not $processPath) {
    $processPath = [System.Environment]::GetEnvironmentVariable('PATH', 'Process')
}
[System.Environment]::SetEnvironmentVariable('Path', $null, 'Process')
[System.Environment]::SetEnvironmentVariable('PATH', $processPath, 'Process')

$arguments = @("-u", "-m", "bfzs.main", "--port", "$Port", "--host", $Host_)
$startArgs = @{
    FilePath               = $Python
    ArgumentList           = $arguments
    WorkingDirectory       = $BfzsDir
    WindowStyle            = 'Hidden'
    RedirectStandardOutput = $stdoutLog
    RedirectStandardError  = $stderrLog
    PassThru               = $true
}
$proc = $null
for ($attempt = 1; $attempt -le 12; $attempt++) {
    try {
        $proc = Start-Process @startArgs
        break
    } catch {
        $dupMatch = [regex]::Match($_.Exception.Message, "Key being added: '([^']+)'")
        if (-not $dupMatch.Success) { throw }
        $dupName = $dupMatch.Groups[1].Value
        Write-Host "  dropping duplicate env var on retry: $dupName" -ForegroundColor Yellow
        [System.Environment]::SetEnvironmentVariable($dupName, $null, 'Process')
    }
}
if (-not $proc) { throw "Start-Process failed: process env still has duplicate case-variant variables" }

Write-Host "  Started PID $($proc.Id)"
Write-Host "  stdout: $stdoutLog"
Write-Host "  stderr: $stderrLog"

$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    if (Get-PortProcessIds -TargetPort $Port) {
        $startedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host "  bfzs server is listening on http://$Host_`:$Port (started at $startedAt)" -ForegroundColor Green
        exit 0
    }

    $proc.Refresh()
    if ($proc.HasExited) {
        throw "bfzs server exited before listening on port $Port. Check logs: $stdoutLog ; $stderrLog"
    }

    Start-Sleep 2
}

throw "bfzs server did not listen on port $Port within 90s. Check logs: $stdoutLog ; $stderrLog"
