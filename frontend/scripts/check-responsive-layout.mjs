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
expectIncludes('App.vue', files.app, ":class=\"{ 'is-mobile-open': mobileLeftOpen }\"")
expectIncludes('App.vue', files.app, ":class=\"{ 'is-mobile-open': mobileRightOpen }\"")
expectMatch('App.vue', files.app, /@media\s*\(max-width:\s*900px\)/, '缺少 900px 移动端布局断点')
expectMatch('App.vue', files.app, /function openMobileLeft\(\)[\s\S]*mobileLeftOpen\.value = !mobileLeftOpen\.value[\s\S]*mobileRightOpen\.value = false/, '移动端左侧抽屉按钮应支持再次点击收起，并关闭右侧抽屉')
expectMatch('App.vue', files.app, /function openMobileRight\(\)[\s\S]*mobileRightOpen\.value = !mobileRightOpen\.value[\s\S]*mobileLeftOpen\.value = false/, '移动端右侧抽屉按钮应支持再次点击收起，并关闭左侧抽屉')
expectMatch('App.vue', files.app, /\.app-container\s*\{[\s\S]*position:\s*fixed[\s\S]*inset:\s*0[\s\S]*height:\s*100dvh/, '应用根容器应固定到移动视口，防止整页滚动导致顶部或输入框消失')
expectMatch('App.vue', files.app, /\.app-body\s*\{[\s\S]*min-height:\s*0/, '主布局应允许内部区域收缩滚动，避免撑开整页')
expectMatch('App.vue', files.app, /\.chat-main\s*\{[\s\S]*min-height:\s*0/, '聊天主区域应允许内部消息区滚动，避免撑开整页')
expectMatch('App.vue', files.app, /\.mobile-left-panel\.is-mobile-open,[\s\S]*\.mobile-right-panel\.is-mobile-open[\s\S]*transform:\s*translateX\(0\)/, '移动端抽屉打开状态应直接绑定到面板自身，避免祖先选择器层叠失效')

expectIncludes('AppHeader.vue', files.header, 'openMobileSidebar')
expectIncludes('AppHeader.vue', files.header, 'openMobileTools')
expectIncludes('AppHeader.vue', files.header, 'aria-label="打开会话列表"')
expectIncludes('AppHeader.vue', files.header, 'aria-label="打开工具和状态面板"')
expectIncludes('AppHeader.vue', files.header, 'mobile-sidebar-btn')
expectIncludes('AppHeader.vue', files.header, 'mobile-tools-btn')
expectIncludes('AppHeader.vue', files.header, 'agent-select')
expectMatch('AppHeader.vue', files.header, /@media\s*\(max-width:\s*900px\)/, '缺少顶部栏移动端断点')
expectMatch('AppHeader.vue', files.header, /\.app-header\s*\{[\s\S]*flex-shrink:\s*0/, '顶部栏应固定占位，不能被主内容滚动挤出')

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
expectMatch('ChatInput.vue', files.chatInput, /\.chat-input-wrapper\s*\{[\s\S]*position:\s*relative[\s\S]*z-index:\s*120/, '底部输入框应固定在布局底层之上，不能被滚动内容覆盖或挤出')

if (failures.length > 0) {
  console.error('响应式布局契约测试失败:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('响应式布局契约测试通过')
