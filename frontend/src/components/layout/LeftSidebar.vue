<template>
  <aside class="left-sidebar">
    <div class="sidebar-section">
      <el-button type="primary" size="small" style="width:100%" @click="$emit('newChat')">
        + 新对话
      </el-button>
    </div>
    <div class="sidebar-section">
      <h4>会话历史</h4>
      <div class="session-list">
        <div
          v-for="session in sessionsStore.sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === sessionsStore.currentSessionId }"
          @click="$emit('switchSession', session.id)"
        >
          <span class="session-title">{{ session.title }}</span>
          <span class="session-time">{{ formatTime(session.updated_at) }}</span>
        </div>
        <p v-if="!sessionsStore.sessions.length" class="empty-hint">暂无会话</p>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useSessionsStore } from '@/stores/sessions'

const sessionsStore = useSessionsStore()

defineEmits<{ newChat: []; switchSession: [id: string] }>()

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}
</script>

<style scoped>
.left-sidebar {
  width: 240px;
  background: var(--lc-bg-secondary);
  border-right: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 16px;
}

.sidebar-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--lc-text-primary);
}

.session-item:hover {
  background: var(--lc-bg-tertiary);
}

.session-item.active {
  background: var(--lc-bg-tertiary);
  border-left: 2px solid var(--lc-accent);
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}

.session-time {
  font-size: 11px;
  color: var(--lc-text-secondary);
  flex-shrink: 0;
}

.empty-hint {
  font-size: 12px;
  color: var(--lc-text-secondary);
  text-align: center;
  padding: 12px;
}
</style>
