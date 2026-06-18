import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

const files = {
  chatView: read('src/views/ChatView.vue'),
  toolCallCard: read('src/components/chat/ToolCallCard.vue'),
  chatStore: read('src/stores/chat.ts'),
  websocket: read('src/api/websocket.ts'),
  chatInput: read('src/components/chat/ChatInput.vue'),
}

const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

function expectMatch(name, content, pattern, message) {
  if (!pattern.test(content)) failures.push(`${name} ${message}`)
}

expectIncludes('ChatView.vue', files.chatView, '#avatar="{ item }"')
expectIncludes('ChatView.vue', files.chatView, '#header="{ item }"')
expectIncludes('ChatView.vue', files.chatView, 'class="role-avatar"')
expectIncludes('ChatView.vue', files.chatView, 'class="role-header is-ai"')
expectMatch('ChatView.vue', files.chatView, /v-else\s+class="role-header is-ai"/, '助手身份栏没有限制为仅助手消息展示')
expectIncludes('ChatView.vue', files.chatView, 'getAssistantLabel()')
expectIncludes('ChatView.vue', files.chatView, 'getModelLabel()')
expectIncludes('ChatView.vue', files.chatView, "type: 'thinking'")
expectIncludes('ChatView.vue', files.chatView, 'class="thinking-block"')
expectIncludes('ChatView.vue', files.chatView, 'class="thinking-unavailable"')
expectIncludes('ChatView.vue', files.chatView, 'shouldShowReasoningNotice(item)')
expectIncludes('ChatView.vue', files.chatView, 'getReasoningTokenTotal')
expectIncludes('ChatView.vue', files.chatView, '没有返回可展示的思考文字')
expectIncludes('ChatView.vue', files.chatView, '<summary class="thinking-summary"')
expectIncludes('ChatView.vue', files.chatView, 'hasStructuredSegments')
expectIncludes('ChatView.vue', files.chatView, 'open')
expectMatch('ChatView.vue', files.chatView, /marker === '<!--THINK_START-->'[\s\S]*type: 'thinking'/, '没有把 THINK 标记解析成 thinking segment')
expectMatch('ChatView.vue', files.chatView, /class="thinking-block"[\s\S]*\n\s+open[\s\S]*<summary class="thinking-summary"/, '思考块没有默认展开，用户会看不到思考正文')
if (files.chatView.includes(':open="item.loading"')) {
  failures.push('ChatView.vue 思考块仍绑定 item.loading；thinking 一写入 content 后 loading 会变 false')
}

expectIncludes('ToolCallCard.vue', files.toolCallCard, 'Tools')
expectIncludes('ToolCallCard.vue', files.toolCallCard, 'class="tool-kind"')
expectIncludes('ToolCallCard.vue', files.toolCallCard, '工具调用')
expectIncludes('ToolCallCard.vue', files.toolCallCard, 'watch')
expectIncludes('ToolCallCard.vue', files.toolCallCard, 'userToggled')
expectMatch('ToolCallCard.vue', files.toolCallCard, /watch\(\(\) => props\.collapsed[\s\S]*isCollapsed\.value = collapsed/, '工具完成后不会跟随 collapsed prop 自动折叠')

expectIncludes('websocket.ts', files.websocket, 'reasoning_tokens?: number')
expectIncludes('chat.ts', files.chatStore, 'function mergeFinalUsageRounds')
expectIncludes('chat.ts', files.chatStore, 'reasoningTokens: msg.reasoning_tokens || 0')
expectIncludes('chat.ts', files.chatStore, 'mergeFinalUsageRounds(last.usage.rounds, usageData)')
expectIncludes('chat.ts', files.chatStore, 'model: modelId')
expectMatch(
  'ChatView.vue',
  files.chatView,
  /chatStore\.sendMessage\(\s*content,\s*agentsStore\.currentAgentId,\s*toolsStore\.currentModel/,
  '发送消息必须继续使用当前 Agent 和当前模型',
)
expectIncludes('ChatInput.vue', files.chatInput, "send: [content: string]")
expectIncludes('ChatView.vue', files.chatView, ':title="item.role === \'user\' ? \'你\' : getAssistantLabel()"')
if (/<span class="role-name">\{\{\s*item\.role === 'user' \? '你'/.test(files.chatView)) {
  failures.push('ChatView.vue 用户消息仍在 role-name 中显示悬空的“你”文本，应由右侧用户头像承担身份标识')
}

if (failures.length > 0) {
  console.error('聊天身份与思考展示契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('聊天身份与思考展示契约测试通过')
