<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">⚡ lc_agent</span>
    </div>
    <div class="header-center">
      <span class="current-agent">{{ agentName }}</span>
      <el-tag size="small" type="info">{{ modelName }}</el-tag>
    </div>
    <div class="header-right">
      <el-tag size="small" :type="connected ? 'success' : 'danger'" effect="dark">
        {{ connected ? '已连接' : '未连接' }}
      </el-tag>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  agentName: string
  modelName: string
  connected: boolean
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

.current-agent {
  font-weight: 500;
}
</style>
