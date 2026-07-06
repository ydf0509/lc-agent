<template>
  <div class="sub-agent-card" :class="statusClass" @click="handleClick">
    <div class="sub-agent-header">
      <span class="sub-agent-icon">{{ statusIcon }}</span>
      <span class="sub-agent-title">子Agent: {{ subAgentId }}</span>
      <span class="sub-agent-status">{{ statusLabel }}</span>
    </div>
    <div class="sub-agent-task" v-if="taskDescription">
      <span class="task-label">任务:</span>
      <span class="task-text">{{ taskDescription }}</span>
    </div>
    <div class="sub-agent-summary" v-if="summary">
      <span class="summary-text">{{ summary }}</span>
    </div>
    <div class="sub-agent-hint" v-if="status === 'done'">
      <span>点击查看完整执行过程</span>
    </div>
    <div class="sub-agent-hint" v-else-if="status === 'running'">
      <span>子Agent执行中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  toolCall: any
}>()

const emit = defineEmits<{
  viewDetail: [toolCallId: string]
}>()

const subAgentId = computed(() => props.toolCall.subAgentId || '')
const taskDescription = computed(() => props.toolCall.taskDescription || '')
const summary = computed(() => props.toolCall.result || '')
const status = computed(() => props.toolCall.status || 'running')

const statusClass = computed(() => `sub-agent-${status.value}`)

const statusLabel = computed(() => {
  switch (status.value) {
    case 'running': return '执行中'
    case 'done': return '已完成'
    case 'error': return '失败'
    default: return '等待中'
  }
})

const statusIcon = computed(() => {
  switch (status.value) {
    case 'running': return '⏳'
    case 'done': return '✅'
    case 'error': return '❌'
    default: return '⏸'
  }
})

function handleClick() {
  if (status.value === 'done' || status.value === 'error') {
    emit('viewDetail', props.toolCall.runId)
  }
}
</script>

<style scoped>
.sub-agent-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 6px 0;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--el-fill-color-light);
}
.sub-agent-card:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.sub-agent-running {
  border-left: 3px solid var(--el-color-warning);
}
.sub-agent-done {
  border-left: 3px solid var(--el-color-success);
}
.sub-agent-error {
  border-left: 3px solid var(--el-color-danger);
}
.sub-agent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.sub-agent-icon {
  font-size: 14px;
}
.sub-agent-title {
  font-weight: 600;
  font-size: 13px;
  flex: 1;
}
.sub-agent-status {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
}
.sub-agent-task {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
  display: flex;
  gap: 4px;
}
.task-label {
  color: var(--el-text-color-placeholder);
  white-space: nowrap;
}
.task-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub-agent-summary {
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin-bottom: 2px;
}
.summary-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.sub-agent-hint {
  font-size: 11px;
  color: var(--el-color-primary);
  margin-top: 2px;
}
</style>