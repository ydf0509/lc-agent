<template>
  <aside class="right-panel">
    <div class="panel-section">
      <h4>模型</h4>
      <ModelSelector
        :models="toolsStore.models"
        :current-model="toolsStore.currentModel"
        @change="toolsStore.setModel"
      />
    </div>

    <div class="panel-section">
      <h4>工具</h4>
      <ToolGroupPanel
        :groups="toolsStore.groups"
        @toggle="toolsStore.toggleGroup"
      />
    </div>

    <div class="panel-section">
      <h4>MCP</h4>
      <p class="empty-hint">暂无 MCP 服务器</p>
    </div>

    <div class="panel-section">
      <h4>Skills</h4>
      <p class="empty-hint">暂无 Skills</p>
    </div>

    <div class="panel-section status-section">
      <h4>状态</h4>
      <div class="status-item">
        <span>连接:</span>
        <el-tag :type="chatStore.isConnected ? 'success' : 'danger'" size="small">
          {{ chatStore.isConnected ? '已连接' : '未连接' }}
        </el-tag>
      </div>
      <div v-if="chatStore.threadId" class="status-item">
        <span>Thread:</span>
        <code>{{ chatStore.threadId.slice(0, 8) }}...</code>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useToolsStore } from '@/stores/tools'
import { useChatStore } from '@/stores/chat'
import ModelSelector from '@/components/panels/ModelSelector.vue'
import ToolGroupPanel from '@/components/panels/ToolGroupPanel.vue'

const toolsStore = useToolsStore()
const chatStore = useChatStore()
</script>

<style scoped>
.right-panel {
  width: 280px;
  background: var(--lc-bg-secondary);
  border-left: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 16px;
}

.panel-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.empty-hint {
  font-size: 12px;
  color: var(--lc-text-secondary);
  margin: 4px 0;
}

.status-section .status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}

.status-section code {
  font-size: 11px;
  color: var(--lc-text-secondary);
}
</style>
