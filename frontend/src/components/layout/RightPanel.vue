﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <aside
    class="right-panel"
    :class="{ collapsed }"
    :style="!collapsed && panelWidth !== undefined ? { width: panelWidth + 'px' } : {}"
  >
    <button
      v-if="collapsed"
      type="button"
      class="toggle-btn rail-toggle"
      title="展开右侧面板"
      @click="emit('toggle-collapse')"
    >
      <span class="toggle-icon">«</span>
    </button>

    <div v-else class="right-panel-body">
      <div class="right-panel-topbar">
        <button
          type="button"
          class="toggle-btn"
          title="收起右侧面板"
          @click="emit('toggle-collapse')"
        >
          <span class="toggle-icon">»</span>
        </button>

        <div class="right-panel-tabs" role="tablist" aria-label="右侧面板分区">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            role="tab"
            class="panel-tab"
            :class="{ active: activeTab === tab.id }"
            :aria-selected="activeTab === tab.id"
            :title="tab.label"
            @click="uiStore.setActiveTab(tab.id)"
          >
            <el-icon class="panel-tab-icon"><component :is="tab.icon" /></el-icon>
            <span class="panel-tab-label">{{ tab.label }}</span>
            <span v-if="tab.badge > 0" class="panel-tab-badge" :class="{ 'is-dirty': tab.id === 'editor' && dirtyFileCount > 0 }">{{ tab.badge }}</span>
          </button>
        </div>
      </div>

      <div class="right-panel-scroll" :class="{ 'is-editor': activeTab === 'editor' }">
        <transition name="fade-up" mode="out-in">
        <div :key="activeTab" class="tab-pane">

          <template v-if="activeTab === 'model'">
            <template v-if="!agentsStore.isCodeAgent">
              <div class="panel-section">
                <h4>模型</h4>
                <ModelSelector
                  :models="toolsStore.models"
                  :current-model="toolsStore.currentModel"
                  @change="toolsStore.setModel"
                />
                <div class="llm-params-controls">
                  <div class="param-row">
                    <div class="param-label-group">
                      <span class="param-label">思考级别</span>
                      <span v-if="reasoningFromPreset" class="param-source-hint">预设</span>
                      <span v-else-if="hasReasoningOverride" class="param-source-hint override">覆盖</span>
                    </div>
                    <div class="param-control-group">
                      <el-select
                        :model-value="effectiveReasoningEffort ?? 'default'"
                        size="small"
                        class="reasoning-effort-select"
                        @update:model-value="(v: string) => toolsStore.setLlmParam('reasoning_effort', v === 'default' ? null : v)"
                      >
                        <el-option
                          v-for="effort in ['default', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']"
                          :key="effort"
                          :label="effort"
                          :value="effort"
                        />
                      </el-select>
                      <button
                        v-if="hasReasoningOverride"
                        class="param-reset-btn"
                        type="button"
                        title="清除覆盖，恢复预设/默认"
                        @click="toolsStore.setLlmParam('reasoning_effort', null)"
                      >×</button>
                    </div>
                  </div>
                  <div class="param-row param-row-slider">
                    <div class="param-label-group">
                      <span class="param-label">温度</span>
                      <span v-if="temperatureFromPreset" class="param-source-hint">预设</span>
                      <span v-else-if="hasTemperatureOverride" class="param-source-hint override">覆盖</span>
                    </div>
                    <div class="temperature-control">
                      <el-slider
                        :model-value="effectiveTemperature"
                        :min="0"
                        :max="2"
                        :step="0.1"
                        size="small"
                        class="temperature-slider"
                        @update:model-value="(v: number) => toolsStore.setLlmParam('temperature', v)"
                      />
                      <el-input-number
                        :model-value="effectiveTemperature"
                        :min="0"
                        :max="2"
                        :step="0.1"
                        :precision="1"
                        size="small"
                        controls-position="right"
                        class="temperature-input"
                        @update:model-value="(v: number | undefined) => toolsStore.setLlmParam('temperature', v ?? null)"
                      />
                      <button
                        v-if="hasTemperatureOverride"
                        class="param-reset-btn"
                        type="button"
                        title="清除覆盖，恢复预设/默认"
                        @click="toolsStore.setLlmParam('temperature', null)"
                      >×</button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="panel-section window-trim-section">
                <div class="window-trim-control">
                  <h4>窗口裁剪模型</h4>
                  <el-switch
                    :model-value="summEnabled"
                    size="small"
                    @change="(val: boolean) => { summEnabled = val; updateSummarization({ enabled: val }) }"
                  />
                </div>
                <el-select
                  v-if="summEnabled"
                  v-model="summModel"
                  placeholder="默认同主模型"
                  size="small"
                  filterable
                  clearable
                  class="window-trim-select"
                  @change="updateSummarization({ default_model: $event || '' })"
                >
                  <el-option
                    v-for="model in toolsStore.models"
                    :key="model.model_id"
                    :label="model.model_id"
                    :value="model.model_id"
                  />
                </el-select>
              </div>
            </template>

            <div v-if="agentsStore.isCodeAgent" class="panel-section code-agent-hint">
              <div class="hint-box code-agent-box">
                <span class="hint-icon">⚙️</span>
                <span class="hint-text">代码智能体</span>
                <span class="hint-sub">此智能体由代码注册，工具、MCP、Skills、提示词和模型由代码中的 graph 决定。当前面板的框架级配置不适用于它。</span>
              </div>
            </div>

            <div v-if="chatStore.threadId" class="panel-section status-section">
              <h4>会话</h4>
              <div class="status-item">
                <span>Thread:</span>
                <code :title="chatStore.threadId">{{ chatStore.threadId }}</code>
              </div>
            </div>

            <div class="panel-section markdown-layout-section appearance-section">
              <div class="section-header compact-section-header">
                <h4>Markdown 版式</h4>
                <span class="theme-current">{{ currentLayoutOption.label }}</span>
              </div>
              <el-select
                v-model="markdownLayout"
                size="small"
                class="markdown-theme-select"
                @change="(value: MarkdownLayoutId) => setMarkdownLayout(value)"
              >
                <el-option
                  v-for="option in MARKDOWN_LAYOUT_OPTIONS"
                  :key="option.id"
                  :label="option.label"
                  :value="option.id"
                >
                  <div class="theme-option-row">
                    <span class="layout-option-mark">Aa</span>
                    <div class="theme-option-copy">
                      <span class="theme-option-name">{{ option.label }}</span>
                      <span class="theme-option-desc">{{ option.description }}</span>
                    </div>
                  </div>
                </el-option>
              </el-select>
            </div>

            <div class="panel-section markdown-theme-section appearance-section">
              <div class="section-header compact-section-header">
                <h4>Markdown 色盘</h4>
                <span class="theme-current">{{ currentOption.label }}</span>
              </div>
              <el-select
                v-model="markdownTheme"
                size="small"
                class="markdown-theme-select"
                @change="(value: MarkdownThemeId) => setMarkdownTheme(value)"
              >
                <el-option
                  v-for="option in MARKDOWN_THEME_OPTIONS"
                  :key="option.id"
                  :label="option.label"
                  :value="option.id"
                >
                  <div class="theme-option-row">
                    <span class="theme-option-dot" :style="{ background: option.accent }"></span>
                    <div class="theme-option-copy">
                      <span class="theme-option-name">{{ option.label }}</span>
                      <span class="theme-option-desc">{{ option.description }}</span>
                    </div>
                  </div>
                </el-option>
              </el-select>
            </div>

            <div class="panel-section input-animation-section appearance-section">
              <div class="section-header compact-section-header">
                <h4>输入框动画</h4>
                <span class="theme-current">{{ currentAnimationOption.label }}</span>
              </div>
              <el-select
                v-model="inputAnimation"
                size="small"
                class="input-animation-select"
                @change="(value: InputAnimationType) => setInputAnimation(value)"
              >
                <el-option
                  v-for="option in INPUT_ANIMATION_OPTIONS"
                  :key="option.id"
                  :label="option.label"
                  :value="option.id"
                >
                  <div class="theme-option-row">
                    <span class="theme-option-dot" :style="{ background: option.id === 'marquee' || option.id === 'rainbow-gradient' ? 'linear-gradient(90deg,#ff2d95,#9b5cff,#2da8ff,#18e6c3,#ffe14d,#ff7a2d)' : option.id === 'transparent-arc' ? 'conic-gradient(transparent 60%, #ff2d95 70%, #2da8ff 80%, transparent 90%)' : 'conic-gradient(#ff2d95,#2da8ff,#18e6c3,#ff2d95)' }"></span>
                    <div class="theme-option-copy">
                      <span class="theme-option-name">{{ option.label }}</span>
                      <span class="theme-option-desc">{{ option.description }}</span>
                    </div>
                  </div>
                </el-option>
              </el-select>
            </div>
          </template>

          <template v-if="activeTab === 'abilities'">
            <div v-if="agentsStore.isCodeAgent" class="panel-section code-agent-hint">
              <div class="hint-box code-agent-box">
                <span class="hint-icon">⚙️</span>
                <span class="hint-text">代码智能体</span>
                <span class="hint-sub">此智能体由代码注册，工具、MCP、Skills、提示词和模型由代码中的 graph 决定。当前面板的框架级配置不适用于它。</span>
              </div>
            </div>

            <div v-if="agentsStore.isChatAgent" class="panel-section chat-only-hint">
              <div class="hint-box">
                <span class="hint-icon">💬</span>
                <span class="hint-text">Chat 模式：纯对话，无工具</span>
                <span class="hint-sub">切换至 Empty 或 Power 智能体以启用工具</span>
              </div>
            </div>

            <template v-if="!agentsStore.isChatAgent && !agentsStore.isCodeAgent">
              <div class="panel-section tools-section">
                <div class="section-header tools-section-header">
                  <h4>工具</h4>
                  <span class="section-summary">{{ toolsStore.filteredGroups.length }} 组</span>
                </div>
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
                      <button
                        class="mcp-refresh-btn"
                        type="button"
                        :disabled="!server.allowed || !server.enabled || toolsStore.isMcpRefreshing(server.name)"
                        :title="`刷新 ${server.name}`"
                        :aria-label="`刷新 ${server.name}`"
                        @click="toolsStore.refreshMcpServer(server.name)"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          :class="{ spinning: toolsStore.isMcpRefreshing(server.name) }"
                        >
                          <path d="M21 2v6h-6" />
                          <path d="M3 12a9 9 0 0 1 15.55-6.36L21 8" />
                          <path d="M3 22v-6h6" />
                          <path d="M21 12a9 9 0 0 1-15.55 6.36L3 16" />
                        </svg>
                      </button>
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
                    <div class="skill-body">
                      <div class="skill-line">
                        <span class="skill-name" :class="{ dimmed: !skill.enabled }">{{ skill.name }}</span>
                        <span v-if="skill.path" class="skill-path" :title="skill.path">{{ skill.path }}</span>
                      </div>
                      <span class="skill-desc">{{ skill.description }}</span>
                    </div>
                    <button class="detail-btn" type="button" @click="openDetail('skill', skill.name, skill)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="16" x2="12" y2="12" />
                        <line x1="12" y1="8" x2="12.01" y2="8" />
                      </svg>
                      详情
                    </button>
                  </div>
                </div>
                <p v-if="!toolsStore.skills.length" class="empty-hint">暂无 Skills</p>
              </div>

              <div class="panel-section">
                <PermissionsPanel />
              </div>
            </template>
          </template>

          <template v-if="activeTab === 'changes'">
            <FileChangesPanel />
          </template>

          <template v-if="activeTab === 'editor'">
            <FileEditorPane />
          </template>

          <template v-if="activeTab === 'tasks'">
            <div v-if="chatStore.todos.length > 0" class="panel-section todo-section">
              <TodoList :todos="chatStore.todos" />
            </div>

            <div class="panel-section automation-section">
              <div class="section-header compact-section-header">
                <h4>自动化任务</h4>
                <span class="theme-current">{{ enabledAutomationTaskCount }}/{{ automationStore.taskCount }}</span>
              </div>
              <button class="automation-entry-btn" type="button" @click="emit('open-automation')">
                <el-icon><Clock /></el-icon>
                管理定时任务
              </button>
            </div>

            <template v-if="!agentsStore.isChatAgent && !agentsStore.isCodeAgent">
              <div class="panel-section processes-section">
                <div class="section-header">
                  <h4>Agent 启动的后台进程</h4>
                  <span class="process-count" v-if="bgProcesses.length">{{ bgProcesses.length }}</span>
                  <button class="refresh-btn" type="button" :disabled="processFetching" @click="fetchProcesses">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ spinning: processFetching }">
                      <path d="M21 2v6h-6" /><path d="M3 12a9 9 0 0 1 15.55-6.36L21 8" /><path d="M3 22v-6h6" /><path d="M21 12a9 9 0 0 1-15.55 6.36L3 16" />
                    </svg>
                    刷新
                  </button>
                </div>
                <div v-if="bgProcesses.length === 0" class="empty-hint">无 Agent 启动的后台进程</div>
                <div v-for="proc in bgProcesses" :key="proc.pid" class="process-item" :class="{ exited: !proc.status.startsWith('running') }" @click="openProcessDetail(proc)">
                  <div class="process-row">
                    <span class="process-pid">{{ proc.pid }}</span>
                    <span class="process-status-dot" :class="proc.status.startsWith('running') ? 'alive' : 'dead'"></span>
                    <span class="process-elapsed">{{ formatElapsed(proc.elapsed_s) }}</span>
                    <button
                      v-if="proc.status.startsWith('running')"
                      class="process-kill-btn"
                      @click.stop="killTrackedProcess(proc.pid)"
                      :disabled="killingPids[proc.pid]"
                    >终止</button>
                  </div>
                  <div class="process-cmd">{{ proc.command }}</div>
                </div>
              </div>

              <teleport to="body">
                <div v-if="processModalVisible" class="process-modal-backdrop" @click="processModalVisible = false">
                  <div class="process-modal" @click.stop>
                    <div class="process-modal-header">
                      <span class="process-modal-title">PID {{ processModalData.pid }}</span>
                      <div class="process-modal-actions">
                        <button v-if="processModalData.status === 'running'" class="process-kill-btn" @click="killFromModal">终止</button>
                        <button class="process-modal-refresh" @click="refreshProcessModal">刷新</button>
                        <button class="process-modal-close" @click="processModalVisible = false">✕</button>
                      </div>
                    </div>
                    <div class="process-modal-cmd">
                      <pre>{{ processModalData.command }}</pre>
                    </div>
                    <div class="process-modal-meta">
                      <span>状态: {{ processModalData.status }}</span>
                      <span>运行: {{ formatElapsed(processModalData.elapsed_s) }}</span>
                    </div>
                    <div class="process-modal-output">
                      <div class="process-modal-output-content" v-html="renderedModalOutput"></div>
                    </div>
                  </div>
                </div>
              </teleport>
            </template>
          </template>


        </div>
        </transition>
      </div>

      <DetailModal
        v-model:visible="detailModal.visible"
        :title="detailModal.title"
        :mode="detailModal.mode"
        :data="detailModal.data"
      />
    </div>
  </aside>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

defineProps<{ collapsed?: boolean; panelWidth?: number }>()
const emit = defineEmits<{ 'toggle-collapse': []; 'open-automation': [] }>()

import { useToolsStore } from '@/stores/tools'
import { useUiStore, type RightPanelTab } from '@/stores/ui'
import { api, fetchApi } from '@/api/http'
import { useChatStore } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import { useAutomationStore } from '@/stores/automation'
import { useFileChangesStore } from '@/stores/file-changes'
import { useOpenedFilesStore } from '@/stores/opened-files'
import { useMarkdownTheme, MARKDOWN_THEME_OPTIONS, type MarkdownThemeId } from '@/composables/useMarkdownTheme'
import { useMarkdownLayout, MARKDOWN_LAYOUT_OPTIONS, type MarkdownLayoutId } from '@/composables/useMarkdownLayout'
import { useInputAnimation, INPUT_ANIMATION_OPTIONS, type InputAnimationType } from '@/composables/useInputAnimation'
import { AnsiUp } from 'ansi_up'
import { Clock, Cpu, Tools, Files, FolderOpened } from '@element-plus/icons-vue'
import ModelSelector from '@/components/panels/ModelSelector.vue'
import ToolGroupPanel from '@/components/panels/ToolGroupPanel.vue'
import DetailModal from '@/components/panels/DetailModal.vue'
import TodoList from '@/components/panels/TodoList.vue'
import PermissionsPanel from '@/components/settings/PermissionsPanel.vue'
import FileChangesPanel from '@/components/panels/FileChangesPanel.vue'
import FileEditorPane from '@/components/panels/FileEditorPane.vue'

const ansiUp = new AnsiUp()

const toolsStore = useToolsStore()
const uiStore = useUiStore()
const chatStore = useChatStore()
const agentsStore = useAgentsStore()
const automationStore = useAutomationStore()
const fileChangesStore = useFileChangesStore()
const openedFilesStore = useOpenedFilesStore()
const enabledAutomationTaskCount = computed(() => automationStore.tasks.filter(task => task.enabled).length)

const activeTab = computed(() => uiStore.activeTab)

const runningProcessCount = computed(() =>
  bgProcesses.value.filter(proc => proc.status.startsWith('running')).length,
)
const mcpErrorCount = computed(() =>
  toolsStore.filteredMcp.filter(server => server.allowed && server.status === 'error').length,
)

// 文件 tab：已打开文件数；有未保存改动时徽标变色提醒
const dirtyFileCount = computed(() =>
  openedFilesStore.files.filter(f => openedFilesStore.contentOf(f.path)?.dirty).length,
)

const tabs = computed((): Array<{ id: RightPanelTab; label: string; icon: any; badge: number }> => {
  const list: Array<{ id: RightPanelTab; label: string; icon: any; badge: number }> = [
    { id: 'model', label: '模型', icon: Cpu, badge: 0 },
    { id: 'abilities', label: '能力', icon: Tools, badge: mcpErrorCount.value },
    { id: 'changes', label: '变更', icon: Files, badge: fileChangesStore.fileCount },
  ]
  // 文件查看区：打开的文件以标签展示，内容在此查看
  list.push({ id: 'editor', label: '文件', icon: FolderOpened, badge: openedFilesStore.files.length })
  list.push({ id: 'tasks', label: '任务', icon: Clock, badge: runningProcessCount.value })
  return list
})

const presetLlmParams = computed(() => agentsStore.currentAgent?.llm_params ?? null)

const effectiveTemperature = computed(() =>
  toolsStore.llmParams?.temperature
    ?? presetLlmParams.value?.temperature
    ?? 0.7
)
const effectiveReasoningEffort = computed(() =>
  toolsStore.llmParams?.reasoning_effort
    ?? presetLlmParams.value?.reasoning_effort
    ?? null
)
const hasTemperatureOverride = computed(() => toolsStore.llmParams?.temperature !== undefined)
const hasReasoningOverride = computed(() => toolsStore.llmParams?.reasoning_effort !== undefined)
const temperatureFromPreset = computed(() =>
  !hasTemperatureOverride.value && presetLlmParams.value?.temperature !== undefined
)
const reasoningFromPreset = computed(() =>
  !hasReasoningOverride.value && presetLlmParams.value?.reasoning_effort !== undefined
)
const { markdownTheme, currentOption, setMarkdownTheme } = useMarkdownTheme()
const { markdownLayout, currentLayoutOption, setMarkdownLayout } = useMarkdownLayout()
const { inputAnimation, currentOption: currentAnimationOption, setInputAnimation } = useInputAnimation()

const summEnabled = ref(true)
const summModel = ref('')

let bgRefreshTimer: ReturnType<typeof setTimeout> | null = null

function onBgProcessChanged() {
  if (bgRefreshTimer) clearTimeout(bgRefreshTimer)
  bgRefreshTimer = setTimeout(() => {
    bgRefreshTimer = null
    fetchProcesses()
  }, 500)
}

onMounted(async () => {
  try {
    const conf = await api.getSummarization()
    summEnabled.value = conf.enabled
    summModel.value = conf.default_model || ''
  } catch { /* ignore */ }
  fetchProcesses()
  automationStore.loadTasks()
  window.addEventListener('bg-process-changed', onBgProcessChanged)
})

onBeforeUnmount(() => {
  window.removeEventListener('bg-process-changed', onBgProcessChanged)
  if (bgRefreshTimer) {
    clearTimeout(bgRefreshTimer)
    bgRefreshTimer = null
  }
})

interface TrackedProcess {
  pid: number
  command: string
  status: string
  elapsed_s: number
}

const bgProcesses = ref<TrackedProcess[]>([])
const killingPids = ref<Record<number, boolean>>({})
const processFetching = ref(false)

async function fetchProcesses() {
  processFetching.value = true
  try {
    const data = await fetchApi<{ processes: TrackedProcess[] }>('/tools/processes')
    bgProcesses.value = data.processes
  } catch { /* ignore */ }
  processFetching.value = false
}

watch(activeTab, (tab) => {
  if (tab === 'tasks') void fetchProcesses()
})

async function killTrackedProcess(pid: number) {
  killingPids.value = { ...killingPids.value, [pid]: true }
  try {
    await fetchApi(`/tools/process/${pid}/kill`, { method: 'POST' })
    await fetchProcesses()
  } catch { /* ignore */ }
  const { [pid]: _, ...rest } = killingPids.value
  killingPids.value = rest
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`
}

const processModalVisible = ref(false)
const processModalData = ref<TrackedProcess>({ pid: 0, command: '', status: '', elapsed_s: 0 })
const processModalOutput = ref('')

async function openProcessDetail(proc: TrackedProcess) {
  processModalData.value = proc
  processModalOutput.value = '加载中...'
  processModalVisible.value = true
  await refreshProcessModal()
}

async function refreshProcessModal() {
  const pid = processModalData.value.pid
  try {
    const data = await fetchApi<{ pid: number; status: string; output: string; offset: number }>(
      `/tools/process/${pid}/output?offset=0`
    )
    processModalOutput.value = data.output || '(无输出)'
    processModalData.value.status = data.status
  } catch {
    processModalOutput.value = '(获取输出失败)'
  }
}

async function killFromModal() {
  const pid = processModalData.value.pid
  await killTrackedProcess(pid)
  await refreshProcessModal()
}

const renderedModalOutput = computed(() => {
  const raw = processModalOutput.value
  if (!raw) return ''
  return ansiUp.ansi_to_html(raw)
    .replace(/\n/g, '<br>')
    .replace(/ {2}/g, '&nbsp;&nbsp;')
})

async function updateSummarization(data: { enabled?: boolean; default_model?: string }) {
  try {
    const res = await api.updateSummarization(data)
    summEnabled.value = res.enabled
    summModel.value = res.default_model || ''
  } catch { /* ignore */ }
}

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
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.right-panel.collapsed {
  width: 44px;
  align-items: center;
  padding-top: 10px;
}

.rail-toggle {
  flex-shrink: 0;
}

.right-panel-topbar {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 12px 0;
  flex-shrink: 0;
}

.toggle-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: color-mix(in srgb, var(--el-fill-color) 90%, var(--el-bg-color) 10%);
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font-size: 14px;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.toggle-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.toggle-icon {
  display: inline-block;
}

.right-panel-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel-tabs {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
  padding: 4px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  background: color-mix(in srgb, var(--el-fill-color) 90%, var(--el-bg-color) 10%);
}

.panel-tab {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 32px;
  padding: 5px 6px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.2px;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.panel-tab:hover:not(.active) {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  transform: translateY(-1px);
}

/* 面板 tab 区域色相：紫，与会话标签靛蓝、文件标签翠绿区分 */
.panel-tab.active {
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  color: #fff;
  border-color: rgba(124, 58, 237, 0.6);
  box-shadow: 0 2px 10px rgba(124, 58, 237, 0.35);
}

.panel-tab-icon {
  font-size: 13px;
}

.panel-tab-label {
  line-height: 1;
}

.panel-tab-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 15px;
  height: 15px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--el-color-danger);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 15px;
  text-align: center;
  box-shadow: 0 0 0 2px var(--el-bg-color);
}

/* 文件 tab 有未保存改动时：徽标改用橙色提醒，与「变更」默认红区分 */
.panel-tab-badge.is-dirty {
  background: var(--el-color-warning);
}

.right-panel-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 16px;
}

/* 文件编辑区自己就是滚动容器：外层必须交出滚动权并去掉内边距，
   否则外层先滚动，编辑器内部的 overflow 拿不到高度约束，滚轮会失效 */
.right-panel-scroll.is-editor {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.right-panel-scroll.is-editor > .tab-pane {
  flex: 1;
  min-height: 0;
}

.tab-pane {
  display: flex;
  flex-direction: column;
}

.fade-up-enter-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.fade-up-leave-active {
  transition: opacity 0.12s ease;
}

.fade-up-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.fade-up-leave-to {
  opacity: 0;
}

.panel-section {
  margin-bottom: 14px;
  padding: 13px;
  background: var(--el-fill-color-extra-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.markdown-layout-section,
.markdown-theme-section {
  background: linear-gradient(180deg, color-mix(in srgb, var(--el-fill-color-extra-light) 90%, var(--el-color-primary) 5%), var(--el-fill-color-extra-light));
}

.window-trim-section,
.markdown-layout-section,
.markdown-theme-section,
.automation-section {
  margin-bottom: 14px;
}

.automation-section {
  background: color-mix(in srgb, var(--el-fill-color-extra-light) 92%, var(--el-color-primary) 8%);
}

.automation-entry-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 34px;
  gap: 7px;
  border: 1px solid var(--el-color-primary);
  border-radius: 6px;
  background: var(--el-color-primary);
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  box-shadow: 0 2px 6px color-mix(in srgb, var(--el-color-primary) 20%, transparent);
  transition: background .15s, border-color .15s, box-shadow .15s, transform .15s;
}

.automation-entry-btn:hover {
  border-color: var(--el-color-primary-dark-2);
  background: var(--el-color-primary-dark-2);
  box-shadow: 0 3px 8px color-mix(in srgb, var(--el-color-primary) 28%, transparent);
}

.automation-entry-btn:active {
  transform: translateY(1px);
  box-shadow: none;
}

.automation-entry-btn:focus-visible {
  outline: 2px solid var(--el-color-primary-light-3);
  outline-offset: 2px;
}

.llm-params-controls {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.param-row-slider {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.param-label-group {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.param-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
  font-weight: 600;
  white-space: nowrap;
}

.param-source-hint {
  font-size: 10px;
  padding: 0 4px;
  border-radius: 3px;
  background: var(--el-fill-color);
  color: var(--el-text-color-placeholder);
  border: 1px solid var(--el-border-color-lighter);
  white-space: nowrap;
}

.param-source-hint.override {
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-7);
}

.param-control-group {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.reasoning-effort-select {
  width: 100%;
}

.param-reset-btn {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 1px solid var(--el-border-color);
  border-radius: 50%;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: all 0.15s ease;
}

.param-reset-btn:hover {
  background: var(--el-color-danger-light-8);
  border-color: var(--el-color-danger-light-5);
  color: var(--el-color-danger);
}

.temperature-control {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.temperature-slider {
  flex: 1;
}

.temperature-input {
  width: 68px;
  flex-shrink: 0;
}

.window-trim-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.window-trim-select {
  width: 100%;
}

.compact-section-header {
  margin-bottom: 8px;
  padding-bottom: 0;
  border-bottom: none;
}

.theme-current {
  max-width: 132px;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.markdown-theme-select {
  width: 100%;
}

.input-animation-section {
  background: linear-gradient(180deg, color-mix(in srgb, var(--el-fill-color-extra-light) 90%, var(--el-color-primary) 5%), var(--el-fill-color-extra-light));
}

.input-animation-select {
  width: 100%;
}

.theme-option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.theme-option-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 12%, transparent);
  flex-shrink: 0;
}

.layout-option-mark {
  display: inline-flex;
  width: 20px;
  height: 20px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-family: Georgia, serif;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  flex-shrink: 0;
}

.theme-option-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.25;
}

.theme-option-name {
  color: var(--el-text-color-primary);
  font-size: 12px;
  font-weight: 700;
}

.theme-option-desc {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-section h4 {
  display: inline-flex;
  align-items: center;
  min-height: 25px;
  margin: 0;
  padding: 0 9px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 999px;
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.35px;
}

.panel-section h4::before {
  content: '';
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--el-color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--el-color-primary) 12%, transparent);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 0;
  border-bottom: none;
}

.section-summary {
  padding: 3px 7px;
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 999px;
  background: color-mix(in srgb, var(--el-color-primary) 8%, transparent);
  color: var(--el-color-primary);
  font-size: 10px;
  font-weight: 700;
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

.processes-section .process-count {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
  font-weight: 700;
}

.tools-section {
  padding-bottom: 10px;
}

.tools-section-header {
  margin-bottom: 10px;
}

.process-item {
  padding: 6px 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  background: var(--el-fill-color);
  border: 1px solid var(--el-border-color-lighter);
}

.process-item.exited {
  opacity: 0.5;
}

.process-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.process-pid {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.process-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.process-status-dot.alive {
  background: var(--el-color-success);
  box-shadow: 0 0 4px var(--el-color-success);
}

.process-status-dot.dead {
  background: var(--el-text-color-placeholder);
}

.process-elapsed {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  margin-left: auto;
}

.process-kill-btn {
  font-size: 10px;
  padding: 1px 6px;
  border: 1px solid var(--el-color-danger-light-5);
  border-radius: 3px;
  background: transparent;
  color: var(--el-color-danger);
  cursor: pointer;
  transition: all 0.15s;
}

.process-kill-btn:hover {
  background: var(--el-color-danger-light-9);
}

.process-kill-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.process-cmd {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
  font-family: 'JetBrains Mono', monospace;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
  line-height: 1.5;
}

.process-item {
  cursor: pointer;
}

.process-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.status-section code {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  word-break: break-all;
  user-select: all;
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
  align-items: flex-start;
  gap: 6px;
}

.skill-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: 2px;
}

.skill-line {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.skill-path {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.skill-desc {
  font-size: 12px;
  color: var(--el-text-color-regular);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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

.mcp-refresh-btn {
  display: inline-flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 4px;
  color: var(--el-text-color-secondary);
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
}

.mcp-refresh-btn:hover:not(:disabled) {
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 8%, transparent);
}

.mcp-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.skill-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-color-primary);
  transition: color 0.15s ease, opacity 0.15s ease;
}

.code-agent-hint .hint-sub {
  line-height: 1.45;
}

.hint-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.hint-icon {
  font-size: 16px;
}

.hint-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.hint-sub {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.code-agent-box {
  border: 1px solid var(--el-color-primary-light-7);
  background: color-mix(in srgb, var(--el-color-primary) 7%, var(--el-fill-color-light));
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .panel-tab,
  .fade-up-enter-active,
  .fade-up-leave-active {
    transition: none;
  }
}

@media (max-width: 900px) {
  .right-panel {
    width: min(90vw, 380px);
    max-width: 90vw;
  }

  .right-panel-topbar {
    padding: 8px 10px 0;
  }

  .right-panel-scroll {
    padding: 10px 12px 14px;
  }

  /* 窄栏下图标文字并排会挤，退化为图标 + 更小字号 */
  .panel-tab {
    gap: 3px;
    padding: 5px 4px;
    font-size: 11px;
  }
}
</style>

<style>
.process-modal-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--el-bg-color-page) 70%, transparent);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.process-modal {
  width: min(1300px, calc(100vw - 40px));
  max-height: min(92vh, 960px);
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
}

.process-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  gap: 12px;
}

.process-modal-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  word-break: break-all;
  line-height: 1.5;
}

.process-modal-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.process-modal-refresh {
  padding: 4px 10px;
  font-size: 11px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
}

.process-modal-refresh:hover {
  border-color: var(--el-color-primary-light-5);
  color: var(--el-color-primary);
}

.process-modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 16px;
  cursor: pointer;
}

.process-modal-close:hover {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.process-modal-cmd {
  padding: 8px 16px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
  max-height: 24vh;
  overflow-y: auto;
  flex-shrink: 0;
}

.process-modal-cmd pre {
  margin: 0;
  font-size: 14px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #79c0ff;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.7;
}

.process-modal-meta {
  display: flex;
  gap: 16px;
  padding: 8px 16px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.process-modal-output {
  flex: 1;
  overflow: auto;
  padding: 12px 16px;
  background: #0d1117;
}

.process-modal-output-content {
  font-size: 15px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #c9d1d9;
  word-break: break-word;
  line-height: 1.8;
}
</style>
