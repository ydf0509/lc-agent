import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const read = (relativePath) => readFileSync(join(root, relativePath), 'utf8')

const chatStore = read('src/stores/chat.ts')
const websocket = read('src/api/websocket.ts')
const chatView = read('src/views/ChatView.vue')
const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

expectIncludes('chat.ts', chatStore, 'export interface HttpTrace')
expectIncludes('chat.ts', chatStore, 'httpTraces?: HttpTrace[]')
expectIncludes('chat.ts', chatStore, 'function normalizeHttpTrace')
expectIncludes('chat.ts', chatStore, 'function normalizeHttpTraces')
expectIncludes('chat.ts', chatStore, 'httpTraces: normalizeHttpTraces(msg.http_traces || msg.httpTraces)')
expectIncludes('chat.ts', chatStore, 'last.httpTraces = normalizeHttpTraces((msg as any).http_traces || (msg as any).httpTraces)')
expectIncludes('websocket.ts', websocket, 'http_traces?: any[]')

if (chatView.includes('buildRoundHttpTraceMap')) {
  failures.push('ChatView.vue 不应再包含 buildRoundHttpTraceMap（已改为 inline block）')
}

if (failures.length > 0) {
  console.error('聊天 HTTP 数据契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('聊天 HTTP 数据契约测试通过')
