import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const read = (relativePath) => readFileSync(join(root, relativePath), 'utf8')

const openedFiles = read('src/stores/opened-files.ts')
const httpApi = read('src/api/http.ts')
const chatStore = read('src/stores/chat.ts')

const failures = []
const expect = (condition, message) => {
  if (!condition) failures.push(message)
}
const sliceBetween = (content, start, end) => {
  const startIndex = content.indexOf(start)
  const endIndex = content.indexOf(end)
  if (startIndex === -1 || endIndex === -1 || endIndex <= startIndex) return ''
  return content.slice(startIndex, endIndex)
}

// A. 跨项目绝对路径：read 不传 agent_id，stat 也必须支持不传并分组查询
expect(openedFiles.includes('function isAbsolutePath('), 'opened-files.ts 缺少 isAbsolutePath 辅助函数')
expect(openedFiles.includes('api.statFiles(undefined'), '绝对路径 stat 未走无 agent_id 分支')
expect(openedFiles.includes('function fetchStats('), 'opened-files.ts 缺少统一的 fetchStats 分组查询')
expect(
  httpApi.includes('statFiles: (agentId: string | undefined, paths: string[])'),
  'http.ts 的 statFiles 应允许 agentId 为 undefined',
)
expect(
  httpApi.includes("const query = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : ''"),
  'http.ts 的 statFiles 未按 agentId 是否为空拼 query，绝对路径无法绕过项目根校验',
)

// B. 轮询：权限/解析失败（info.error）不能当成「文件已删除」
const pollRegion = sliceBetween(openedFiles, 'async function pollOnce(', 'function startPolling(')
expect(pollRegion.length > 0, 'opened-files.ts 无法定位 pollOnce 区域')
expect(pollRegion.includes('if (info.error) continue'), '轮询未忽略 info.error，跨项目文件会每次轮询都重新置位')
const errorIndex = pollRegion.indexOf('if (info.error) continue')
const missingIndex = pollRegion.indexOf('if (!info.exists)')
expect(
  errorIndex !== -1 && missingIndex !== -1 && errorIndex < missingIndex,
  'info.error 的判断必须放在 !info.exists 之前',
)

// C. file_change 事件置位前先比对 mtime，内容已经最新时不要误报
const markRegion = sliceBetween(
  openedFiles,
  'async function markExternalChanged(',
  'function dismissExternalChanged(',
)
expect(markRegion.length > 0, 'markExternalChanged 未改为 async，或无法定位函数区域')
expect(markRegion.includes('sameMtime('), 'markExternalChanged 未比对 mtime')
const sameMtimeIndex = markRegion.indexOf('sameMtime(')
const flagIndex = markRegion.indexOf('c.externalChanged = true')
expect(
  sameMtimeIndex !== -1 && flagIndex !== -1 && sameMtimeIndex < flagIndex,
  'mtime 比对必须在置位 externalChanged 之前',
)

// 事件处理器显式忽略 Promise，避免未处理拒绝
expect(
  chatStore.includes('void useOpenedFilesStore().markExternalChanged(filePath)'),
  'chat.ts 未显式忽略 markExternalChanged 返回的 Promise',
)

if (failures.length > 0) {
  console.error('文件外部改动提示契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('文件外部改动提示契约测试通过')
