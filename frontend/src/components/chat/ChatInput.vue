<template>
  <div class="chat-input-wrapper">
    <el-input
      v-model="inputText"
      type="textarea"
      :placeholder="isStreaming ? 'AI 正在回复...' : '输入消息... (Enter发送, Shift+Enter换行)'"
      :autosize="{ minRows: 2, maxRows: 8 }"
      :disabled="isStreaming"
      @keydown="handleKeydown"
    />
    <el-button
      type="primary"
      :disabled="!inputText.trim() || isStreaming"
      :loading="isStreaming"
      @click="send"
    >
      发送
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ isStreaming: boolean }>()
const emit = defineEmits<{ send: [content: string] }>()

const inputText = ref('')

function send() {
  if (!inputText.value.trim() || props.isStreaming) return
  emit('send', inputText.value)
  inputText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<style scoped>
.chat-input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 12px 16px;
  border-top: 1px solid var(--lc-border);
  background: var(--lc-bg-secondary);
}

.chat-input-wrapper .el-textarea {
  flex: 1;
}
</style>
