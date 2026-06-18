import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

const files = {
  app: read('src/App.vue'),
  chatInput: read('src/components/chat/ChatInput.vue'),
  chatStore: read('src/stores/chat.ts'),
  appHeader: read('src/components/layout/AppHeader.vue'),
}

const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

function expectNotIncludes(name, content, unexpected) {
  if (content.includes(unexpected)) failures.push(`${name} 不应包含: ${unexpected}`)
}

expectNotIncludes('ChatInput.vue', files.chatInput, ':disabled="!isConnected"')
expectIncludes('ChatInput.vue', files.chatInput, ':disabled="isInputDisabled"')
expectIncludes('ChatInput.vue', files.chatInput, 'const isInputDisabled = computed(() => isStreaming.value)')

expectIncludes('App.vue', files.app, 'const sameRouteSession = route.params.sessionId === session.id')
expectIncludes('App.vue', files.app, 'if (sameRouteSession) {')
expectIncludes('App.vue', files.app, 'await restoreSession(session.id)')

expectIncludes('chat.ts', files.chatStore, "ws.value.on('disconnected'")
expectIncludes('chat.ts', files.chatStore, 'threadId.value = null')

expectIncludes('AppHeader.vue', files.appHeader, "connected ? '已连接' : '待连接'")
expectIncludes('AppHeader.vue', files.appHeader, "connected ? 'WebSocket 已连接' : '发送消息时自动连接'")

if (failures.length > 0) {
  console.error('聊天连接恢复契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('聊天连接恢复契约测试通过')
