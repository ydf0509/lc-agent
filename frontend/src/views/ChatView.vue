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
import { computed, onMounted } from 'vue'
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


onMounted(() => {
  chatStore.connect()
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
}

.messages-container :deep(.elx-bubble-list) {
  width: 100%;
}

.messages-container :deep(.elx-bubble) {
  max-width: 85% !important;
}

.messages-container :deep(.elx-bubble__content) {
  max-width: none !important;
}

.bubble-content-wrap {
  width: 100%;
}

.tool-call-inline {
  margin: 8px 0;
  position: relative;
  z-index: 1;
  pointer-events: auto !important;
}

.messages-container :deep([style*="pointer-events"]) .tool-call-inline,
.messages-container :deep(.tool-call-card) {
  pointer-events: auto !important;
  cursor: pointer;
}

.messages-container :deep(.markdown-body) {
  max-width: 100%;
}

.messages-container :deep(.markdown-body pre.hljs) {
  background: var(--el-fill-color-darker, var(--el-bg-color));
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
</style>
