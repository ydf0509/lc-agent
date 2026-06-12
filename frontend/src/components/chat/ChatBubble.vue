<template>
  <div class="chat-bubble" :class="[message.role, { streaming: message.isStreaming }]">
    <div class="bubble-avatar" :class="message.role">
      <span v-if="message.role === 'user'" class="avatar-icon">👨‍💻</span>
      <span v-else class="avatar-icon">🤖</span>
    </div>
    <div class="bubble-body">
      <div class="bubble-label">
        <span v-if="message.role === 'user'" class="role-name user-name">You</span>
        <span v-else class="role-name ai-name">{{ modelLabel }}</span>
        <button
          v-if="showEdit"
          class="edit-btn"
          title="编辑并重发"
          @click="$emit('edit')"
        >✏️</button>
      </div>
      <div class="bubble-content">
        <template v-if="message.role === 'assistant'">
          <template v-for="(seg, idx) in renderedSegments" :key="idx">
            <ToolCallCard v-if="seg.type === 'tool' && seg.toolCall" :tool-call="seg.toolCall" :collapsed="true" />
            <div v-else-if="seg.type === 'text' && seg.html" :class="seg.cls">
              <div v-if="seg.cls === 'thinking-block'" class="thinking-header">
                <span class="thinking-icon">💭</span>
                <span class="thinking-label">思考中</span>
              </div>
              <div v-html="seg.html" class="markdown-body" />
            </div>
          </template>
        </template>
        <div v-else-if="message.role === 'user'" class="plain-text">{{ message.content }}</div>

        <span v-if="message.isStreaming" class="streaming-cursor">▊</span>

        <TokenUsagePanel v-if="message.role === 'assistant' && !message.isStreaming && message.usage" :usage="message.usage" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import { useToolsStore } from '@/stores/tools'
import ToolCallCard from './ToolCallCard.vue'
import TokenUsagePanel from './TokenUsagePanel.vue'
import type { ChatMessage, ToolCall } from '@/stores/chat'

interface RenderedSegment {
  type: 'text' | 'tool'
  html?: string
  cls?: string
  toolCall?: ToolCall
}

const props = defineProps<{
  message: ChatMessage
  showEdit?: boolean
}>()
defineEmits<{ edit: [] }>()
const toolsStore = useToolsStore()

const renderedSegments = computed((): RenderedSegment[] => {
  const content = props.message.content
  if (!content) return []

  const toolCalls = props.message.toolCalls || []
  const toolMarkerRe = /<!--TOOL:(\d+)-->/g
  const parts: RenderedSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let lastToolSegIdx = -1

  while ((match = toolMarkerRe.exec(content)) !== null) {
    const textBefore = content.slice(lastIndex, match.index).trim()
    if (textBefore) {
      parts.push({ type: 'text', html: renderMarkdown(textBefore), cls: 'thinking-block' })
    }
    const tcIdx = parseInt(match[1], 10)
    if (toolCalls[tcIdx]) {
      lastToolSegIdx = parts.length
      parts.push({ type: 'tool', toolCall: toolCalls[tcIdx] })
    }
    lastIndex = match.index + match[0].length
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) {
    parts.push({ type: 'text', html: renderMarkdown(remaining), cls: 'content-block' })
  }

  // Re-classify: text before the last tool = thinking, after = content
  for (let i = 0; i < parts.length; i++) {
    if (parts[i].type === 'text') {
      parts[i].cls = (lastToolSegIdx >= 0 && i < lastToolSegIdx) ? 'thinking-block' : 'content-block'
    }
  }

  return parts
})

const modelLabel = computed(() => {
  const model = toolsStore.currentModel
  if (!model) return 'AI'
  const parts = model.split('/')
  return parts[parts.length - 1] || 'AI'
})
</script>

<style scoped>
.chat-bubble {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  margin-bottom: 12px;
  border: 1px solid transparent;
}

.chat-bubble.user {
  background: #0f2b1e;
  border-color: #1b4332;
}

.chat-bubble.assistant {
  background: var(--lc-glass-bg);
  border-color: var(--lc-glass-border);
}

.bubble-avatar {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bubble-avatar.user {
  background: linear-gradient(135deg, #2ea043, #238636);
  box-shadow: 0 2px 8px rgba(46, 160, 67, 0.3);
}

.bubble-avatar.assistant {
  background: #21262d;
}

.bubble-body {
  flex: 1;
  min-width: 0;
}

.bubble-label {
  margin-bottom: 4px;
}

.role-name {
  font-size: 12px;
  font-weight: 600;
}

.user-name {
  color: #56d364;
}

.ai-name {
  color: #8b949e;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.bubble-content {
  overflow-wrap: break-word;
  line-height: 1.7;
  font-size: 14px;
}

.streaming-cursor {
  animation: blink 1s infinite;
  color: var(--lc-accent);
  font-size: 16px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.thinking-block {
  background: rgba(234, 179, 8, 0.08);
  border: 1px solid rgba(234, 179, 8, 0.2);
  border-left: 3px solid rgba(234, 179, 8, 0.6);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 8px 0;
  position: relative;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 2px 0 4px;
  user-select: none;
  border-bottom: 1px solid rgba(139, 148, 158, 0.1);
  margin-bottom: 6px;
}

.thinking-icon {
  font-size: 13px;
}

.thinking-label {
  font-size: 11px;
  color: #eab308;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.thinking-toggle {
  font-size: 10px;
  color: #6e7681;
  margin-left: auto;
}

.thinking-block :deep(.markdown-body) {
  font-size: 12.5px !important;
  color: #d4a017 !important;
  font-style: italic;
  line-height: 1.65;
  opacity: 0.9;
}

.thinking-block :deep(.markdown-body p) {
  color: #d4a017;
  margin: 4px 0;
}

.thinking-block :deep(.markdown-body code) {
  background: rgba(234, 179, 8, 0.12);
  color: #eab308;
}

.thinking-block :deep(.markdown-body strong) {
  color: #facc15;
  font-style: normal;
}

.content-block {
  margin: 4px 0;
}

.tool-calls {
  margin-bottom: 8px;
}

.edit-btn {
  margin-left: 8px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.chat-bubble.user:hover .edit-btn {
  opacity: 0.7;
}

.edit-btn:hover {
  opacity: 1 !important;
  background: rgba(255, 255, 255, 0.1);
}
</style>
