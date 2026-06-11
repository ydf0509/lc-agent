<template>
  <div class="chat-bubble" :class="[message.role, { streaming: message.isStreaming }]">
    <div class="bubble-avatar">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="bubble-content">
      <div v-if="message.role === 'assistant'" class="markdown-body" v-html="renderedContent" />
      <div v-else class="plain-text">{{ message.content }}</div>

      <div v-if="message.toolCalls?.length" class="tool-calls">
        <ToolCallCard
          v-for="(tc, idx) in message.toolCalls"
          :key="idx"
          :tool-call="tc"
        />
      </div>

      <span v-if="message.isStreaming" class="streaming-cursor">▊</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import ToolCallCard from './ToolCallCard.vue'
import type { ChatMessage } from '@/stores/chat'

const props = defineProps<{ message: ChatMessage }>()

const renderedContent = computed(() => renderMarkdown(props.message.content))
</script>

<style scoped>
.chat-bubble {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.chat-bubble.user {
  background: var(--lc-bg-tertiary);
}

.chat-bubble.assistant {
  background: transparent;
}

.bubble-avatar {
  font-size: 20px;
  flex-shrink: 0;
}

.bubble-content {
  flex: 1;
  overflow-wrap: break-word;
  line-height: 1.6;
}

.streaming-cursor {
  animation: blink 1s infinite;
  color: var(--lc-accent);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.tool-calls {
  margin-top: 8px;
}
</style>
