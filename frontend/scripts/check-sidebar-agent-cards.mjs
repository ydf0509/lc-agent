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

expectIncludes('SIDEBAR_COLLAPSED_GROUPS_KEY')
expectIncludes('lc-agent:sidebar:collapsed-agent-groups')
expectIncludes('loadCollapsedGroups')
expectIncludes('persistCollapsedGroups')
expectIncludes('class="agent-group-header"')
expectIncludes('class="agent-card-shell"')
expectIncludes('class="agent-card-count"')
expectIncludes("'is-active-agent': group.title === activeAgentName")
expectMatch(
  /\.session-list\s+:deep\(\.elx-conversations__group\)[\s\S]*border:\s*1px solid var\(--sidebar-agent-card-border\)/,
  'Agent 分组缺少卡片边框',
)
expectMatch(
  /\.session-list\s+:deep\(\.elx-conversations__group:has\(\.agent-group-header\.is-active-agent\)\)[\s\S]*border-color:\s*var\(--sidebar-agent-card-active-border\)/,
  '当前 Agent 卡片缺少高亮边框',
)
expectMatch(/\.left-sidebar[\s\S]*--sidebar-agent-card-bg:/, '缺少侧栏卡片主题变量')
expectMatch(/html\.dark[\s\S]*--sidebar-agent-card-bg:/, '缺少黑色主题侧栏卡片变量')
expectMatch(
  /@media\s*\(max-width:\s*900px\)[\s\S]*\.session-list\s+:deep\(\.elx-conversations__group\)[\s\S]*margin:/,
  '移动端 Agent 卡片没有收紧间距',
)
expectMatch(
  /\.session-list\s+:deep\(\.elx-conversations-item__label\)[\s\S]*text-overflow:\s*ellipsis/,
  '会话标题缺少省略策略',
)
expectMatch(
  /\.left-sidebar[\s\S]*--sidebar-session-hover-bg:\s*color-mix\(in srgb, var\(--el-color-success\)/,
  '会话 hover 背景应使用绿色高亮',
)
expectMatch(
  /html\.dark[\s\S]*--sidebar-session-hover-bg:\s*color-mix\(in srgb, var\(--el-color-success\)/,
  '黑色主题会话 hover 背景应使用绿色高亮',
)
expectMatch(
  /\.session-list\s+:deep\(\.elx-conversations-item:hover\)[\s\S]*background:\s*var\(--sidebar-session-hover-bg\)[\s\S]*color:\s*var\(--sidebar-session-hover-color\)/,
  '会话 hover 状态没有同时覆盖背景和文字颜色',
)
expectMatch(
  /\.session-list\s+:deep\(\.elx-conversations-item:hover \.elx-conversations-item__label\)[\s\S]*color:\s*var\(--sidebar-session-hover-color\)/,
  '会话 hover 状态没有覆盖标题文字颜色',
)

if (failures.length > 0) {
  console.error('Agent 会话侧栏契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Agent 会话侧栏契约测试通过')
