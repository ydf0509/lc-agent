<template>
  <div v-if="todos.length > 0" class="todo-panel">
    <div class="todo-header">
      <span class="todo-title">任务进度</span>
      <span class="todo-counter">{{ completed }}/{{ todos.length }}</span>
    </div>

    <div class="todo-progress-bar">
      <div class="todo-progress-fill" :style="{ width: percentage + '%' }" />
    </div>

    <ul class="todo-list">
      <li
        v-for="(todo, idx) in todos"
        :key="idx"
        class="todo-item"
        :class="'todo-' + todo.status"
      >
        <span class="todo-icon">{{ statusIcon(todo.status) }}</span>
        <span class="todo-content">{{ todo.content }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TodoItem } from '@/stores/chat'

const props = defineProps<{ todos: TodoItem[] }>()

const completed = computed(() => props.todos.filter(t => t.status === 'completed').length)
const percentage = computed(() =>
  props.todos.length ? Math.round((completed.value / props.todos.length) * 100) : 0,
)

function statusIcon(status: string) {
  switch (status) {
    case 'completed': return '✓'
    case 'in_progress': return '◉'
    default: return '○'
  }
}
</script>

<style scoped>
.todo-panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-bg-color);
}

.todo-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.todo-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.todo-counter {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.todo-progress-bar {
  height: 4px;
  border-radius: 2px;
  background: var(--el-fill-color-light);
  margin-bottom: 10px;
  overflow: hidden;
}

.todo-progress-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--el-color-success);
  transition: width 0.4s ease;
}

.todo-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  border: 1px solid transparent;
}

.todo-icon {
  flex-shrink: 0;
  width: 16px;
  text-align: center;
  margin-top: 1px;
}

.todo-content {
  flex: 1;
  word-break: break-word;
}

.todo-pending {
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-secondary);
}
.todo-pending .todo-icon {
  color: var(--el-text-color-placeholder);
}

.todo-in_progress {
  background: var(--el-color-warning-light-9);
  border-color: var(--el-color-warning-light-7);
  color: var(--el-color-warning-dark-2);
}
.todo-in_progress .todo-icon {
  color: var(--el-color-warning);
  animation: pulse 1.5s ease-in-out infinite;
}

.todo-completed {
  background: var(--el-color-success-light-9);
  border-color: var(--el-color-success-light-7);
  color: var(--el-color-success-dark-2);
}
.todo-completed .todo-content {
  text-decoration: line-through;
  opacity: 0.7;
}
.todo-completed .todo-icon {
  color: var(--el-color-success);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
