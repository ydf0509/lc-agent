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
      <h4>MCP 服务器</h4>
      <div v-for="server in toolsStore.mcpServers" :key="server.name" class="mcp-item">
        <div class="mcp-header">
          <span class="mcp-name">{{ server.name }}</span>
          <el-tag size="small" :type="server.status === 'connected' ? 'success' : server.status === 'error' ? 'danger' : 'info'">
            {{ server.status === 'connected' ? '已连接' : server.status === 'error' ? '错误' : '未连接' }}
          </el-tag>
        </div>
        <div v-if="server.tools.length" class="mcp-tools">
          <el-tag v-for="tool in server.tools" :key="tool" size="small" type="info">{{ tool }}</el-tag>
        </div>
      </div>
      <p v-if="!toolsStore.mcpServers.length" class="empty-hint">暂无 MCP 服务器</p>
    </div>

    <div class="panel-section">
      <h4>Skills</h4>
      <div v-for="skill in toolsStore.skills" :key="skill.name" class="skill-item">
        <span class="skill-name">{{ skill.name }}</span>
        <span class="skill-desc">{{ skill.description }}</span>
      </div>
      <p v-if="!toolsStore.skills.length" class="empty-hint">暂无 Skills</p>
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

.mcp-item {
  margin-bottom: 8px;
  padding: 6px 8px;
  background: var(--lc-bg-tertiary);
  border-radius: 6px;
}

.mcp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mcp-name {
  font-size: 13px;
  font-weight: 500;
}

.mcp-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.skill-item {
  display: flex;
  flex-direction: column;
  padding: 6px 8px;
  margin-bottom: 4px;
  background: var(--lc-bg-tertiary);
  border-radius: 6px;
}

.skill-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--lc-accent);
}

.skill-desc {
  font-size: 11px;
  color: var(--lc-text-secondary);
  margin-top: 2px;
}
</style>
