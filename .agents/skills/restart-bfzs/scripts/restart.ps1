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
    [string]$Host_ = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$FrontendDir = "D:\codes\lc-agent\frontend"
$BfzsDir = "D:\codes\lc-agent-bfzs"
$Python = "D:\ProgramData\miniconda3\envs\py312\python.exe"

Write-Host "`n=== [1/3] Building frontend ===" -ForegroundColor Cyan
Push-Location $FrontendDir
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
    Write-Host "Frontend build OK" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host "`n=== [2/3] Stopping existing server on port $Port ===" -ForegroundColor Cyan
$pids = (Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue).OwningProcess |
    Sort-Object -Unique | Where-Object { $_ -ne 0 }
if ($pids) {
    $pids | ForEach-Object {
        Write-Host "  Killing PID $_"
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep 2
    Write-Host "  Old server stopped" -ForegroundColor Green
} else {
    Write-Host "  No existing server found" -ForegroundColor Yellow
}

Write-Host "`n=== [3/3] Starting bfzs server ===" -ForegroundColor Cyan
$env:PYTHONUNBUFFERED = "1"
Push-Location $BfzsDir
try {
    & $Python -u -m bfzs.main --port $Port --host $Host_
} finally {
    Pop-Location
}
