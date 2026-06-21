<template>
  <div class="chat-input-wrapper">
    <div v-if="isEditing" class="edit-banner">
      <span>正在编辑上一条消息</span>
      <button type="button" class="cancel-edit-btn" @click="handleCancelEdit">取消</button>
    </div>
    <XSender
      ref="senderRef"
      :loading="isStreaming"
      :disabled="isInputDisabled"
      placeholder="Send a message..."
      submit-type="enter"
      clearable
      auto-focus
      @submit="handleSubmit"
      @cancel="handleStop"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { XSender } from 'vue-element-plus-x'
import { useChatStore } from '@/stores/chat'

const props = defineProps<{
  isStreaming?: boolean
  editContent?: string
  isEditing?: boolean
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

watch(() => props.editContent, async (content) => {
  await nextTick()
  content = content || ''
  senderRef.value?.setText(content)
  if (content) {
    senderRef.value?.focus('end')
  }
}, { immediate: true })

function handleSubmit() {
  const model = senderRef.value?.getModelValue()
  const text = model?.text ?? ''
  if (!text.trim()) return
  emit('send', text.trim())
  senderRef.value?.clear()
}

function handleStop() {
  emit('stop')
}

function handleCancelEdit() {
  senderRef.value?.clear()
  emit('cancelEdit')
}
</script>

<style scoped>
.chat-input-wrapper {
  padding: 10px 20px 14px;
  border-top: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
  box-sizing: border-box;
  flex-shrink: 0;
  position: relative;
  z-index: 120;
  width: 100%;
}

.chat-input-wrapper :deep(.elx-x-sender) {
  width: 100%;
  background: var(--el-bg-color-overlay) !important;
  border-color: var(--el-border-color) !important;
  border-radius: 8px;
}

.edit-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  padding: 7px 10px;
  border: 1px solid color-mix(in srgb, var(--el-color-success) 38%, var(--el-border-color));
  border-radius: 8px;
  background: color-mix(in srgb, var(--el-color-success) 12%, var(--el-bg-color-overlay));
  color: var(--el-text-color-primary);
  font-size: 12px;
}

.cancel-edit-btn {
  border: none;
  background: transparent;
  color: var(--el-color-success);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 4px;
}

.cancel-edit-btn:hover {
  color: var(--el-color-success-light-3);
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
