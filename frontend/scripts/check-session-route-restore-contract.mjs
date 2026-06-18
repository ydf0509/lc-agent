import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

const files = {
  app: read('src/App.vue'),
  appHeader: read('src/components/layout/AppHeader.vue'),
}

const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

function expectNotIncludes(name, content, unexpected) {
  if (content.includes(unexpected)) failures.push(`${name} 不应包含: ${unexpected}`)
}

function expectMatch(name, content, pattern, message) {
  if (!pattern.test(content)) failures.push(`${name} ${message}`)
}

expectIncludes('AppHeader.vue', files.appHeader, '@change="$emit(\'changeAgent\', $event)"')
expectIncludes('AppHeader.vue', files.appHeader, 'changeAgent: [id: string]')
expectNotIncludes('AppHeader.vue', files.appHeader, '@change="agentsStore.selectAgent"')

expectIncludes('App.vue', files.app, '@change-agent="handleAgentChange"')
expectIncludes('App.vue', files.app, 'async function handleAgentChange(agentId: string)')
expectMatch(
  'App.vue',
  files.app,
  /async function handleAgentChange\(agentId: string\)[\s\S]*sessionsStore\.createLocalSession\(agentId,\s*toolsStore\.currentModel\)/,
  '用户手动切换 Agent 的处理函数没有创建该 Agent 的本地新会话',
)
expectMatch(
  'App.vue',
  files.app,
  /const sessionId = route\.params\.sessionId as string[\s\S]*if \(sessionId\) \{[\s\S]*await restoreSession\(sessionId\)[\s\S]*return[\s\S]*\}/,
  '初始化时应优先按 URL sessionId 恢复会话，再处理 agent query',
)
expectNotIncludes('App.vue', files.app, 'skipAgentWatch')
expectNotIncludes('App.vue', files.app, "watch(() => agentsStore.currentAgentId")

if (failures.length > 0) {
  console.error('会话路由恢复契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('会话路由恢复契约测试通过')
