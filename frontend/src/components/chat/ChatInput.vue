<template>
  <div class="chat-input-wrapper">
    <XSender
      ref="senderRef"
      :loading="isStreaming"
      :disabled="isInputDisabled"
      placeholder="Send a message..."
      submit-type="enter"
      clearable
      auto-focus
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { XSender } from 'vue-element-plus-x'
import { useChatStore } from '@/stores/chat'

defineProps<{
  isStreaming?: boolean
  editContent?: string
}>()

const emit = defineEmits<{
  send: [content: string]
  stop: []
  cancelEdit: []
}>()

const chatStore = useChatStore()
const { isStreaming } = storeToRefs(chatStore)
const senderRef = ref<InstanceType<typeof XSender>>()
const isInputDisabled = computed(() => isStreaming.value)

function handleSubmit() {
  const model = senderRef.value?.getModelValue()
  const text = model?.text ?? ''
  if (!text.trim()) return
  emit('send', text.trim())
  senderRef.value?.clear()
}
</script>

<style scoped>
.chat-input-wrapper {
  padding: 10px 20px 14px;
  border-top: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
  box-sizing: border-box;
  flex-shrink: 0;
  width: 100%;
}

.chat-input-wrapper :deep(.elx-x-sender) {
  width: 100%;
  background: var(--el-bg-color-overlay) !important;
  border-color: var(--el-border-color) !important;
  border-radius: 8px;
}

.chat-input-wrapper :deep(.chat-rich-text) {
  background: transparent !important;
}

.chat-input-wrapper :deep([contenteditable="true"]) {
  color: var(--el-text-color-primary) !important;
}

.chat-input-wrapper :deep([contenteditable="true"] p),
.chat-input-wrapper :deep([contenteditable="true"] span) {
  color: inherit !important;
}

.chat-input-wrapper :deep(.elx-x-sender__chat) {
  background: transparent !important;
}

.chat-input-wrapper :deep(.chat-grid-wrap) {
  color: var(--el-text-color-primary) !important;
}

@media (max-width: 520px) {
  .chat-input-wrapper {
    padding: 8px 10px 10px;
  }

  .chat-input-wrapper :deep(.elx-x-sender) {
    border-radius: 10px;
  }

  .chat-input-wrapper :deep([contenteditable="true"]) {
    min-height: 22px;
  }
}
</style>
