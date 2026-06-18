<template>
  <div class="chat-view">
    <div class="messages-container">
      <Welcome
        v-if="messages.length === 0 && !isLoading"
        title="Start a conversation"
        description="Ask me anything"
        variant="borderless"
      />
      <BubbleList
        v-else
        :list="bubbleList"
        max-height="100%"
        :auto-scroll="isStreaming"
        :virtual="false"
      >
        <template #content="{ item }">
          <div class="bubble-content-wrap">
            <template v-if="item.segments && item.segments.length > 0">
              <template v-for="(seg, segIdx) in item.segments" :key="segIdx">
                <div
                  v-if="seg.type === 'text' && seg.text"
                  class="markdown-body"
                  v-html="renderMarkdown(seg.text)"
                />
                <div v-else-if="seg.type === 'tool' && item.toolCalls && seg.toolIndex != null" class="tool-call-inline">
                  <ToolCallCard
                    :tool-call="item.toolCalls[seg.toolIndex!]"
                    :collapsed="item.toolCalls[seg.toolIndex!]?.status === 'done'"
                  />
                </div>
              </template>
            </template>
            <template v-else>
              <div
                v-if="item.isMarkdown"
                class="markdown-body"
                v-html="renderMarkdown(stripThinkingMarkers(item.content || ''))"
              />
              <span v-else>{{ item.content }}</span>
            </template>
            <TokenUsagePanel
              v-if="item.usage"
              :usage="item.usage"
              :tool-calls="item.toolCalls"
            />
          </div>
        </template>
      </BubbleList>
      <Thinking
        v-if="isLoading && !isStreaming"
        status="thinking"
        content=""
      />
    </div>

    <ChatInput
      :is-streaming="isStreaming"
      @send="handleSend"
      @stop="handleStop"
    />

    <InterruptDialog
      :interrupt="interrupt"
      @decide="handleInterruptDecide"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { BubbleList, Thinking, Welcome } from 'vue-element-plus-x'
import type { BubbleListItemProps } from 'vue-element-plus-x/types/BubbleList'
import { useChatStore } from '@/stores/chat'
import type { ToolCall, MessageUsage } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import { renderMarkdown } from '@/utils/markdown'
import ChatInput from '@/components/chat/ChatInput.vue'
import InterruptDialog from '@/components/chat/InterruptDialog.vue'
import ToolCallCard from '@/components/chat/ToolCallCard.vue'
import TokenUsagePanel from '@/components/chat/TokenUsagePanel.vue'

interface ContentSegment {
  type: 'text' | 'tool'
  text?: string
  toolIndex?: number
}

type ChatBubbleItem = BubbleListItemProps & {
  isMarkdown?: boolean
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  usage?: MessageUsage
}

const chatStore = useChatStore()
const agentsStore = useAgentsStore()
const { messages, isStreaming, interrupt } = storeToRefs(chatStore)

const isLoading = computed(() => {
  const msgs = messages.value
  if (msgs.length === 0) return false
  const last = msgs[msgs.length - 1]
  return last.role === 'user' && !isStreaming.value
})

const bubbleList = computed((): ChatBubbleItem[] =>
  messages.value
    .filter(msg => msg.role === 'user' || msg.role === 'assistant')
    .map((msg, idx, arr) => ({
      key: msg.id,
      role: msg.role === 'assistant' ? 'ai' : 'user',
      placement: msg.role === 'user' ? 'end' : 'start',
      content: msg.content || '',
      shape: 'corner' as const,
      variant: (msg.role === 'user' ? 'outlined' : 'filled') as 'outlined' | 'filled',
      isMarkdown: msg.role !== 'user',
      toolCalls: msg.toolCalls,
      usage: msg.usage,
      segments: msg.role === 'assistant' && msg.toolCalls?.length
        ? parseSegments(msg.content || '', msg.toolCalls)
        : undefined,
      loading:
        msg.role === 'assistant'
        && idx === arr.length - 1
        && isStreaming.value
        && !msg.content,
      avatarSize: '28px',
      avatarGap: '8px',
    })),
)


function stripThinkingMarkers(content: string): string {
  return content.replace(/<!--(?:THINK_START|THINK_END)-->/g, '').trim()
}

function parseSegments(content: string, toolCalls?: ToolCall[]): ContentSegment[] {
  const segments: ContentSegment[] = []
  const pattern = /<!--TOOL:(\d+)-->/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(content)) !== null) {
    const textBefore = content.slice(lastIndex, match.index).trim()
    if (textBefore) {
      segments.push({ type: 'text', text: stripThinkingMarkers(textBefore) })
    }
    const toolIdx = parseInt(match[1], 10)
    if (toolCalls && toolIdx < toolCalls.length) {
      segments.push({ type: 'tool', toolIndex: toolIdx })
    }
    lastIndex = match.index + match[0].length
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) {
    segments.push({ type: 'text', text: stripThinkingMarkers(remaining) })
  }

  return segments
}

function handleSend(content: string) {
  chatStore.sendMessage(content, agentsStore.currentAgentId)
}

function handleStop() {
  chatStore.stopGeneration()
}

function handleInterruptDecide(decision: { type: string }) {
  chatStore.respondToInterrupt(decision.type === 'approve', agentsStore.currentAgentId)
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

function handleMarkdownClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
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
  chatStore.connect()
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
}

.messages-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
  background: var(--el-bg-color-page);
  min-width: 0;
}

.messages-container :deep(.elx-bubble-list) {
  width: 100%;
}

.messages-container :deep(.elx-bubble) {
  max-width: 85% !important;
}

.messages-container :deep(.elx-bubble__content) {
  max-width: none !important;
  min-width: 0;
}

.bubble-content-wrap {
  width: 100%;
  min-width: 0;
  overflow-wrap: anywhere;
}

.tool-call-inline {
  margin: 8px 0;
  position: relative;
  z-index: 1;
  pointer-events: auto !important;
  max-width: 100%;
  overflow-x: auto;
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

.messages-container :deep(.elx-welcome__description) {
  color: var(--el-text-color-secondary) !important;
}

@media (max-width: 900px) {
  .messages-container {
    padding: 12px;
  }

  .messages-container :deep(.elx-bubble) {
    max-width: 100% !important;
  }
}

@media (max-width: 520px) {
  .messages-container {
    padding: 8px;
  }

  .messages-container :deep(.elx-bubble) {
    max-width: 100% !important;
  }

  .messages-container :deep(.elx-bubble__content) {
    padding: 8px 10px;
  }
}
</style>
