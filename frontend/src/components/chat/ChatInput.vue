<template>
  <div class="chat-input-wrapper">
    <div v-if="isEditing" class="edit-hint">
      <span class="edit-hint-text">✏️ 编辑消息中</span>
      <button class="edit-cancel-btn" @click="cancelEdit">取消</button>
    </div>
    <div class="input-row">
      <div class="input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :placeholder="isStreaming ? 'AI 正在回复...' : '输入消息... (Enter发送, Shift+Enter换行)'"
          :autosize="{ minRows: 2, maxRows: 8 }"
          @keydown="handleKeydown"
        />
      </div>
      <div class="input-actions">
        <button
          v-if="isStreaming"
          class="action-btn btn-stop"
          @click="$emit('stop')"
        >
          <span class="btn-icon">■</span>
          停止
        </button>
        <button
          v-else
          class="action-btn btn-send"
          :disabled="!inputText.trim()"
          @click="send"
        >
          <span class="btn-icon">↑</span>
          {{ isEditing ? '重发' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = defineProps<{
  isStreaming: boolean
  editContent?: string
}>()
const emit = defineEmits<{
  send: [content: string]
  stop: []
  cancelEdit: []
}>()

const inputText = ref('')
const isEditing = computed(() => !!props.editContent)

watch(() => props.editContent, (val) => {
  if (val !== undefined && val !== '') {
    inputText.value = val
  }
})

function send() {
  if (!inputText.value.trim()) return
  emit('send', inputText.value)
  inputText.value = ''
}

function cancelEdit() {
  inputText.value = ''
  emit('cancelEdit')
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (props.isStreaming) return
    send()
  }
  if (e.key === 'Escape' && isEditing.value) {
    cancelEdit()
  }
}
</script>

<style scoped>
.chat-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 10px 20px 14px;
  background: var(--lc-glass-bg);
  border-top: 1px solid var(--lc-glass-border);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.edit-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0 8px;
}

.edit-hint-text {
  font-size: 12px;
  color: #f0883e;
  font-weight: 500;
}

.edit-cancel-btn {
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid #30363d;
  border-radius: 4px;
  background: transparent;
  color: #8b949e;
  cursor: pointer;
  transition: all 0.15s;
}

.edit-cancel-btn:hover {
  color: #f85149;
  border-color: #f85149;
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.input-area {
  flex: 1;
}

.input-area .el-textarea {
  width: 100%;
}

.input-area :deep(.el-textarea__inner) {
  background: transparent !important;
  color: var(--lc-text-primary);
  font-size: 14px;
  line-height: 1.6;
}

.input-actions {
  display: flex;
  align-items: center;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-icon {
  font-size: 14px;
}

.btn-send {
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  box-shadow: 0 2px 8px rgba(46, 160, 67, 0.3);
}

.btn-send:hover:not(:disabled) {
  background: linear-gradient(135deg, #2ea043, #3fb950);
  box-shadow: 0 4px 12px rgba(46, 160, 67, 0.4);
  transform: translateY(-1px);
}

.btn-send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-stop {
  background: linear-gradient(135deg, #da3633, #f85149);
  color: #fff;
  box-shadow: 0 2px 8px rgba(248, 81, 73, 0.3);
  animation: pulse-stop 1.5s ease-in-out infinite;
}

.btn-stop:hover {
  background: linear-gradient(135deg, #f85149, #ff7b72);
  box-shadow: 0 4px 12px rgba(248, 81, 73, 0.5);
  transform: translateY(-1px);
}

@keyframes pulse-stop {
  0%, 100% { box-shadow: 0 2px 8px rgba(248, 81, 73, 0.3); }
  50% { box-shadow: 0 2px 16px rgba(248, 81, 73, 0.6); }
}
</style>
