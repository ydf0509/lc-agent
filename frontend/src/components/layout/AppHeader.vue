<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">⚡ lc_agent</span>
    </div>
    <div class="header-center">
      <el-select
        :model-value="agentsStore.currentAgentId"
        size="small"
        style="width: 240px"
        @change="agentsStore.selectAgent"
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
      <span class="model-badge">{{ modelName }}</span>
      <span class="status-dot" :class="connected ? 'connected' : 'disconnected'" />
      <span class="status-text">{{ connected ? '已连接' : '未连接' }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useAgentsStore } from '@/stores/agents'

const agentsStore = useAgentsStore()

defineProps<{
  modelName: string
  connected: boolean
}>()

defineEmits<{
  editAgent: []
  newAgent: []
  newChat: []
}>()
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: var(--lc-glass-bg);
  backdrop-filter: blur(var(--lc-glass-blur-heavy));
  -webkit-backdrop-filter: blur(var(--lc-glass-blur-heavy));
  border-bottom: 1px solid var(--lc-glass-border);
  height: 52px;
  z-index: 100;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  background: var(--lc-gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.model-badge {
  font-size: 12px;
  padding: 3px 10px;
  background: var(--lc-glass-bg-hover);
  border: 1px solid var(--lc-glass-border);
  border-radius: 12px;
  color: var(--lc-text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected {
  background: var(--lc-success);
  box-shadow: 0 0 8px rgba(63, 185, 80, 0.5);
  animation: pulse 2s infinite;
}

.status-dot.disconnected {
  background: var(--lc-danger);
}

.status-text {
  font-size: 12px;
  color: var(--lc-text-secondary);
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
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
  border: 1px solid rgba(88, 166, 255, 0.3);
}

.badge-code {
  background: rgba(255, 180, 50, 0.15);
  color: #ffb832;
  border: 1px solid rgba(255, 180, 50, 0.3);
}

.badge-user {
  background: rgba(63, 185, 80, 0.15);
  color: #6ee77a;
  border: 1px solid rgba(63, 185, 80, 0.3);
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
  background: #21262d;
  color: #c9d1d9;
  border: 1px solid #30363d;
}

.btn-edit:hover:not(:disabled) {
  background: #30363d;
  color: #e6edf3;
}

.btn-new-agent {
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #ffffff;
}

.btn-new-agent:hover {
  background: linear-gradient(135deg, #2ea043, #3fb950);
  box-shadow: 0 2px 8px rgba(46, 160, 67, 0.3);
}

.btn-new-chat {
  background: linear-gradient(135deg, #1f6feb, #388bfd);
  color: #ffffff;
}

.btn-new-chat:hover {
  background: linear-gradient(135deg, #388bfd, #58a6ff);
  box-shadow: 0 2px 8px rgba(56, 139, 253, 0.3);
}
</style>
