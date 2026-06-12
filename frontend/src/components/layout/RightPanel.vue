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

    <template v-if="!agentsStore.isChatAgent">
      <div class="panel-section">
        <h4>工具</h4>
        <ToolGroupPanel
          :groups="toolsStore.filteredGroups"
          @toggle="toolsStore.toggleGroup"
        />
      </div>

      <div class="panel-section">
        <h4>MCP 服务器</h4>
        <div v-for="server in toolsStore.filteredMcp" :key="server.name" class="mcp-item" :class="{ 'not-allowed': !server.allowed }">
          <div class="mcp-header">
            <div class="mcp-left">
              <el-switch
                :model-value="server.enabled"
                :disabled="!server.allowed"
                size="small"
                @change="toolsStore.toggleMcp(server.name)"
              />
              <span class="mcp-name">{{ server.name }}</span>
            </div>
            <el-tag size="small" :type="!server.allowed ? 'warning' : server.status === 'connected' ? 'success' : server.status === 'error' ? 'danger' : server.status === 'disabled' ? 'warning' : 'info'">
              {{ !server.allowed ? '未授权' : server.status === 'connected' ? '已连接' : server.status === 'error' ? '错误' : server.status === 'disabled' ? '已禁用' : '未连接' }}
            </el-tag>
          </div>
          <div v-if="server.error && server.allowed" class="mcp-error">{{ server.error }}</div>
          <div v-if="server.tools && server.tools.length && server.allowed" class="mcp-tools">
            <el-tag v-for="tool in server.tools.slice(0, 5)" :key="tool" size="small" :class="server.enabled ? 'tool-tag-enabled' : 'tool-tag-disabled'">{{ tool }}</el-tag>
            <el-tag v-if="server.tools.length > 5" size="small" :class="server.enabled ? 'tool-tag-enabled' : 'tool-tag-disabled'">+{{ server.tools.length - 5 }}</el-tag>
          </div>
        </div>
        <p v-if="!toolsStore.mcpServers.length" class="empty-hint">暂无 MCP 服务器</p>
      </div>

      <div class="panel-section">
        <h4>Skills</h4>
        <div v-for="skill in toolsStore.filteredSkills" :key="skill.name" class="skill-item" :class="{ 'not-allowed': !skill.allowed, 'skill-disabled': !skill.enabled }">
          <div class="skill-header">
            <el-switch
              :model-value="skill.enabled"
              :disabled="!skill.allowed"
              size="small"
              @change="toolsStore.toggleSkill(skill.name)"
            />
            <span class="skill-name" :class="{ dimmed: !skill.enabled }">{{ skill.name }}</span>
          </div>
          <span class="skill-desc">{{ skill.description }}</span>
        </div>
        <p v-if="!toolsStore.skills.length" class="empty-hint">暂无 Skills</p>
      </div>
    </template>

    <div v-if="agentsStore.isChatAgent" class="panel-section chat-only-hint">
      <div class="hint-box">
        <span class="hint-icon">💬</span>
        <span class="hint-text">Chat 模式：纯对话，无工具</span>
        <span class="hint-sub">切换至 Empty 或 Power 智能体以启用工具</span>
      </div>
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
import { useAgentsStore } from '@/stores/agents'
import ModelSelector from '@/components/panels/ModelSelector.vue'
import ToolGroupPanel from '@/components/panels/ToolGroupPanel.vue'

const toolsStore = useToolsStore()
const chatStore = useChatStore()
const agentsStore = useAgentsStore()
</script>

<style scoped>
.right-panel {
  width: 420px;
  background: var(--lc-glass-bg);
  backdrop-filter: blur(var(--lc-glass-blur));
  -webkit-backdrop-filter: blur(var(--lc-glass-blur));
  border-left: 1px solid var(--lc-glass-border);
  padding: 14px;
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--lc-glass-bg);
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-md);
}

.panel-section h4 {
  margin: 0 0 10px;
  font-size: 11px;
  color: var(--lc-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.7px;
  font-weight: 600;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--lc-glass-border);
}

.empty-hint {
  font-size: 12px;
  color: var(--lc-text-secondary);
  margin: 4px 0;
  opacity: 0.6;
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
  padding: 8px 10px;
  background: var(--lc-glass-bg-hover);
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-sm);
  transition: border-color var(--lc-transition-fast);
}

.mcp-item:hover {
  border-color: var(--lc-glass-border-hover);
}

.mcp-item:has(.el-switch:not(.is-checked)) {
  opacity: 0.75;
  border: 1px dashed rgba(255, 180, 80, 0.35) !important;
  background: rgba(255, 170, 50, 0.04) !important;
}

.mcp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mcp-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mcp-error {
  font-size: 11px;
  color: var(--lc-danger);
  margin-top: 4px;
  word-break: break-all;
  opacity: 0.8;
}

.mcp-name {
  font-size: 13px;
  font-weight: 500;
}

.mcp-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.skill-item {
  padding: 8px 10px;
  margin-bottom: 4px;
  background: var(--lc-glass-bg-hover);
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-sm);
  transition: border-color var(--lc-transition-fast);
}

.skill-item:hover {
  border-color: var(--lc-glass-border-hover);
}

.skill-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.skill-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--lc-accent);
  transition: color var(--lc-transition-fast), opacity var(--lc-transition-fast);
}

.skill-name.dimmed {
  color: var(--lc-text-secondary);
  opacity: 0.6;
}

.skill-disabled {
  opacity: 0.75;
  border: 1px dashed rgba(255, 180, 80, 0.4) !important;
  background: rgba(255, 170, 50, 0.05) !important;
}

.skill-disabled .skill-name {
  color: rgba(255, 200, 100, 0.85) !important;
  text-decoration: line-through;
}

.skill-desc {
  font-size: 11px;
  color: var(--lc-text-secondary);
  margin-top: 3px;
  opacity: 0.8;
}

.not-allowed {
  opacity: 0.4;
}

.chat-only-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hint-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  text-align: center;
}

.hint-icon {
  font-size: 32px;
}

.hint-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--lc-text-primary);
}

.hint-sub {
  font-size: 12px;
  color: var(--lc-text-secondary);
  opacity: 0.7;
}
</style>
