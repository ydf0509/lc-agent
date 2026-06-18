$ErrorActionPreference = "Stop"

$python = "D:\ProgramData\Miniconda3\envs\py312\python.exe"
$script = Join-Path $PSScriptRoot "run_reasoning_probe.py"

& $python $script --report (Join-Path $PSScriptRoot "reasoning_probe_report.json")
