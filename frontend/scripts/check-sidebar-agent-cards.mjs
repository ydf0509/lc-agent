import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const leftSidebar = readFileSync(join(root, 'src/components/layout/LeftSidebar.vue'), 'utf8')

const failures = []

function expectIncludes(expected) {
  if (!leftSidebar.includes(expected)) {
    failures.push(`LeftSidebar.vue 缺少: ${expected}`)
  }
}

function expectMatch(pattern, message) {
  if (!pattern.test(leftSidebar)) {
    failures.push(`LeftSidebar.vue ${message}`)
  }
}

expectIncludes('searchQuery')
expectIncludes('visibleCountByAgent')
expectIncludes('sidebar-search-input')
expectIncludes('agent-section')
expectIncludes('agent-section-header')
expectIncludes('session-children')
expectIncludes('session-item')
expectIncludes('show-more-btn')
expectIncludes('每次显示更多 20 条')
expectIncludes('setPinned(')
expectIncludes('is_pinned')
expectMatch(/const DEFAULT_VISIBLE_COUNT = 5/, '缺少每组默认显示 5 条的常量')
expectMatch(/const LOAD_MORE_COUNT = 20/, '缺少每次追加 20 条的常量')
expectMatch(/searchQuery\.value\.trim\(\)/, '搜索逻辑缺少 trim 处理')
expectMatch(/\.session-children[\s\S]*padding-left:/, '聊天标题缺少明显缩进')
expectMatch(/\.agent-section-header[\s\S]*font-weight:\s*700/, 'agent 标题缺少更明显层级字重')
expectMatch(/v-if="group\.hiddenCount > 0"/, '显示更多按钮缺少隐藏数量判断')

if (failures.length > 0) {
  console.error('Agent 层级侧栏契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Agent 层级侧栏契约测试通过')
