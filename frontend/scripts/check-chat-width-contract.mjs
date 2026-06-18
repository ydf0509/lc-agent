import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const chatView = readFileSync(join(root, 'src/views/ChatView.vue'), 'utf8')
const toolCallCard = readFileSync(join(root, 'src/components/chat/ToolCallCard.vue'), 'utf8')

const failures = []

function expectIncludes(expected) {
  if (!chatView.includes(expected)) {
    failures.push(`ChatView.vue 缺少: ${expected}`)
  }
}

function expectMatch(pattern, message) {
  if (!pattern.test(chatView)) {
    failures.push(`ChatView.vue ${message}`)
  }
}

function expectNotMatch(pattern, message) {
  if (pattern.test(chatView)) {
    failures.push(`ChatView.vue ${message}`)
  }
}

function expectToolIncludes(expected) {
  if (!toolCallCard.includes(expected)) {
    failures.push(`ToolCallCard.vue 缺少: ${expected}`)
  }
}

function expectToolMatch(pattern, message) {
  if (!pattern.test(toolCallCard)) {
    failures.push(`ToolCallCard.vue ${message}`)
  }
}

expectIncludes('--chat-assistant-bubble-width')
expectIncludes('--chat-user-bubble-max-width')
expectIncludes('.elx-bubble--start')
expectIncludes('.elx-bubble--end')
expectIncludes('width: var(--chat-assistant-bubble-width)')
expectNotMatch(/\.elx-bubble--end\)\s*\{\s*width:\s*fit-content/, '桌面端 user 消息行仍是 fit-content，不能整体贴右')
expectMatch(/\.elx-bubble--end[\s\S]*width:\s*100%\s*!important/, '桌面端 user 消息行应占满宽度，方便整体靠右')
expectMatch(/\.elx-bubble--end[\s\S]*justify-content:\s*flex-end/, '桌面端 user 消息缺少贴右对齐')
expectMatch(/\.elx-bubble--end \.elx-bubble__content-wrapper[\s\S]*width:\s*fit-content/, 'user 气泡内容仍应保持紧凑宽度')
expectIncludes('.elx-bubble--start .elx-bubble__content-wrapper')
expectIncludes('.elx-bubble--start .elx-bubble__content')
expectMatch(/\.elx-bubble--start[\s\S]*align-self:\s*flex-start/, 'assistant 气泡缺少左侧稳定对齐')
expectMatch(/\.elx-bubble--end[\s\S]*align-self:\s*flex-end/, 'user 气泡缺少右侧紧凑对齐')
expectMatch(/@media\s*\(max-width:\s*900px\)[\s\S]*--chat-assistant-bubble-width:\s*100%/, '移动端 assistant 气泡应占满可用宽度')
expectToolIncludes('flex-wrap: wrap')
expectToolMatch(/\.tool-name[\s\S]*min-width:\s*0/, '工具名缺少 min-width: 0，移动端会把长工具名压成竖排')
expectToolMatch(/\.tool-name[\s\S]*white-space:\s*nowrap/, '工具名缺少 nowrap，移动端会逐字换行')
expectToolMatch(/\.tool-name[\s\S]*text-overflow:\s*ellipsis/, '工具名缺少省略策略，移动端会撑破或竖排')
expectToolMatch(/@media\s*\(max-width:\s*520px\)[\s\S]*\.tool-name[\s\S]*flex-basis:\s*100%/, '移动端工具名应独占一行，避免被状态和统计信息挤窄')

if (failures.length > 0) {
  console.error('聊天气泡宽度契约测试失败:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('聊天气泡宽度契约测试通过')
