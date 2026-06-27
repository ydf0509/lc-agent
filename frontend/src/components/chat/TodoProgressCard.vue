<template>
  <div class="todo-progress-card" :class="{ expanded: isExpanded }" @click="isExpanded = !isExpanded">
    <div class="todo-compact">
      <span class="todo-status-icon" :class="{ spinning: hasInProgress }">
        {{ hasInProgress ? '◉' : allCompleted ? '✓' : '○' }}
      </span>
      <span class="todo-current-label">{{ currentLabel }}</span>
      <span class="todo-progress-badge">{{ completed }}/{{ totalCount }}</span>
      <div class="todo-mini-bar">
        <div class="todo-mini-fill" :style="{ width: percentage + '%' }" />
      </div>
      <span class="todo-expand-icon">{{ isExpanded ? '▾' : '▸' }}</span>
    </div>

    <ul v-if="isExpanded" class="todo-full-list" @click.stop>
      <li
        v-for="(todo, idx) in todoItems"
        :key="idx"
        class="todo-row"
        :class="'status-' + todo.status"
      >
        <span class="row-icon">{{ statusIcon(todo.status) }}</span>
        <span class="row-text">{{ todo.content }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ToolCall } from '@/stores/chat'

const props = defineProps<{ toolCall: ToolCall }>()

const isExpanded = ref(false)

interface TodoEntry {
  content: string
  status: 'pending' | 'in_progress' | 'completed'
}

const todoItems = computed((): TodoEntry[] => {
  const args = props.toolCall.args
  if (!args || !Array.isArray(args.todos)) return []
  return args.todos as TodoEntry[]
})

const totalCount = computed(() => todoItems.value.length)
const completed = computed(() => todoItems.value.filter(t => t.status === 'completed').length)
const hasInProgress = computed(() => todoItems.value.some(t => t.status === 'in_progress'))
const allCompleted = computed(() => totalCount.value > 0 && completed.value === totalCount.value)
const percentage = computed(() =>
  totalCount.value ? Math.round((completed.value / totalCount.value) * 100) : 0,
)

const currentLabel = computed(() => {
  const inProgress = todoItems.value.find(t => t.status === 'in_progress')
  if (inProgress) return inProgress.content
  if (allCompleted.value) return '全部完成'
  const nextPending = todoItems.value.find(t => t.status === 'pending')
  return nextPending?.content || '任务进度'
})

function statusIcon(status: string) {
  switch (status) {
    case 'completed': return '✓'
    case 'in_progress': return '◉'
    default: return '○'
  }
}
</script>

<style scoped>
.todo-progress-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 10px 14px;
  margin: 8px 0;
  background: var(--el-fill-color-blank);
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  user-select: none;
}

.todo-progress-card:hover {
  border-color: var(--el-border-color);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.todo-progress-card.expanded {
  border-color: var(--el-color-primary-light-5);
}

.todo-compact {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.todo-status-icon {
  font-size: 14px;
  flex-shrink: 0;
  color: var(--el-color-warning);
}

.todo-status-icon.spinning {
  animation: pulse 1.5s ease-in-out infinite;
}

.todo-current-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.todo-progress-badge {
  flex-shrink: 0;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 9px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.todo-mini-bar {
  width: 48px;
  height: 4px;
  border-radius: 2px;
  background: var(--el-fill-color-light);
  overflow: hidden;
  flex-shrink: 0;
}

.todo-mini-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--el-color-success);
  transition: width 0.4s ease;
}

.todo-expand-icon {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
}

.todo-full-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: default;
}

.todo-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  border: 1px solid transparent;
}

.row-icon {
  flex-shrink: 0;
  width: 16px;
  text-align: center;
  margin-top: 1px;
}

.row-text {
  flex: 1;
  word-break: break-word;
}

.status-pending {
  color: var(--el-text-color-secondary);
}
.status-pending .row-icon {
  color: var(--el-text-color-placeholder);
}

.status-in_progress {
  background: var(--el-color-warning-light-9);
  border-color: var(--el-color-warning-light-7);
  color: var(--el-color-warning-dark-2);
}
.status-in_progress .row-icon {
  color: var(--el-color-warning);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-completed {
  color: var(--el-color-success-dark-2);
}
.status-completed .row-text {
  text-decoration: line-through;
  opacity: 0.7;
}
.status-completed .row-icon {
  color: var(--el-color-success);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
