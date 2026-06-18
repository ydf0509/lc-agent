import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

const files = {
  app: read('src/App.vue'),
  header: read('src/components/layout/AppHeader.vue'),
  leftSidebar: read('src/components/layout/LeftSidebar.vue'),
  rightPanel: read('src/components/layout/RightPanel.vue'),
  chatView: read('src/views/ChatView.vue'),
  chatInput: read('src/components/chat/ChatInput.vue'),
}

const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) {
    failures.push(`${name} 缺少: ${expected}`)
  }
}

function expectMatch(name, content, pattern, message) {
  if (!pattern.test(content)) {
    failures.push(`${name} ${message}`)
  }
}

expectIncludes('App.vue', files.app, 'mobileLeftOpen')
expectIncludes('App.vue', files.app, 'mobileRightOpen')
expectIncludes('App.vue', files.app, 'mobile-drawer-backdrop')
expectIncludes('App.vue', files.app, '@open-mobile-sidebar')
expectIncludes('App.vue', files.app, '@open-mobile-tools')
expectIncludes('App.vue', files.app, 'mobile-left-panel')
expectIncludes('App.vue', files.app, 'mobile-right-panel')
expectMatch('App.vue', files.app, /@media\s*\(max-width:\s*900px\)/, '缺少 900px 移动端布局断点')

expectIncludes('AppHeader.vue', files.header, 'openMobileSidebar')
expectIncludes('AppHeader.vue', files.header, 'openMobileTools')
expectIncludes('AppHeader.vue', files.header, 'aria-label="打开会话列表"')
expectIncludes('AppHeader.vue', files.header, 'aria-label="打开工具和状态面板"')
expectIncludes('AppHeader.vue', files.header, 'mobile-sidebar-btn')
expectIncludes('AppHeader.vue', files.header, 'mobile-tools-btn')
expectIncludes('AppHeader.vue', files.header, 'agent-select')
expectMatch('AppHeader.vue', files.header, /@media\s*\(max-width:\s*900px\)/, '缺少顶部栏移动端断点')

expectMatch('LeftSidebar.vue', files.leftSidebar, /@media\s*\(max-width:\s*900px\)/, '缺少左侧栏移动端断点')
expectIncludes('LeftSidebar.vue', files.leftSidebar, 'min(86vw, 340px)')

expectMatch('RightPanel.vue', files.rightPanel, /@media\s*\(max-width:\s*900px\)/, '缺少右侧面板移动端断点')
expectIncludes('RightPanel.vue', files.rightPanel, 'min(90vw, 380px)')

expectMatch('ChatView.vue', files.chatView, /@media\s*\(max-width:\s*520px\)/, '缺少聊天区手机断点')
expectIncludes('ChatView.vue', files.chatView, 'overflow-x: auto')
expectIncludes('ChatView.vue', files.chatView, 'max-width: 100% !important')
expectIncludes('ChatView.vue', files.chatView, 'class="role-header-icon"')
expectMatch('ChatView.vue', files.chatView, /@media\s*\(max-width:\s*520px\)[\s\S]*padding:\s*6px 6px 8px 0/, '手机端聊天区左侧 padding 应压到 0，避免浪费横向空间')
expectMatch('ChatView.vue', files.chatView, /@media\s*\(max-width:\s*520px\)[\s\S]*\.elx-bubble--start \.elx-bubble__avatar[\s\S]*display:\s*none/, '手机端助手头像列应隐藏，避免左侧 gutter 浪费空间')
expectMatch('ChatView.vue', files.chatView, /@media\s*\(max-width:\s*520px\)[\s\S]*\.role-header-icon[\s\S]*display:\s*inline-flex/, '手机端助手身份图标应挪到标题行')
expectMatch('ChatView.vue', files.chatView, /@media\s*\(max-width:\s*520px\)[\s\S]*\.elx-bubble--end[\s\S]*width:\s*100%/, '手机端用户消息行应占满整行以便右对齐')
expectMatch('ChatView.vue', files.chatView, /@media\s*\(max-width:\s*520px\)[\s\S]*\.elx-bubble--end[\s\S]*justify-content:\s*flex-end/, '手机端用户消息应贴右侧对齐')

expectMatch('ChatInput.vue', files.chatInput, /@media\s*\(max-width:\s*520px\)/, '缺少输入框手机断点')
expectIncludes('ChatInput.vue', files.chatInput, 'width: 100%')

if (failures.length > 0) {
  console.error('响应式布局契约测试失败:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('响应式布局契约测试通过')
