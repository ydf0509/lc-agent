import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const read = (p) => readFileSync(join(root, p), 'utf8')

const chatView = read('src/views/ChatView.vue')
const router = read('src/components/chat/tools/ToolCardRouter.vue')
const toolRouter = read('src/components/chat/tools/toolCardRouter.ts')
const editCard = read('src/components/chat/tools/ToolFileEditCard.vue')
const writeCard = read('src/components/chat/tools/ToolFileWriteCard.vue')
const terminalCard = read('src/components/chat/tools/ToolTerminalCard.vue')
const genericCard = read('src/components/chat/tools/ToolGenericCard.vue')
const fileCard = read('src/components/chat/tools/ToolFileCard.vue')
const useToolCard = read('src/components/chat/tools/useToolCard.ts')
const chatStore = read('src/stores/chat.ts')

const failures = []

function expect(cond, message) {
  if (!cond) failures.push(message)
}

// ChatView 必须走路由，不再直引旧通用卡
expect(chatView.includes('ToolCardRouter'), 'ChatView.vue 缺少 ToolCardRouter 接线')
expect(!chatView.includes("from '@/components/chat/ToolCallCard.vue'"), 'ChatView.vue 仍在直引旧 ToolCallCard')
expect(chatView.includes('<ToolCardRouter'), 'ChatView.vue 缺少 <ToolCardRouter> 使用')

// 文件卡：复用 fileDiff / filePreview，标题说人话
expect(fileCard.includes('fileDiff'), 'ToolFileCard.vue 未使用 fileDiff')
expect(fileCard.includes('filePreview'), 'ToolFileCard.vue 未使用 filePreview')
expect(fileCard.includes('在抽屉里看'), 'ToolFileCard.vue 缺少抽屉入口')
// 编辑/写入文件卡不自动折叠：跑完也保持展开，用户手动才收
expect(fileCard.includes('keepExpanded: true'), 'ToolFileCard.vue 未传 keepExpanded（文件卡仍会自动折叠）')
expect(useToolCard.includes('keepExpanded'), 'useToolCard.ts 缺少 keepExpanded 支持')
expect(editCard.includes('variant="edit"'), 'ToolFileEditCard.vue 未透传 variant=edit')
expect(writeCard.includes('variant="write"'), 'ToolFileWriteCard.vue 未透传 variant=write')

// 终端卡：命令置顶 + 退出码 + PID 停止
expect(terminalCard.includes('commandText'), 'ToolTerminalCard.vue 缺少命令置顶行')
expect(terminalCard.includes('exit_code'), 'ToolTerminalCard.vue 未解析 exit_code')
expect(terminalCard.includes('killProcess'), 'ToolTerminalCard.vue 缺少停止进程')
expect(terminalCard.includes('/tools/process/'), 'ToolTerminalCard.vue 缺少后台输出轮询')

// 通用卡：标题说人话 + 折叠 + 图标徽标（不再用“工”字占位）
expect(genericCard.includes('friendlyTitle'), 'ToolGenericCard.vue 缺少人话标题')
expect(genericCard.includes('badgeIcon'), 'ToolGenericCard.vue 缺少图标徽标')
expect(!genericCard.includes('>工<'), 'ToolGenericCard.vue 仍有“工”字占位')
expect(toolRouter.includes('command__run_command'), 'toolCardRouter.ts 未覆盖 run_command')
expect(toolRouter.includes('edit_block'), 'toolCardRouter.ts 未覆盖 edit_block')
expect(toolRouter.includes('write_file'), 'toolCardRouter.ts 未覆盖 write_file')
expect(useToolCard.includes('liveElapsed'), 'useToolCard.ts 缺少运行计时')

// 结果大小 / token 徽章（旧 ToolCallCard 的 chars/tokens 展示，拆卡后必须保留）
expect(useToolCard.includes('resultSizeText'), 'useToolCard.ts 缺少结果大小徽章')
expect(useToolCard.includes('formatTokenCount'), 'useToolCard.ts 缺少 token 估算')
expect(genericCard.includes('resultSizeText'), 'ToolGenericCard.vue 缺少 chars/tokens 徽章')
expect(fileCard.includes('resultSizeText'), 'ToolFileCard.vue 缺少 chars/tokens 徽章')
expect(terminalCard.includes('resultSizeText'), 'ToolTerminalCard.vue 缺少 chars/tokens 徽章')

// 路由只做 P0 分发，其余走 generic
expect(router.includes("kind === 'edit'"), 'ToolCardRouter.vue 缺少 edit 分发')
expect(router.includes("kind === 'write'"), 'ToolCardRouter.vue 缺少 write 分发')
expect(router.includes("kind === 'terminal'"), 'ToolCardRouter.vue 缺少 terminal 分发')
expect(router.includes('GenericToolCard'), 'ToolCardRouter.vue 缺少通用兜底')

// 刷新后也要能看当时的 diff：后端随 tool_calls 入库，历史归一化必须保留字段
expect(chatStore.includes('fileDiff'), 'chat.ts 历史归一化未保留 fileDiff（刷新后看不到 diff）')
expect(chatStore.includes('filePreview'), 'chat.ts 历史归一化未保留 filePreview（刷新后看不到写入预览）')

// 展开区标签列：三张卡共用 ToolField，左侧统一「工具 → 目标 → 内容」栅格
// （通用卡 工具/入参/结果，文件卡 工具/文件/改动|内容，终端卡 工具/命令/输出）
const toolField = read('src/components/chat/tools/ToolField.vue')
expect(toolField.includes('tool-field-label'), 'ToolField.vue 缺少左侧标签列')
expect(toolField.includes('is-dark'), 'ToolField.vue 缺少深色 tone（终端卡要用）')
expect(genericCard.includes("from './ToolField.vue'"), 'ToolGenericCard.vue 未使用 ToolField')
expect(fileCard.includes("from './ToolField.vue'"), 'ToolFileCard.vue 未使用 ToolField')
expect(terminalCard.includes("from './ToolField.vue'"), 'ToolTerminalCard.vue 未使用 ToolField')

expect(genericCard.includes('label="工具"'), 'ToolGenericCard.vue 展开区缺少工具名行')
expect(fileCard.includes('label="工具"'), 'ToolFileCard.vue 展开区缺少工具名行')
expect(terminalCard.includes('label="工具"'), 'ToolTerminalCard.vue 展开区缺少工具名行')

// 标签文字按卡分别定名
expect(genericCard.includes('label="入参"'), 'ToolGenericCard.vue 缺少「入参」标签')
expect(genericCard.includes('label="结果"'), 'ToolGenericCard.vue 缺少「结果」标签')
expect(fileCard.includes('label="文件"'), 'ToolFileCard.vue 缺少「文件」标签')
expect(fileCard.includes('label="改动"'), 'ToolFileCard.vue 缺少「改动」标签')
expect(fileCard.includes('label="内容"'), 'ToolFileCard.vue 缺少「内容」标签')
expect(terminalCard.includes('label="命令"'), 'ToolTerminalCard.vue 缺少「命令」标签')
expect(terminalCard.includes('label="输出"'), 'ToolTerminalCard.vue 缺少「输出」标签')
expect(terminalCard.includes('tone="dark"'), 'ToolTerminalCard.vue 未给深色标签列传 tone=dark')

// 复制按钮多槽位：一张卡里工具名和命令各存各的状态
expect(useToolCard.includes('copyLabel'), 'useToolCard.ts 缺少 copyLabel')
expect(useToolCard.includes('copyStates'), 'useToolCard.ts 缺少多槽位复制状态')
expect(!/\bcopyState\b/.test(useToolCard), 'useToolCard.ts 仍在用单槽 copyState')

// 入参不再硬截断，改成块渲染 + 看全文
expect(genericCard.includes('ARG_INLINE_MAX'), 'ToolGenericCard.vue 缺少入参内联/块判断')
expect(genericCard.includes('看全文'), 'ToolGenericCard.vue 缺少入参看全文入口')
expect(!genericCard.includes('formatted.length > 200'), 'ToolGenericCard.vue 入参仍在硬截断')
expect(genericCard.includes('ModalTarget'), 'ToolGenericCard.vue 弹层目标未用带类型标识（入参名叫 result 会串台）')

// 预览页要能真折叠：样例自带 collapsed 开关，否则“折叠态露出错误”测不出来
const testSegments = read('src/views/TestSegments.vue')
expect(testSegments.includes('sample.collapsed'), 'TestSegments.vue 未按样例传折叠态')

// 折叠态也不能把错误藏起来
expect(terminalCard.includes('!isCollapsed || (errorText && !hasOutput)'), 'ToolTerminalCard.vue 折叠后藏了错误')
expect(fileCard.includes('!isCollapsed || errorText'), 'ToolFileCard.vue 折叠后藏了错误')
expect(genericCard.includes('!isCollapsed || errorText'), 'ToolGenericCard.vue 折叠后藏了错误')

if (failures.length > 0) {
  console.error('工具卡片契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('工具卡片契约测试通过')
