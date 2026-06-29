<template>
  <aside class="right-panel">
    <div class="right-panel-fixed">
      <div class="panel-section">
        <h4>模型</h4>
        <ModelSelector
          :models="toolsStore.models"
          :current-model="toolsStore.currentModel"
          @change="toolsStore.setModel"
        />
      </div>

      <div v-if="chatStore.todos.length > 0" class="panel-section">
        <TodoList :todos="chatStore.todos" />
      </div>
    </div>

    <div class="right-panel-scroll">
      <template v-if="!agentsStore.isChatAgent">
        <div class="panel-section">
          <h4>工具</h4>
          <ToolGroupPanel
            :groups="toolsStore.filteredGroups"
            @toggle="toolsStore.toggleGroup"
            @detail="(group) => openDetail('tool-group', group.description || group.id, group)"
          />
        </div>

        <div class="panel-section">
          <div class="section-header">
            <h4>MCP 服务器</h4>
            <button class="refresh-btn" type="button" :disabled="toolsStore.mcpRefreshing" @click="toolsStore.refreshMcpServers()">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                :class="{ spinning: toolsStore.mcpRefreshing }"
              >
                <path d="M21 2v6h-6" />
                <path d="M3 12a9 9 0 0 1 15.55-6.36L21 8" />
                <path d="M3 22v-6h6" />
                <path d="M21 12a9 9 0 0 1-15.55 6.36L3 16" />
              </svg>
              刷新
            </button>
          </div>
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
                <button class="detail-btn" type="button" @click="openDetail('mcp', server.name, server)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                  </svg>
                  详情
                </button>
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
              <button class="detail-btn" type="button" @click="openDetail('skill', skill.name, skill)">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                详情
              </button>
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
          <el-tag :type="chatStore.isConnected ? 'success' : 'warning'" size="small">
            {{ chatStore.isConnected ? '已连接' : '待连接' }}
          </el-tag>
        </div>
        <div v-if="chatStore.threadId" class="status-item">
          <span>Thread:</span>
          <code>{{ chatStore.threadId.slice(0, 8) }}...</code>
        </div>
      </div>
    </div>

    <DetailModal
      v-model:visible="detailModal.visible"
      :title="detailModal.title"
      :mode="detailModal.mode"
      :data="detailModal.data"
    />
  </aside>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useToolsStore } from '@/stores/tools'
import { api } from '@/api/http'
import { useChatStore } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import ModelSelector from '@/components/panels/ModelSelector.vue'
import ToolGroupPanel from '@/components/panels/ToolGroupPanel.vue'
import DetailModal from '@/components/panels/DetailModal.vue'
import TodoList from '@/components/panels/TodoList.vue'

const toolsStore = useToolsStore()
const chatStore = useChatStore()
const agentsStore = useAgentsStore()

const detailModal = reactive<{
  visible: boolean
  mode: 'tool-group' | 'mcp' | 'skill'
  title: string
  data: any
}>({
  visible: false,
  mode: 'tool-group',
  title: '',
  data: null,
})

async function openDetail(mode: 'tool-group' | 'mcp' | 'skill', title: string, data: any) {
  detailModal.mode = mode
  detailModal.title = title
  if (mode === 'skill' && data?.name && !data.body) {
    try {
      const detail = await api.getSkillDetail(data.name)
      detailModal.data = { ...data, ...detail }
    } catch {
      detailModal.data = data
    }
  } else {
    detailModal.data = data
  }
  detailModal.visible = true
}
</script>

<style scoped>
.right-panel {
  width: 350px;
  background: var(--el-bg-color);
  border-left: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel-fixed {
  flex-shrink: 0;
  padding: 16px 16px 0;
}

.right-panel-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px 16px;
}

.panel-section {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.panel-section h4 {
  margin: 0;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.7px;
  font-weight: 600;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color);
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  background: var(--el-bg-color);
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.18s ease;
}

.refresh-btn:hover:not(:disabled) {
  border-color: var(--el-color-primary-light-5);
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 6%, var(--el-bg-color));
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning {
  animation: spin 0.9s linear infinite;
}

.empty-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
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
  color: var(--el-text-color-secondary);
}

.mcp-item {
  margin-bottom: 8px;
  padding: 8px 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  transition: border-color 0.15s ease;
}

.mcp-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.mcp-item:has(.el-switch:not(.is-checked)) {
  opacity: 0.75;
  border: 1px dashed var(--el-color-warning-light-5) !important;
  background: var(--el-color-warning-light-9) !important;
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
  color: var(--el-color-danger);
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
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  transition: border-color 0.15s ease;
}

.skill-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.skill-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 10px;
  background: color-mix(in srgb, var(--el-color-primary) 8%, transparent);
  font-size: 11px;
  color: var(--el-color-primary);
  cursor: pointer;
  line-height: 1;
  flex-shrink: 0;
  transition: all 0.18s ease;
  white-space: nowrap;
}

.detail-btn:hover {
  background: color-mix(in srgb, var(--el-color-primary) 15%, transparent);
  border-color: var(--el-color-primary-light-3);
  box-shadow: 0 1px 4px color-mix(in srgb, var(--el-color-primary) 12%, transparent);
}

.detail-btn:active {
  transform: scale(0.95);
  background: color-mix(in srgb, var(--el-color-primary) 20%, transparent);
}

.skill-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-color-primary);
  transition: color 0.15s ease, opacity 0.15s ease;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
