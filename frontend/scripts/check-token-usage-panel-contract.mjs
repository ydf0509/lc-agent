import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const panel = readFileSync(join(root, 'src/components/chat/TokenUsagePanel.vue'), 'utf8')
const failures = []

function expectIncludes(expected) {
  if (!panel.includes(expected)) failures.push(`TokenUsagePanel.vue 缺少: ${expected}`)
}

function expectNotIncludes(unexpected) {
  if (panel.includes(unexpected)) failures.push(`TokenUsagePanel.vue 不应包含: ${unexpected}`)
}

function expectMatch(pattern, message) {
  if (!pattern.test(panel)) failures.push(`TokenUsagePanel.vue ${message}`)
}

expectIncludes('import { ref, computed, nextTick, watch }')
expectIncludes('const usageDetailsRef = ref<HTMLElement>()')
expectIncludes('const toolsDetailsRef = ref<HTMLElement>()')
expectIncludes('function scrollDetailsIntoView')
expectIncludes('scrollIntoView({ behavior: \'smooth\', block: \'nearest\' })')
expectIncludes('function toggleRoundsDetails()')
expectIncludes('function toggleToolsDetails()')
expectIncludes('@click.stop="toggleRoundsDetails"')
expectIncludes('@click.stop="toggleToolsDetails"')
expectIncludes('<Transition name="usage-details"')
expectMatch(/ref="usageDetailsRef"[\s\S]*class="usage-details"/, 'rounds 详情块应绑定滚动目标 ref')
expectMatch(/ref="toolsDetailsRef"[\s\S]*class="tools-details"/, '工具详情块应绑定滚动目标 ref')
expectMatch(/\.usage-details-enter-active,[\s\S]*\.usage-details-leave-active[\s\S]*transition:/, '展开详情应有进入和离开动画')
expectMatch(/\.usage-details\s*\{[\s\S]*scroll-margin:\s*72px 0 96px/, 'rounds 详情滚动定位应避开顶部栏和底部输入框')
expectMatch(/\.tools-details\s*\{[\s\S]*scroll-margin:\s*72px 0 96px/, '工具详情滚动定位应避开顶部栏和底部输入框')
expectNotIncludes('@click.stop="toolsExpanded = !toolsExpanded"')
expectNotIncludes('@click.stop="expanded = !expanded"')

// 平均 TPS：纯前端按「首个 token -> llm_usage」估算，不入库。
// 徽章显示在输入框右侧；面板里只保留 per-round 详情表的 TPS 列和 Sum 行。
const chatStore = readFileSync(join(root, 'src/stores/chat.ts'), 'utf8')
const sessionState = readFileSync(join(root, 'src/stores/chat-session-state.ts'), 'utf8')
const chatInput = readFileSync(join(root, 'src/components/chat/ChatInput.vue'), 'utf8')

function expectFileIncludes(content, fileName, expected) {
  if (!content.includes(expected)) failures.push(`${fileName} 缺少: ${expected}`)
}

expectIncludes('const avgTps = computed(')
expectIncludes('const hasRoundTps = computed(')
expectIncludes('round.tps')
expectNotIncludes('badge-speed')
expectNotIncludes('⚡')

expectFileIncludes(chatInput, 'ChatInput.vue', 'const lastTurnTps = computed(')
expectFileIncludes(chatInput, 'ChatInput.vue', 'tps-badge')
expectFileIncludes(chatInput, 'ChatInput.vue', 'tok/s')
expectFileIncludes(chatInput, 'ChatInput.vue', '模型生成耗时')

expectFileIncludes(sessionState, 'chat-session-state.ts', 'currentRoundFirstTokenAt: number')
expectFileIncludes(sessionState, 'chat-session-state.ts', 'subagentFirstTokenAt: Map<string, number>')

expectFileIncludes(chatStore, 'chat.ts', 'currentRoundFirstTokenAt')
expectFileIncludes(chatStore, 'chat.ts', 'subagentFirstTokenAt')
expectFileIncludes(chatStore, 'chat.ts', '_markMainFirstToken')
expectFileIncludes(chatStore, 'chat.ts', '_markSubagentFirstToken')
expectFileIncludes(chatStore, 'chat.ts', 'genMs')
expectFileIncludes(chatStore, 'chat.ts', 'tps:')

if (failures.length > 0) {
  console.error('Token 用量面板交互契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Token 用量面板交互契约测试通过')
