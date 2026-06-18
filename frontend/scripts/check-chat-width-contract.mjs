import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const chatView = readFileSync(join(root, 'src/views/ChatView.vue'), 'utf8')

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

expectIncludes('--chat-assistant-bubble-width')
expectIncludes('--chat-user-bubble-max-width')
expectIncludes('.elx-bubble--start')
expectIncludes('.elx-bubble--end')
expectIncludes('width: var(--chat-assistant-bubble-width)')
expectIncludes('width: fit-content')
expectIncludes('.elx-bubble--start .elx-bubble__content-wrapper')
expectIncludes('.elx-bubble--start .elx-bubble__content')
expectMatch(/\.elx-bubble--start[\s\S]*align-self:\s*flex-start/, 'assistant 气泡缺少左侧稳定对齐')
expectMatch(/\.elx-bubble--end[\s\S]*align-self:\s*flex-end/, 'user 气泡缺少右侧紧凑对齐')
expectMatch(/@media\s*\(max-width:\s*900px\)[\s\S]*--chat-assistant-bubble-width:\s*100%/, '移动端 assistant 气泡应占满可用宽度')

if (failures.length > 0) {
  console.error('聊天气泡宽度契约测试失败:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('聊天气泡宽度契约测试通过')
