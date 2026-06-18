import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

const files = {
  chatView: read('src/views/ChatView.vue'),
  chatInput: read('src/components/chat/ChatInput.vue'),
  chatStore: read('src/stores/chat.ts'),
}

const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

function expectMatch(name, content, pattern, message) {
  if (!pattern.test(content)) failures.push(`${name} ${message}`)
}

expectIncludes('ChatView.vue', files.chatView, 'canEditMessage(item)')
expectIncludes('ChatView.vue', files.chatView, 'class="message-edit-btn"')
expectIncludes('ChatView.vue', files.chatView, 'title="编辑并重新发送"')
expectIncludes('ChatView.vue', files.chatView, '@click.stop="startEditMessage(item)"')
expectIncludes('ChatView.vue', files.chatView, 'const editingMessageId = ref<string | null>(null)')
expectIncludes('ChatView.vue', files.chatView, 'const editingContent = ref(\'\')')
expectIncludes('ChatView.vue', files.chatView, ':edit-content="editingContent"')
expectIncludes('ChatView.vue', files.chatView, ':is-editing="Boolean(editingMessageId)"')
expectIncludes('ChatView.vue', files.chatView, '@cancel-edit="cancelEdit"')
expectIncludes('ChatView.vue', files.chatView, 'function getReplayHistory(beforeMessageId: string): ReplayMessage[]')
expectIncludes('ChatView.vue', files.chatView, 'replaceFromMessageId: editMessageId || undefined')
expectIncludes('ChatView.vue', files.chatView, 'history,')
expectMatch(
  'ChatView.vue',
  files.chatView,
  /function canEditMessage\(item: ChatBubbleItem\)[\s\S]*item\.role === 'user'[\s\S]*lastUserMessage\.value\?\.id === item\.messageId[\s\S]*!isStreaming\.value/,
  '编辑入口必须限制为最后一条用户消息且非流式输出中',
)
expectMatch(
  'ChatView.vue',
  files.chatView,
  /function handleSend\(content: string\)[\s\S]*getReplayHistory\(editMessageId\)[\s\S]*chatStore\.truncateAfterMessage\(editingMessageId\.value\)[\s\S]*cancelEdit\(\)[\s\S]*chatStore\.sendMessage/,
  '编辑提交必须保留编辑点之前的历史、截断旧回复，再重新发送',
)
expectIncludes('ChatInput.vue', files.chatInput, 'isEditing?: boolean')
expectIncludes('ChatInput.vue', files.chatInput, 'watch(() => props.editContent')
expectIncludes('ChatInput.vue', files.chatInput, 'senderRef.value?.setText(content)')
expectIncludes('ChatInput.vue', files.chatInput, 'senderRef.value?.focus(\'end\')')
expectIncludes('ChatInput.vue', files.chatInput, 'class="edit-banner"')
expectIncludes('ChatInput.vue', files.chatInput, '@click="handleCancelEdit"')
expectIncludes('chat.ts', files.chatStore, 'function truncateAfterMessage(messageId: string)')
expectIncludes('chat.ts', files.chatStore, 'messages.value = messages.value.slice(0, idx)')
expectIncludes('chat.ts', files.chatStore, 'truncateAfterMessage')
expectIncludes('chat.ts', files.chatStore, 'export interface ReplayMessage')
expectIncludes('chat.ts', files.chatStore, 'export interface SendMessageOptions')
expectIncludes('chat.ts', files.chatStore, 'replace_from_message_id: options.replaceFromMessageId')
expectIncludes('chat.ts', files.chatStore, 'history: options.history')

if (failures.length > 0) {
  console.error('聊天编辑并重发契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('聊天编辑并重发契约测试通过')
