<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">⚡ lc_agent</span>
    </div>
    <div class="header-center">
      <el-select
        :model-value="agentsStore.currentAgentId"
        size="small"
        style="width: 200px"
        @change="agentsStore.selectAgent"
      >
        <el-option
          v-for="agent in agentsStore.agents"
          :key="agent.id"
          :label="agent.name"
          :value="agent.id"
        />
      </el-select>
      <el-button size="small" @click="$emit('editAgent')">
        编辑
      </el-button>
      <el-button size="small" type="primary" @click="$emit('newAgent')">
        + 新Agent
      </el-button>
    </div>
    <div class="header-right">
      <el-tag size="small" type="info">{{ modelName }}</el-tag>
      <el-tag size="small" :type="connected ? 'success' : 'danger'" effect="dark">
        {{ connected ? '已连接' : '未连接' }}
      </el-tag>
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
}>()
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--lc-bg-secondary);
  border-bottom: 1px solid var(--lc-border);
  height: 48px;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--lc-accent);
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
