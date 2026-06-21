import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const apiFile = readFileSync(join(root, 'src/api/http.ts'), 'utf8')
const sessionsStore = readFileSync(join(root, 'src/stores/sessions.ts'), 'utf8')

const failures = []

function expectIncludes(label, text, expected) {
  if (!text.includes(expected)) {
    failures.push(`${label} 缺少: ${expected}`)
  }
}

expectIncludes('http.ts', apiFile, 'is_pinned?: boolean')
expectIncludes('sessions.ts', sessionsStore, 'is_pinned: boolean')
expectIncludes('sessions.ts', sessionsStore, 'pinned_at: string | null')
expectIncludes('sessions.ts', sessionsStore, 'async function setPinned(id: string, isPinned: boolean)')
expectIncludes('sessions.ts', sessionsStore, "await api.updateSession(id, { is_pinned: isPinned })")

if (failures.length > 0) {
  console.error('Session pinning 前端契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Session pinning 前端契约测试通过')
