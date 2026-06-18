import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const repoRoot = dirname(root)
const script = readFileSync(join(repoRoot, '.agents/skills/restart-bfzs/scripts/restart.ps1'), 'utf8')

const failures = []

function expectIncludes(expected) {
  if (!script.includes(expected)) failures.push(`restart.ps1 缺少: ${expected}`)
}

function expectMatch(pattern, message) {
  if (!pattern.test(script)) failures.push(`restart.ps1 ${message}`)
}

expectIncludes('Get-PortProcessIds')
expectIncludes('& $Netstat -ano')
expectIncludes('$RunLogDir')
expectIncludes('bfzs-restart-')
expectIncludes('Start-Process')
expectIncludes('-RedirectStandardOutput')
expectIncludes('-RedirectStandardError')
expectIncludes('-PassThru')
expectIncludes('".tmp"')
expectIncludes('"bfzs-runlogs"')
expectIncludes("$processPath = [System.Environment]::GetEnvironmentVariable('Path', 'Process')")
expectIncludes("SetEnvironmentVariable('Path', $null, 'Process')")
expectIncludes("SetEnvironmentVariable('PATH', $processPath, 'Process')")
expectIncludes('$Netstat = Join-Path $env:SystemRoot "System32\\netstat.exe"')
expectMatch(
  /while\s*\(\(Get-Date\)\s*-lt\s*\$deadline\)[\s\S]*Get-PortProcessIds -TargetPort \$Port/,
  '后台启动后应轮询端口确认服务已监听',
)
expectMatch(
  /\$proc\.HasExited[\s\S]*throw "bfzs server exited before listening/,
  '后台进程提前退出时应失败并提示日志',
)

if (failures.length > 0) {
  console.error('bfzs 重启脚本契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('bfzs 重启脚本契约测试通过')
