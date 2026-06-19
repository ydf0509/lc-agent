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

expectIncludes('import { ref, computed, nextTick }')
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

if (failures.length > 0) {
  console.error('Token 用量面板交互契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Token 用量面板交互契约测试通过')
