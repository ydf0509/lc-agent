<template>
  <header class="app-header">
    <div class="header-left">
      <el-button
        class="mobile-sidebar-btn"
        :icon="Menu"
        circle
        size="small"
        aria-label="打开会话列表"
        @click="$emit('openMobileSidebar')"
      />
      <span class="logo">⚡ lc_agent</span>
    </div>
    <div class="header-center">
      <el-select
        class="agent-select"
        :model-value="agentsStore.currentAgentId"
        size="small"
        @change="$emit('changeAgent', $event)"
      >
        <el-option
          v-for="agent in agentsStore.agents"
          :key="agent.id"
          :label="agent.name"
          :value="agent.id"
        >
          <div class="agent-option">
            <span>{{ agent.name }}</span>
            <span v-if="agent.source === 'builtin'" class="source-badge badge-builtin">内置</span>
            <span v-else-if="agent.source === 'code'" class="source-badge badge-code">代码</span>
            <span v-else class="source-badge badge-user">自建</span>
          </div>
        </el-option>
      </el-select>
      <button class="header-btn btn-edit" @click="$emit('editAgent')" :disabled="agentsStore.isBuiltin">编辑</button>
      <button class="header-btn btn-new-agent" @click="$emit('newAgent')">+ 新Agent</button>
      <button class="header-btn btn-new-chat" @click="$emit('newChat')">+ 新对话</button>
    </div>
    <div class="header-right">
      <el-button
        class="mobile-tools-btn"
        :icon="Setting"
        circle
        size="small"
        aria-label="打开工具和状态面板"
        @click="$emit('openMobileTools')"
      />
      <span class="model-badge">{{ modelName }}</span>
      <span class="status-dot" :class="connected ? 'connected' : 'disconnected'" />
      <span class="status-text" :title="connected ? 'WebSocket 已连接' : 'WebSocket 未连接'">
        {{ connected ? '已连接' : '未连接' }}
      </span>
      <el-button :icon="isDark ? Sunny : Moon" circle size="small" @click="toggleDark()" />
    </div>
  </header>
</template>

<script setup lang="ts">
import { useAgentsStore } from '@/stores/agents'
import { useTheme } from '@/composables/useTheme'
import { Sunny, Moon, Menu, Setting } from '@element-plus/icons-vue'

const agentsStore = useAgentsStore()
const { isDark, toggleDark } = useTheme()

defineProps<{
  modelName: string
  connected: boolean
}>()

defineEmits<{
  editAgent: []
  newAgent: []
  newChat: []
  changeAgent: [id: string]
  openMobileSidebar: []
  openMobileTools: []
}>()
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  height: 52px;
  flex-shrink: 0;
  z-index: 100;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-sidebar-btn,
.mobile-tools-btn {
  display: none;
}

.agent-select {
  width: 240px;
}

.model-badge {
  font-size: 12px;
  padding: 3px 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  color: var(--el-text-color-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected {
  background: var(--el-color-success);
  animation: pulse 2s infinite;
}

.status-dot.disconnected {
  background: var(--el-color-danger);
}

.status-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.agent-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.source-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.badge-builtin {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border: 1px solid var(--el-color-primary-light-5);
}

.badge-code {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
  border: 1px solid var(--el-color-warning-light-5);
}

.badge-user {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  border: 1px solid var(--el-color-success-light-5);
}

.header-btn {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.header-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-edit {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
  border: 1px solid var(--el-border-color);
}

.btn-edit:hover:not(:disabled) {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.btn-new-agent {
  background: var(--el-color-success);
  color: var(--el-color-white);
}

.btn-new-agent:hover {
  background: var(--el-color-success-light-3);
}

.btn-new-chat {
  background: var(--el-color-primary);
  color: var(--el-color-white);
  white-space: nowrap;
  flex-shrink: 0;
}

.btn-new-chat:hover {
  background: var(--el-color-primary-light-3);
}

@media (max-width: 900px) {
  .app-header {
    padding: 8px 10px;
    gap: 8px;
  }

  .mobile-sidebar-btn,
  .mobile-tools-btn {
    display: inline-flex;
    flex-shrink: 0;
  }

  .header-left,
  .header-right {
    flex-shrink: 0;
  }

  .header-center {
    flex: 1;
    justify-content: flex-end;
  }

  .agent-select {
    width: min(42vw, 220px);
  }

  .btn-edit,
  .btn-new-agent,
  .model-badge {
    display: none;
  }
}

@media (max-width: 520px) {
  .logo {
    font-size: 14px;
  }

  .agent-select {
    width: min(40vw, 160px);
  }

  .status-text {
    display: none;
  }

  .btn-new-chat {
    padding: 5px 8px;
  }
}

@media (max-width: 420px) {
  .logo {
    display: none;
  }

  .agent-select {
    width: min(46vw, 170px);
  }
}
</style>
