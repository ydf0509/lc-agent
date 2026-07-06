<template>
  <div class="chat-view">
    <div v-if="viewingSubAgentRunId" class="sub-agent-detail-view">
      <div class="sub-agent-detail-header">
        <el-button size="small" @click="handleBackToMainChat">
          ← 返回主对话
        </el-button>
        <span v-if="subAgentRun" class="sub-agent-detail-title">
          子Agent: {{ subAgentRun.sub_agent_name || subAgentRun.sub_agent_id }}
        </span>
        <span v-else-if="loadingSubAgent" class="sub-agent-detail-title">
          加载中...
        </span>
      </div>
      <div v-if="loadingSubAgent" class="sub-agent-detail-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载子Agent执行过程...</span>
      </div>
      <div v-else-if="subAgentEvents.length === 0" class="sub-agent-detail-empty">
        暂无执行事件
      </div>
      <div v-else class="sub-agent-events">
        <div
          v-for="event in subAgentEvents"
          :key="event.id"
          class="sub-agent-event-item"
          :class="'event-' + event.event_type.replace(/^on_/, '')"
        >
          <div class="event-header">
            <span class="event-type-badge">{{ event.event_type }}</span>
            <span class="event-seq">#{{ event.sequence }}</span>
          </div>
          <div v-if="event.event_type === 'on_chat_model_stream'" class="event-preview">
            <span class="event-text">{{ event.payload?.data?.chunk?.content || event.payload?.data?.chunk || '' }}</span>
          </div>
          <div v-else-if="event.event_type === 'on_tool_start'" class="event-preview">
            <span class="event-tool-name">{{ event.payload?.name || event.payload?.data?.name }}()</span>
            <span class="event-args">{{ JSON.stringify(event.payload?.data?.input || event.payload?.data || {}) }}</span>
          </div>
          <div v-else-if="event.event_type === 'on_tool_end'" class="event-preview">
            <span class="event-result-tag">结果</span>
            <span class="event-text">{{ String(event.payload?.data?.output || '').slice(0, 200) }}</span>
          </div>
          <div v-else class="event-preview">
            <span class="event-text">{{ JSON.stringify(event.payload?.data || event.payload || {}).slice(0, 200) }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="messages-container">
      <Welcome
        v-if="messages.length === 0 && !isLoading"
        title="Start a conversation"
        description="Ask me anything"
        variant="borderless"
      />
      <template v-else>
        <BubbleList
          :list="bubbleList"
          max-height="100%"
          :auto-scroll="isStreaming"
          :virtual="false"
        >
        <template #item="{ item }">
          <div
            v-if="item.itemType === 'load-older'"
            class="load-older-messages is-inline"
          >
            <el-button
              :loading="loadingOlder"
              size="small"
              text
              @click="handleLoadOlderMessages"
            >
              {{ loadingOlder ? '加载中...' : '加载更早的消息' }}
            </el-button>
          </div>
        </template>
        <template #avatar="{ item }">
          <div
            class="role-avatar"
            :class="item.role === 'user' ? 'is-user' : 'is-ai'"
            :title="item.role === 'user' ? '你' : getAssistantLabel()"
            :aria-label="item.role === 'user' ? '你' : getAssistantLabel()"
          >
            <el-icon>
              <User v-if="item.role === 'user'" />
              <Cpu v-else />
            </el-icon>
          </div>
        </template>
        <template #header="{ item }">
          <div v-if="item.role === 'user'" class="role-header is-user">
            <button
              v-if="canEditMessage(item)"
              class="message-edit-btn"
              type="button"
              title="编辑并重新发送"
              @click.stop="startEditMessage(item)"
            >
              编辑
            </button>
          </div>
          <div v-else class="role-header is-ai">
            <span class="role-header-icon" aria-hidden="true">
              <el-icon><Cpu /></el-icon>
            </span>
            <span class="role-name">{{ getAssistantLabel() }}</span>
            <span class="role-model">{{ getModelLabel() }}</span>
          </div>
        </template>
        <template #content="{ item }">
          <div class="bubble-content-wrap">
            <template v-if="item.segments && item.segments.length > 0">
              <template v-for="(seg, segIdx) in item.segments" :key="segIdx">
                <div
                  v-if="seg.type === 'text' && seg.text"
                  class="markdown-body"
                  v-html="renderMarkdown(seg.text)"
                />
                <details
                  v-else-if="seg.type === 'thinking' && seg.text"
                  class="thinking-block"
                  :open="isThinkingExpanded(item)"
                >
                  <summary class="thinking-summary">
                    <el-icon><Cpu /></el-icon>
                    <span>思考过程</span>
                  </summary>
                  <div class="markdown-body thinking-body" v-html="renderMarkdown(seg.text)" />
                </details>
                <div v-else-if="seg.type === 'tool' && item.toolCalls && seg.toolIndex != null" class="tool-call-inline">
                  <TodoProgressCard
                    v-if="item.toolCalls[seg.toolIndex!]?.name === 'write_todos'"
                    :tool-call="item.toolCalls[seg.toolIndex!]"
                  />
                  <SubAgentCard
                    v-else-if="item.toolCalls[seg.toolIndex!]?.name === 'task' && item.toolCalls[seg.toolIndex!]?.subAgentId"
                    :tool-call="item.toolCalls[seg.toolIndex!]"
                    @view-detail="handleViewSubAgentDetail"
                  />
                  <ToolCallCard
                    v-else
                    :tool-call="item.toolCalls[seg.toolIndex!]"
                    :collapsed="item.toolCalls[seg.toolIndex!]?.status === 'done'"
                  />
                </div>
              </template>
              <HttpTracesGroup
                v-if="item.httpTraces?.length || item.httpTracesCount"
                :traces="item.httpTraces"
                :traces-count="item.httpTracesCount"
                :session-id="chatStore.threadId || undefined"
                :message-id="item.messageId"
                :rounds="item.usage?.rounds"
              />
            </template>
            <template v-else>
              <div
                v-if="item.isMarkdown"
                class="markdown-body"
                v-html="renderMarkdown(stripThinkingMarkers(item.content || ''))"
              />
              <span v-else class="user-plain-text">{{ item.content }}</span>
            </template>
            <div
              v-if="shouldShowReasoningNotice(item)"
              class="thinking-unavailable"
            >
              <el-icon><Cpu /></el-icon>
              <div class="thinking-unavailable-text">
                <strong>模型进行了内部推理</strong>
                <span>
                  本轮消耗 {{ formatCompactTokens(getReasoningTokenTotal(item.usage)) }} reasoning tokens，
                  但供应商没有返回可展示的思考文字。
                </span>
              </div>
            </div>
            <MessageToolbar
              v-if="getOriginalMessage(item.messageId) && !item.loading"
              :message="getOriginalMessage(item.messageId)!"
              :model-name="sessionModel"
              :has-thinking="item.hasThinking"
              :has-tool-calls="item.hasToolCalls"
              :has-answer="item.hasAnswer"
            />
            <TokenUsagePanel
              v-if="item.usage"
              :usage="item.usage"
              :tool-calls="item.toolCalls"
            />
          </div>
        </template>
      </BubbleList>
      </template>
      <Thinking
        v-if="isLoading && !isStreaming && !errorMessage"
        status="thinking"
        content=""
      />
    </div>

    <ChatInput
      v-if="!viewingSubAgentRunId"
      :is-streaming="isStreaming"
      :edit-content="editingContent"
      :is-editing="Boolean(editingMessageId)"
      @send="handleSend"
      @stop="handleStop"
      @cancel-edit="cancelEdit"
    />

    <InterruptDialog
      :interrupt="interrupt"
      @decide="handleInterruptDecide"
      @resume="handleInterruptResume"
      @allow-permanently="handleAllowPermanently"
    />

    <CodeBlockModal
      :visible="codeModalVisible"
      :code="codeModalSource"
      :language="codeModalLanguage"
      @close="codeModalVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
// Workaround: avoid '<!--' directly in string literals (Rolldown WASM parser bug with HTML comment-like strings)
const C = '\x3c!--'  // '<' + '!--' = '<!--'
const THINK_START = `${C}THINK_START-->`
const THINK_END = `${C}THINK_END-->`
const HTTP_MARKER = `${C}HTTP:`
const TOOL_MARKER = `${C}TOOL:`

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { BubbleList, Thinking, Welcome } from 'vue-element-plus-x'
import type { BubbleListItemProps } from 'vue-element-plus-x/types/BubbleList'
import { Cpu, User, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import type { ToolCall, MessageUsage, ReplayMessage, HttpTrace, ErrorInfo } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import { useToolsStore } from '@/stores/tools'
import { renderMarkdown } from '@/utils/markdown'
import ChatInput from '@/components/chat/ChatInput.vue'
import InterruptDialog from '@/components/chat/InterruptDialog.vue'
import TodoProgressCard from '@/components/chat/TodoProgressCard.vue'
import ToolCallCard from '@/components/chat/ToolCallCard.vue'
import SubAgentCard from '@/components/chat/SubAgentCard.vue'
import HttpTracesGroup from '@/components/chat/HttpTracesGroup.vue'
import TokenUsagePanel from '@/components/chat/TokenUsagePanel.vue'
import MessageToolbar from '@/components/chat/MessageToolbar.vue'
import CodeBlockModal from '@/components/chat/CodeBlockModal.vue'

const LOAD_OLDER_REVEAL_THRESHOLD = 24

interface ContentSegment {
  type: 'text' | 'thinking' | 'tool' | 'http'
  text?: string
  toolIndex?: number
  httpIndex?: number
}

type MessageBubbleItem = BubbleListItemProps & {
  role: 'user' | 'ai'
  messageId: string
  isMarkdown?: boolean
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  usage?: MessageUsage
  hasThinking?: boolean
  hasToolCalls?: boolean
  hasAnswer?: boolean
  httpTraces?: HttpTrace[]
  httpTracesCount?: number
  isStreamingMessage?: boolean
}

type LoadOlderBubbleItem = BubbleListItemProps & {
  key: string
  type: 'load-older'
  itemType: 'load-older'
  role: 'ai'
  messageId: string
  content: string
  isMarkdown?: boolean
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  usage?: MessageUsage
  hasThinking?: boolean
  hasToolCalls?: boolean
  hasAnswer?: boolean
  httpTraces?: HttpTrace[]
  httpTracesCount?: number
  isStreamingMessage?: boolean
}

type ChatBubbleItem = MessageBubbleItem | LoadOlderBubbleItem

const chatStore = useChatStore()
const agentsStore = useAgentsStore()
const toolsStore = useToolsStore()
const { messages, isStreaming, interrupt, errorMessage, hasOlderMessages, loadingOlder } = storeToRefs(chatStore)
const editingMessageId = ref<string | null>(null)
const editingContent = ref('')
const messagesContainerRef = ref<HTMLElement | null>(null)
const showLoadOlderMessages = ref(false)
const codeModalVisible = ref(false)
const codeModalSource = ref('')
const codeModalLanguage = ref('')

const isLoading = computed(() => {
  const msgs = messages.value
  if (msgs.length === 0) return false
  const last = msgs[msgs.length - 1]
  return last.role === 'user' && !isStreaming.value
})

function createLoadOlderItem(): LoadOlderBubbleItem {
  return {
    key: 'load-older-messages',
    type: 'load-older',
    itemType: 'load-older',
    role: 'ai',
    messageId: '__load_older_messages__',
    content: '加载更早的消息',
  }
}

const bubbleList = computed((): ChatBubbleItem[] => {
  const items = messages.value
    .filter(msg => msg.role === 'user' || msg.role === 'assistant')
    .map((msg, idx, arr): MessageBubbleItem => {
      const segs = msg.role === 'assistant' && hasStructuredSegments(msg.content || '', msg.toolCalls)
        ? parseSegments(msg.content || '', msg.toolCalls)
        : undefined
      const isStreamingMessage =
        msg.role === 'assistant'
        && idx === arr.length - 1
        && isStreaming.value
      return {
        key: msg.id,
        messageId: msg.id,
        role: msg.role === 'assistant' ? 'ai' : 'user',
        placement: msg.role === 'user' ? 'end' : 'start',
        content: msg.content || '',
        shape: 'corner' as const,
        variant: (msg.role === 'user' ? 'outlined' : 'filled') as 'outlined' | 'filled',
        isMarkdown: msg.role !== 'user',
        toolCalls: msg.toolCalls,
        usage: msg.usage,
        segments: segs,
        httpTraces: msg.role === 'assistant' ? msg.httpTraces : undefined,
        httpTracesCount: msg.role === 'assistant' ? (msg.httpTracesCount || 0) : 0,
        hasThinking: segs?.some(s => s.type === 'thinking' && s.text?.trim()) ?? false,
        hasToolCalls: segs?.some(s => s.type === 'tool') ?? false,
        hasAnswer: segs?.some(s => s.type === 'text' && s.text?.trim()) ?? false,
        isStreamingMessage,
        loading:
          isStreamingMessage
          && !msg.content,
        avatarSize: '28px',
        avatarGap: '8px',
      }
    })

  if (hasOlderMessages.value) items.unshift(createLoadOlderItem())
  return items
})

const lastUserMessage = computed(() =>
  [...messages.value].reverse().find(msg => msg.role === 'user'),
)

const sessionModel = computed(() => getModelLabel())

function getOriginalMessage(messageId: string) {
  return messages.value.find(m => m.id === messageId)
}

function getAssistantLabel(): string {
  return agentsStore.currentAgent?.name || 'AI'
}

function getModelLabel(): string {
  if (agentsStore.isCodeAgent) return '代码内定义'
  const model = toolsStore.currentModel || agentsStore.currentAgent?.default_model || ''
  if (!model) return '模型未选择'
  const parts = model.split('/')
  return parts[parts.length - 1] || model
}

function isThinkingExpanded(item: ChatBubbleItem): boolean {
  return item.isStreamingMessage === true
}

function canEditMessage(item: ChatBubbleItem) {
  return item.role === 'user'
    && lastUserMessage.value?.id === item.messageId
    && !isStreaming.value
}

function startEditMessage(item: ChatBubbleItem) {
  if (!canEditMessage(item)) return
  editingMessageId.value = item.messageId
  editingContent.value = item.content || ''
}

function cancelEdit() {
  editingMessageId.value = null
  editingContent.value = ''
}

function hasStructuredSegments(content: string, toolCalls?: ToolCall[]): boolean {
  return Boolean(
    toolCalls?.length
    || content.includes(THINK_START)
    || content.includes(THINK_END)
    || content.includes(HTTP_MARKER),
  )
}

function getReasoningTokenTotal(usage?: MessageUsage): number {
  return usage?.rounds.reduce((total, round) => total + (round.reasoningTokens || 0), 0) || 0
}

function hasThinkingSegment(segments?: ContentSegment[]): boolean {
  return Boolean(segments?.some(seg => seg.type === 'thinking' && seg.text?.trim()))
}

function shouldShowReasoningNotice(item: ChatBubbleItem): boolean {
  return item.role === 'ai'
    && getReasoningTokenTotal(item.usage) > 0
    && !hasThinkingSegment(item.segments)
}

function formatCompactTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function stripThinkingMarkers(content: string): string {
  return content.replace(/<!--(?:THINK_START|THINK_END)-->/g, '').trim()
}

function stripUiMarkers(content: string): string {
  return stripThinkingMarkers(content).replace(/<!--TOOL:\d+-->/g, '').replace(/<!--HTTP:\d+-->/g, '').trim()
}

function getReplayHistory(beforeMessageId: string): ReplayMessage[] {
  const idx = messages.value.findIndex(msg => msg.id === beforeMessageId)
  if (idx < 0) return []

  return messages.value
    .slice(0, idx)
    .filter((msg): msg is typeof msg & { role: 'user' | 'assistant' } =>
      msg.role === 'user' || msg.role === 'assistant',
    )
    .map(msg => ({
      role: msg.role,
      content: stripUiMarkers(msg.content || ''),
    }))
    .filter(msg => msg.content.trim())
}

function parseSegments(content: string, toolCalls?: ToolCall[]): ContentSegment[] {
  const segments: ContentSegment[] = []
  const pattern = /<!--(?:TOOL:(\d+)|HTTP:(\d+)|THINK_START|THINK_END)-->/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  let inThinking = false

  while ((match = pattern.exec(content)) !== null) {
    const textBefore = content.slice(lastIndex, match.index).trim()
    const marker = match[0]

    if (marker === THINK_START) {
      if (textBefore) {
        segments.push({ type: inThinking ? 'thinking' : 'text', text: stripThinkingMarkers(textBefore) })
      }
      inThinking = true
      lastIndex = match.index + match[0].length
      continue
    }

    if (marker === THINK_END) {
      if (textBefore) {
        segments.push({ type: 'thinking', text: stripThinkingMarkers(textBefore) })
      }
      inThinking = false
      lastIndex = match.index + match[0].length
      continue
    }

    if (match[2] != null) {
      if (textBefore) {
        segments.push({ type: inThinking ? 'thinking' : 'text', text: stripThinkingMarkers(textBefore) })
      }
      segments.push({ type: 'http', httpIndex: parseInt(match[2], 10) })
      lastIndex = match.index + match[0].length
      continue
    }

    if (textBefore) {
      segments.push({ type: inThinking ? 'thinking' : 'text', text: stripThinkingMarkers(textBefore) })
    }
    const toolIdx = parseInt(match[1], 10)
    if (toolCalls && toolIdx < toolCalls.length) {
      segments.push({ type: 'tool', toolIndex: toolIdx })
    }
    lastIndex = match.index + match[0].length
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) {
    segments.push({ type: inThinking ? 'thinking' : 'text', text: stripThinkingMarkers(remaining) })
  }

  return segments
}

function handleSend(content: string) {
  const editMessageId = editingMessageId.value
  const history = editMessageId ? getReplayHistory(editMessageId) : undefined
  const modelOverride = agentsStore.isCodeAgent ? '' : toolsStore.currentModel
  if (editingMessageId.value) {
    chatStore.truncateAfterMessage(editingMessageId.value)
    cancelEdit()
  }
  chatStore.sendMessage(content, agentsStore.currentAgentId, modelOverride, {
    replaceFromMessageId: editMessageId || undefined,
    history,
    llmParams: toolsStore.llmParams,
  })
}

function handleStop() {
  chatStore.stopGeneration()
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

let lastNotificationId: ReturnType<typeof ElMessage> | null = null

function showErrorNotification(error: ErrorInfo) {
  if (lastNotificationId) {
    lastNotificationId.close()
    lastNotificationId = null
  }

  const t = escapeHtml(error.title)
  const d = escapeHtml(error.detail)
  const suggestions = error.suggestions?.map(s => `<li>${escapeHtml(s)}</li>`).join('') || ''
  const tech = error.techDetail ? escapeHtml(error.techDetail) : ''

  lastNotificationId = ElMessage({
    type: 'error',
    dangerouslyUseHTMLString: true,
    showClose: true,
    duration: 0,
    grouping: true,
    message: `<div style="line-height:1.5;max-width:420px">
      <strong style="font-size:15px">${t}</strong>
      <div style="margin:6px 0 10px;font-size:13px;color:var(--el-text-color-regular)">${d}</div>
      ${suggestions ? `<div style="font-size:12px;color:var(--el-text-color-secondary)">
        <strong>建议：</strong>
        <ul style="margin:4px 0 0;padding-left:18px;line-height:1.6">${suggestions}</ul></div>` : ''}
      ${tech ? `<details style="margin-top:10px;font-size:11px;color:var(--el-text-color-placeholder)">
        <summary style="cursor:pointer">技术详情</summary>
        <pre style="margin:6px 0 0;padding:8px;background:var(--el-fill-color-light);border-radius:4px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;max-height:150px;overflow-y:auto">${tech}</pre>
      </details>` : ''}
    </div>`,
    onClose: () => { lastNotificationId = null },
  })
}

watch(errorMessage, (newError) => {
  if (newError) {
    showErrorNotification(newError)
  }
})

watch(() => messages.value[messages.value.length - 1]?.id, () => {
  scrollMessagesToBottom()
}, { flush: 'post' })

function handleAllowPermanently(toolName: string) {
  chatStore.respondToInterrupt(true, agentsStore.currentAgentId, toolName, toolsStore.llmParams)
}

function handleInterruptDecide(decision: { type: string }) {
  chatStore.respondToInterrupt(decision.type === 'approve', agentsStore.currentAgentId, undefined, toolsStore.llmParams)
}

function handleInterruptResume(value: any) {
  (chatStore as any).resumeInterrupt(value, agentsStore.currentAgentId, toolsStore.currentModel, toolsStore.llmParams)
}

const viewingSubAgentRunId = ref<string | null>(null)
const subAgentEvents = ref<any[]>([])
const subAgentRun = ref<any>(null)
const loadingSubAgent = ref(false)

async function handleViewSubAgentDetail(runId: string) {
  if (!runId) return
  loadingSubAgent.value = true
  viewingSubAgentRunId.value = runId
  try {
    const runResp = await fetch(`/api/sub-agent-runs/${runId}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
    })
    if (runResp.ok) {
      subAgentRun.value = await runResp.json()
    }
    const eventsResp = await fetch(`/api/sub-agent-runs/${runId}/events`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
    })
    if (eventsResp.ok) {
      const data = await eventsResp.json()
      subAgentEvents.value = data.events || []
    }
  } catch (e) {
    console.error('[SubAgent] Failed to load details:', e)
  } finally {
    loadingSubAgent.value = false
  }
}

function handleBackToMainChat() {
  viewingSubAgentRunId.value = null
  subAgentRun.value = null
  subAgentEvents.value = []
}

function getCodeToCopy(button: HTMLButtonElement): string {
  const encoded = button.dataset.code
  if (encoded) {
    try {
      return decodeURIComponent(encoded)
    } catch {
      return encoded
    }
  }
  return button.closest('.markdown-code-block')?.querySelector('code')?.textContent ?? ''
}

function fallbackCopy(text: string) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

async function copyMarkdownCode(button: HTMLButtonElement) {
  const text = getCodeToCopy(button)
  if (!text) return

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
  } else {
    fallbackCopy(text)
  }

  const previousText = button.textContent || '复制'
  button.textContent = '已复制'
  button.classList.add('copied')
  window.setTimeout(() => {
    button.textContent = previousText
    button.classList.remove('copied')
  }, 1400)
}

function getMessagesScroller() {
  return messagesContainerRef.value?.querySelector('.elx-bubble-list') as HTMLElement | null
}

function handleMessagesScroll() {
  const scroller = getMessagesScroller()
  if (!scroller) {
    showLoadOlderMessages.value = false
    return
  }
  const canRevealLoadOlderMessages = scroller.scrollHeight > scroller.clientHeight + LOAD_OLDER_REVEAL_THRESHOLD
  showLoadOlderMessages.value = canRevealLoadOlderMessages && scroller.scrollTop <= LOAD_OLDER_REVEAL_THRESHOLD
}

async function scrollMessagesToBottom() {
  await nextTick()
  const container = getMessagesScroller()
  if (!container) return
  container.scrollTop = container.scrollHeight
  handleMessagesScroll()
}

async function handleLoadOlderMessages() {
  if (loadingOlder.value) return
  const sessionId = chatStore.threadId
  const scroller = getMessagesScroller()
  if (!sessionId || !scroller) return

  const distanceFromBottom = scroller.scrollHeight - scroller.scrollTop
  await chatStore.loadOlderMessages(sessionId)
  await nextTick()
  scroller.scrollTop = scroller.scrollHeight - distanceFromBottom
  handleMessagesScroll()
}

function handleMarkdownClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null

  const expandBtn = target?.closest?.('.markdown-code-expand') as HTMLButtonElement | null
  if (expandBtn) {
    event.preventDefault()
    const encoded = expandBtn.dataset.code || ''
    const lang = expandBtn.dataset.lang || 'text'
    try {
      codeModalSource.value = decodeURIComponent(encoded)
    } catch {
      codeModalSource.value = encoded
    }
    codeModalLanguage.value = lang
    codeModalVisible.value = true
    return
  }

  const button = target?.closest?.('.markdown-code-copy') as HTMLButtonElement | null
  if (!button) return
  event.preventDefault()
  copyMarkdownCode(button).catch(() => {
    button.textContent = '复制失败'
    window.setTimeout(() => {
      button.textContent = '复制'
    }, 1400)
  })
}

onMounted(() => {
  if (!chatStore.isConnected && !chatStore.threadId) {
    chatStore.connect()
  }
  document.addEventListener('click', handleMarkdownClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleMarkdownClick)
})
</script>

<style scoped>
.chat-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  min-height: 0;
}

.messages-container {
  --chat-assistant-bubble-width: min(85%, 920px);
  --chat-user-bubble-max-width: min(78%, 720px);
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
  background: var(--el-bg-color-page);
  min-width: 0;
  min-height: 0;
}

.messages-container :deep(.elx-bubble-list) {
  width: 100%;
  flex: 1;
  min-height: 0;
}

.messages-container :deep(.elx-bubble-list__list) {
  height: 100%;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  -webkit-overflow-scrolling: touch;
}

.messages-container :deep(.elx-bubble-list__content) {
  min-height: 100%;
}

.load-older-messages.is-inline {
  display: flex;
  justify-content: center;
  width: 100%;
  padding: 4px 0 8px;
}

.messages-container :deep(.elx-bubble) {
  max-width: 100% !important;
}

.messages-container :deep(.elx-bubble--start) {
  width: var(--chat-assistant-bubble-width) !important;
  max-width: var(--chat-assistant-bubble-width) !important;
  align-self: flex-start;
}

.messages-container :deep(.elx-bubble--end) {
  width: 100% !important;
  max-width: 100% !important;
  align-self: flex-end;
  justify-content: flex-end;
}

.messages-container :deep(.elx-bubble--end .elx-bubble__avatar) {
  margin-top: 2px;
}

.messages-container :deep(.elx-bubble--end .elx-bubble__header) {
  display: flex;
  justify-content: flex-end;
  min-height: 22px;
  margin-bottom: 4px;
}

.messages-container :deep(.elx-bubble--start),
.messages-container :deep(.elx-bubble--end) {
  padding-inline: 0 !important;
}

.messages-container :deep(.elx-bubble--end .elx-bubble__content-wrapper) {
  width: fit-content;
  max-width: var(--chat-user-bubble-max-width) !important;
}

.messages-container :deep(.elx-bubble__content) {
  max-width: none !important;
  min-width: 0;
}

.messages-container :deep(.elx-bubble--start .elx-bubble__content-wrapper),
.messages-container :deep(.elx-bubble--start .elx-bubble__content) {
  width: 100%;
  max-width: 100% !important;
}

.messages-container :deep(.elx-bubble--end .elx-bubble__content-wrapper),
.messages-container :deep(.elx-bubble--end .elx-bubble__content) {
  max-width: 100% !important;
}

.role-avatar {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--el-border-color);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
}

.role-header.is-user {
  display: flex;
  justify-content: flex-end;
  width: 100%;
}

.message-edit-btn {
  border: 1px solid color-mix(in srgb, var(--el-color-success) 34%, var(--el-border-color));
  border-radius: 999px;
  background: color-mix(in srgb, var(--el-color-success) 12%, var(--el-bg-color-overlay));
  color: var(--el-color-success);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  opacity: 0;
  padding: 5px 9px;
  transform: translateY(2px);
  transition: opacity 0.16s ease, transform 0.16s ease, background 0.16s ease;
}

.messages-container :deep(.elx-bubble--end:hover) .message-edit-btn,
.message-edit-btn:focus-visible {
  opacity: 1;
  transform: translateY(0);
}

.message-edit-btn:hover {
  background: color-mix(in srgb, var(--el-color-success) 22%, var(--el-bg-color-overlay));
}

.role-avatar.is-user {
  color: #f7fee7;
  background: linear-gradient(135deg, #2ea043, #1f7a3a);
  border-color: rgba(74, 222, 128, 0.45);
}

.role-avatar.is-ai {
  color: #d8f3dc;
  background: linear-gradient(135deg, #15382a, #0b2119);
  border-color: rgba(74, 222, 128, 0.32);
}

.role-header {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 7px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.role-header.is-ai {
  min-height: 24px;
}

.role-header-icon {
  display: none;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  color: #d8f3dc;
  background: linear-gradient(135deg, #15382a, #0b2119);
  border: 1px solid rgba(74, 222, 128, 0.32);
}

.role-name {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.role-model {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--el-text-color-secondary);
  background: color-mix(in srgb, var(--el-fill-color-light) 82%, transparent);
  border: 1px solid color-mix(in srgb, var(--el-border-color-lighter) 78%, transparent);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
}

.bubble-content-wrap {
  width: 100%;
  min-width: 0;
  overflow-wrap: anywhere;
}

.user-plain-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.tool-call-inline {
  margin: 8px 0;
  position: relative;
  z-index: 1;
  pointer-events: auto !important;
  max-width: 100%;
  overflow-x: auto;
}

.thinking-block {
  margin: 8px 0 10px;
  border-radius: 12px;
  border: 1px solid rgba(234, 179, 8, 0.22);
  border-left: 3px solid rgba(234, 179, 8, 0.72);
  background: rgba(234, 179, 8, 0.08);
  overflow: hidden;
}

.thinking-summary {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 11px;
  cursor: pointer;
  user-select: none;
  color: #d69e2e;
  font-size: 12px;
  font-weight: 700;
}

.thinking-summary::-webkit-details-marker {
  display: none;
}

.thinking-summary::after {
  content: '展开';
  margin-left: auto;
  color: var(--el-text-color-secondary);
  font-weight: 500;
  font-size: 11px;
}

.thinking-block[open] .thinking-summary::after {
  content: '收起';
}

.thinking-body {
  padding: 0 12px 10px;
  color: #c58f22;
  font-size: 13px;
  opacity: 0.92;
}

.thinking-unavailable {
  display: flex;
  gap: 9px;
  align-items: flex-start;
  margin: 8px 0 10px;
  padding: 9px 11px;
  border-radius: 12px;
  color: var(--el-text-color-secondary);
  background: color-mix(in srgb, var(--el-fill-color-light) 82%, var(--el-color-warning) 8%);
  border: 1px dashed color-mix(in srgb, var(--el-color-warning) 36%, var(--el-border-color));
  font-size: 12px;
  line-height: 1.55;
}

.thinking-unavailable .el-icon {
  color: var(--el-color-warning);
  margin-top: 2px;
  flex-shrink: 0;
}

.thinking-unavailable-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.thinking-unavailable-text strong {
  color: var(--el-text-color-primary);
  font-size: 12px;
}

.messages-container :deep([style*="pointer-events"]) .tool-call-inline,
.messages-container :deep(.tool-call-card) {
  pointer-events: auto !important;
  cursor: pointer;
}

.messages-container :deep(.markdown-body) {
  max-width: 100%;
}

.messages-container :deep(.markdown-code-block),
.messages-container :deep(.markdown-body pre),
.messages-container :deep(.markdown-body table),
.messages-container :deep(.tool-call-card) {
  max-width: 100%;
  overflow-x: auto;
}

.messages-container :deep(.markdown-body code) {
  overflow-wrap: anywhere;
}

.messages-container :deep(.elx-welcome) {
  background: var(--el-bg-color-overlay) !important;
  border: 1px solid var(--el-border-color-lighter) !important;
  border-radius: 12px;
  color: var(--el-text-color-primary);
}

.messages-container :deep(.elx-welcome__title) {
  color: var(--el-text-color-primary) !important;
}

@media (max-width: 960px) {
  .messages-container {
    padding: 6px 0;
    overscroll-behavior-y: contain;
  }

  .messages-container :deep(.elx-bubble--start),
  .messages-container :deep(.elx-bubble--end) {
    width: 100% !important;
    max-width: 100% !important;
    padding-inline: 0 !important;
  }

  .messages-container :deep(.elx-bubble--start .elx-bubble__content-wrapper),
  .messages-container :deep(.elx-bubble--start .elx-bubble__content),
  .messages-container :deep(.elx-bubble--end .elx-bubble__content-wrapper),
  .messages-container :deep(.elx-bubble--end .elx-bubble__content),
  .messages-container :deep(.elx-bubble__content) {
    width: 100%;
    max-width: 100% !important;
  }

  .messages-container :deep(.markdown-body),
  .messages-container :deep(.markdown-body > *:first-child),
  .messages-container :deep(.markdown-body > *:last-child) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .messages-container :deep(.markdown-code-block),
  .messages-container :deep(.markdown-body pre),
  .messages-container :deep(.markdown-body table),
  .messages-container :deep(.tool-call-card) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .thinking-summary {
    padding: 8px 8px;
  }

  .thinking-body {
    padding: 0 8px 10px;
  }

  .thinking-unavailable {
    padding: 8px 8px;
  }

  .messages-container :deep(.elx-bubble__avatar) {
    display: none !important;
  }

  .role-header {
    gap: 6px;
    margin-bottom: 5px;
  }

  .role-header-icon {
    display: inline-flex;
  }

  .role-model {
    max-width: 42vw;
  }
}

@media (max-width: 560px) {
  .messages-container {
    padding: 4px 0;
  }

  .messages-container :deep(.elx-bubble-list__content) {
    gap: 0 !important;
  }

  .messages-container :deep(.elx-bubble-list) {
    overscroll-behavior: contain;
  }

  .messages-container :deep(.elx-bubble--start),
  .messages-container :deep(.elx-bubble--end) {
    padding-inline: 0 !important;
    margin-inline: 0 !important;
  }

  .messages-container :deep(.elx-bubble__content) {
    padding-left: 6px !important;
    padding-right: 6px !important;
  }

  .messages-container :deep(.elx-bubble) {
    gap: 0 !important;
  }

  .messages-container :deep(.elx-bubble--start .elx-bubble__content-wrapper),
  .messages-container :deep(.elx-bubble--start .elx-bubble__content),
  .messages-container :deep(.elx-bubble--end .elx-bubble__content-wrapper),
  .messages-container :deep(.elx-bubble--end .elx-bubble__content),
  .messages-container :deep(.elx-bubble__content),
  .messages-container :deep(.markdown-body),
  .messages-container :deep(.tool-call-card) {
    width: 100%;
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .messages-container :deep(.markdown-code-block),
  .messages-container :deep(.markdown-body pre),
  .messages-container :deep(.markdown-body table) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .messages-container :deep(.markdown-body > p),
  .messages-container :deep(.markdown-body > ul),
  .messages-container :deep(.markdown-body > ol),
  .messages-container :deep(.markdown-body > blockquote),
  .messages-container :deep(.markdown-body > h1),
  .messages-container :deep(.markdown-body > h2),
  .messages-container :deep(.markdown-body > h3),
  .messages-container :deep(.markdown-body > h4),
  .messages-container :deep(.markdown-body > h5),
  .messages-container :deep(.markdown-body > h6) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .thinking-summary {
    padding: 7px 6px;
  }

  .thinking-body {
    padding: 0 6px 9px;
  }

  .thinking-unavailable {
    padding: 7px 6px;
  }

  .role-model {
    max-width: 46vw;
  }

  .role-header {
    font-size: 11px;
  }

  .message-edit-btn {
    opacity: 1;
    transform: none;
    padding: 4px 8px;
  }

  .thinking-summary,
  .thinking-body,
  .thinking-unavailable,
  .thinking-unavailable-text strong {
    font-size: 12px;
  }
}

.sub-agent-detail-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px 16px;
}
.sub-agent-detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color);
  margin-bottom: 12px;
}
.sub-agent-detail-title {
  font-weight: 600;
  font-size: 14px;
}
.sub-agent-detail-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
}
.sub-agent-detail-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
}
.sub-agent-events {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sub-agent-event-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
}
.event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.event-type-badge {
  font-size: 10px;
  font-family: monospace;
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.event-seq {
  font-size: 10px;
  color: var(--el-text-color-placeholder);
}
.event-preview {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.event-tool-name {
  font-weight: 600;
  color: var(--el-color-warning);
  margin-right: 4px;
}
.event-args {
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 11px;
}
.event-result-tag {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  margin-right: 4px;
}
.event-text {
  word-break: break-all;
}
.event-chat_model_stream {
  border-left: 2px solid var(--el-color-primary);
}
.event-tool_start {
  border-left: 2px solid var(--el-color-warning);
}
.event-tool_end {
  border-left: 2px solid var(--el-color-success);
}
</style>
