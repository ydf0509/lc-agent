import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

const files = {
  uuid: read('src/utils/client-id.ts'),
  sessions: read('src/stores/sessions.ts'),
  chat: read('src/stores/chat.ts'),
}

const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

function expectNotMatch(name, content, pattern, message) {
  if (pattern.test(content)) failures.push(`${name} ${message}`)
}

expectIncludes('client-id.ts', files.uuid, 'export function createClientId()')
expectIncludes('client-id.ts', files.uuid, 'crypto.getRandomValues')
expectIncludes('client-id.ts', files.uuid, 'getRandomValues(bytes)')
expectNotMatch('client-id.ts', files.uuid, /crypto\.randomUUID/g, '不应使用受安全上下文限制的 crypto.randomUUID')
expectNotMatch('client-id.ts', files.uuid, /Math\.random/g, '不应使用弱随机数兜底生成会话 ID')

expectIncludes('sessions.ts', files.sessions, "import { createClientId } from '@/utils/client-id'")
expectIncludes('chat.ts', files.chat, "import { createClientId } from '@/utils/client-id'")
expectNotMatch('sessions.ts', files.sessions, /crypto\.randomUUID/g, '不应直接调用 crypto.randomUUID')
expectNotMatch('chat.ts', files.chat, /crypto\.randomUUID/g, '不应直接调用 crypto.randomUUID')

if (failures.length > 0) {
  console.error('客户端 ID 兼容性契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('客户端 ID 兼容性契约测试通过')
