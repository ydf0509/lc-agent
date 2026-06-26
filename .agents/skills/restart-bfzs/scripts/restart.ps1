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
    [string]$Host_ = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$RepoDir = "D:\codes\lc-agent"
$FrontendDir = "D:\codes\lc-agent\frontend"
$BfzsDir = "D:\codes\lc-agent-bfzs"
$Python = "D:\ProgramData\miniconda3\envs\py312\python.exe"
$Netstat = Join-Path $env:SystemRoot "System32\netstat.exe"

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
function Get-PortProcessIds {
    param([int]$TargetPort)

    $ids = @()
    try {
        $tcpConnections = Get-NetTCPConnection -LocalPort $TargetPort -ErrorAction SilentlyContinue
        foreach ($conn in $tcpConnections) {
            # TIME_WAIT 状态的连接进程已死，端口未真正释放，跳过
            if ($conn.State -ne 'TimeWait') {
                $ids += $conn.OwningProcess
            }
        }
    } catch {
        Write-Host "  Get-NetTCPConnection failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    $netstatLines = & $Netstat -ano | Select-String ":$TargetPort"
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

    $ids | Sort-Object -Unique | Where-Object { $_ -ne 0 }
}

$pids = Get-PortProcessIds -TargetPort $Port
if ($pids) {
    $pids | ForEach-Object {
        Write-Host "  Killing PID $_"
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep 10
    $remaining = Get-PortProcessIds -TargetPort $Port
    if ($remaining) {
        throw "Port $Port is still occupied by PID(s): $($remaining -join ', ')"
    }
    Write-Host "  Old server stopped" -ForegroundColor Green
} else {
    Write-Host "  No existing server found" -ForegroundColor Yellow
}

Write-Host "`n=== [3/3] Starting bfzs server ===" -ForegroundColor Cyan
$RunLogDir = Join-Path (Join-Path $RepoDir ".tmp") "bfzs-runlogs"
New-Item -ItemType Directory -Force -Path $RunLogDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$stdoutLog = Join-Path $RunLogDir "bfzs-restart-$timestamp.out.log"
$stderrLog = Join-Path $RunLogDir "bfzs-restart-$timestamp.err.log"

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoDir;$env:PYTHONPATH" } else { $RepoDir }
$processPath = [System.Environment]::GetEnvironmentVariable('Path', 'Process')
if (-not $processPath) {
    $processPath = [System.Environment]::GetEnvironmentVariable('PATH', 'Process')
}
[System.Environment]::SetEnvironmentVariable('Path', $null, 'Process')
[System.Environment]::SetEnvironmentVariable('PATH', $processPath, 'Process')
$arguments = @("-u", "-m", "bfzs.main", "--port", "$Port", "--host", $Host_)
$proc = Start-Process `
    -FilePath $Python `
    -ArgumentList $arguments `
    -WorkingDirectory $BfzsDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

Write-Host "  Started PID $($proc.Id)"
Write-Host "  stdout: $stdoutLog"
Write-Host "  stderr: $stderrLog"

$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    if (Get-PortProcessIds -TargetPort $Port) {
        Write-Host "  bfzs server is listening on http://$Host_`:$Port" -ForegroundColor Green
        exit 0
    }

    $proc.Refresh()
    if ($proc.HasExited) {
        throw "bfzs server exited before listening on port $Port. Check logs: $stdoutLog ; $stderrLog"
    }

    Start-Sleep 2
}

throw "bfzs server did not listen on port $Port within 90s. Check logs: $stdoutLog ; $stderrLog"
