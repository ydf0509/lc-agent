<template>
  <el-dialog
    v-model="visible"
    title="⚠️ 工具需要审批"
    width="500px"
    :close-on-click-modal="false"
  >
    <div v-for="(action, idx) in interrupt?.actionRequests ?? []" :key="idx" class="action-item">
      <p><strong>工具:</strong> {{ action.name }}</p>
      <pre class="action-args">{{ JSON.stringify(action.arguments, null, 2) }}</pre>
    </div>

    <template #footer>
      <el-button @click="reject">拒绝</el-button>
      <el-button type="primary" @click="approve">批准执行</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InterruptInfo } from '@/stores/chat'

const props = defineProps<{ interrupt: InterruptInfo | null }>()
const emit = defineEmits<{ decide: [decision: { type: string; message?: string }] }>()

const visible = computed({
  get: () => props.interrupt !== null,
  set: () => {},
})

function approve() {
  emit('decide', { type: 'approve' })
}

function reject() {
  emit('decide', { type: 'reject', message: '用户拒绝了此操作' })
}
</script>

<style scoped>
.action-item {
  margin-bottom: 14px;
  padding: 12px;
  background: var(--lc-glass-bg);
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-md);
}

.action-args {
  background: rgba(0, 0, 0, 0.25);
  padding: 10px;
  border-radius: var(--lc-radius-sm);
  font-size: 12px;
  overflow-x: auto;
  margin-top: 8px;
  border: 1px solid var(--lc-glass-border);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
</style>
