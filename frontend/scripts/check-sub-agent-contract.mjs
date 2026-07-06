import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const agentsStore = readFileSync(join(root, 'src/stores/agents.ts'), 'utf8')
const agentEditor = readFileSync(join(root, 'src/components/dialogs/AgentEditorDialog.vue'), 'utf8')

const failures = []

function expectIncludes(fileName, content, expected) {
  if (!content.includes(expected)) {
    failures.push(`${fileName} 缺少: ${expected}`)
  }
}

expectIncludes(
  'agents.ts',
  agentsStore,
  'allowed_sub_agents: string[] | null',
)
expectIncludes(
  'AgentEditorDialog.vue',
  agentEditor,
  "const subAgentMode = ref<'all' | 'none' | 'custom'>('none')",
)
expectIncludes(
  'AgentEditorDialog.vue',
  agentEditor,
  'subAgentMode.value = \'none\'',
)
expectIncludes(
  'AgentEditorDialog.vue',
  agentEditor,
  'const allowed_sub_agents =',
)
expectIncludes(
  'AgentEditorDialog.vue',
  agentEditor,
  'allowed_sub_agents,',
)

if (failures.length > 0) {
  console.error('子Agent Agent 配置契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('子Agent Agent 配置契约测试通过')
