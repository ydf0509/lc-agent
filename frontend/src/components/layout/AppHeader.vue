<template>
  <!-- 桌面无标题栏模式：header 自身不当拖拽区（否则内部按钮/选择器点不中），
       拖拽手柄只有两段：logo 块 + 中央空白 spacer。
       双击任一段切换最大化/还原。 -->
  <header class="app-header">
    <div class="header-left">
      <!-- 左拖拽手柄：只包 logo，不包移动端按钮 -->
      <span
        v-if="showDesktopChrome"
        class="desktop-drag-block pywebview-drag-region"
        @dblclick="desktop.toggleMax()"
      ><span class="logo desktop-logo">⚡ {{ appName }}</span></span>
      <span v-if="!showDesktopChrome" class="logo">⚡ {{ appName }}</span>
      <el-button
        class="mobile-sidebar-btn"
        :icon="Menu"
        circle
        size="small"
        aria-label="打开会话列表"
        @click="$emit('openMobileSidebar')"
      />
    </div>
    <div class="header-center">
      <div class="agent-select-wrapper">
      <el-select
        class="agent-select"
        :model-value="agentsStore.currentAgentId"
        size="small"
        @change="$emit('changeAgent', $event)"
        placeholder="选择智能体"
        popper-class="agent-select-popper"
      >
        <el-option
          v-for="agent in agentsStore.agents"
          :key="agent.id"
          :label="`${getAgentIcon(agent)} ${agent.display_name || agent.name}`"
          :value="agent.id"
        >
          <div class="agent-option">
            <span class="agent-option-icon">{{ getAgentIcon(agent) }}</span>
            <div class="agent-option-content">
              <span class="agent-option-name">{{ agent.display_name || agent.name }}</span>
            </div>
            <span v-if="agent.project_mode" class="source-tag source-tag--project">项目</span>
            <span v-else :class="['source-tag', `source-tag--${agent.source || 'user'}`]">
              {{ agent.source === 'builtin' ? '内置' : agent.source === 'code' ? '代码' : '自建' }}
            </span>
          </div>
        </el-option>
      </el-select>
      </div>
      <!-- 中央空白拖拽手柄：桌面无标题栏模式才出现，双击切换最大化 -->
      <span
        v-if="showDesktopChrome"
        class="desktop-drag-spacer pywebview-drag-region"
        @dblclick="desktop.toggleMax()"
      />
      <div class="header-actions desktop-only">
        <FileChangesBadge />
        <button class="header-btn btn-manage-agents" @click="$emit('manageAgents')">⚙ Agents管理</button>
        <button class="header-btn btn-new-chat" @click="$emit('newChat')">+ 新对话</button>
        <CopyRoundsButton v-if="hasMessages" :messages="chatStore.messages" :model-name="sessionModel" />
      </div>
    </div>
    <div class="header-right">
      <button class="header-btn mobile-agents-btn" @click="$emit('manageAgents')" aria-label="Agents管理">
        <el-icon><Briefcase /></el-icon>
      </button>
      <button class="header-btn mobile-new-chat-btn" @click="$emit('newChat')">
        <el-icon class="mobile-btn-icon"><Plus /></el-icon>
        <span class="mobile-btn-text">新对话</span>
      </button>
      <span class="mobile-only">
        <FileChangesBadge />
        <CopyRoundsButton v-if="hasMessages" :messages="chatStore.messages" :model-name="sessionModel" />
      </span>
      <el-button
        class="mobile-tools-btn"
        :icon="Setting"
        circle
        size="small"
        aria-label="打开工具和状态面板"
        @click="$emit('openMobileTools')"
      />
      <el-select
        v-if="!agentsStore.isCodeAgent"
        class="header-model-select"
        :model-value="toolsStore.currentModel"
        size="small"
        filterable
        placeholder="选择模型"
        popper-class="header-model-select-popper"
        @change="toolsStore.setModel($event)"
      >
        <el-option
          v-for="model in toolsStore.models"
          :key="model.model_id"
          :label="model.model_id"
          :value="model.model_id"
        >
          <span>{{ model.model_id }}</span>
          <span class="header-model-option-provider">{{ model.provider }}</span>
        </el-option>
      </el-select>
      <span v-else class="model-badge">{{ modelName }}</span>
      <el-button :icon="RefreshRight" circle size="small" title="刷新页面" @click="reloadPage" />
      <el-button :icon="isDark ? Sunny : Moon" circle size="small" @click="toggleDark()" />
      <DesktopWindowControls />
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAgentsStore } from '@/stores/agents'
import { useChatStore } from '@/stores/chat'
import { useToolsStore } from '@/stores/tools'
import { useTheme } from '@/composables/useTheme'
import { getAgentIcon } from '@/utils/agentIcon'
import { Sunny, Moon, Menu, Setting, RefreshRight, Plus, Briefcase } from '@element-plus/icons-vue'
import CopyRoundsButton from '@/components/chat/CopyRoundsButton.vue'
import FileChangesBadge from '@/components/chat/FileChangesBadge.vue'
import DesktopWindowControls from '@/components/layout/DesktopWindowControls.vue'
import { useDesktopMode } from '@/stores/desktop'

const desktop = useDesktopMode()

// 桌面无标题栏模式才启用拖拽手柄 + 自绘三按钮；浏览器完全不受影响
const showDesktopChrome = computed(() => desktop.isDesktop && desktop.isFrameless)

function onPywebviewReady() {
  desktop.markBridgeReady()
}

if (typeof window !== 'undefined') {
  // 就绪判定不用事件、用“api 里有没有真实方法”做轮询确认，原因：
  // 1. pywebviewready 是 CustomEvent，不排队不重放——Vue setup 执行晚了就永远错过；
  // 2. window.pywebview 对象先被注入时 api 只是空对象 {}（truthy），方法稍后才挂上，
  //    同步探测 pv?.api 会误判就绪。所以必须确认 typeof minimize === 'function'。
  // 事件只做加速信号，最终以轮询为准；浏览器 ?desktop=1 预览下轮询永不命中，
  // 按钮保持禁用（符合预期）。
  const hasRealApi = () => {
    const pv = (window as unknown as { pywebview?: { api?: Record<string, unknown> } }).pywebview
    return typeof pv?.api?.minimize === 'function'
  }
  if (hasRealApi()) {
    onPywebviewReady()
  } else {
    window.addEventListener('pywebviewready', onPywebviewReady, { once: true })
    const timer = window.setInterval(() => {
      if (hasRealApi()) {
        window.clearInterval(timer)
        window.removeEventListener('pywebviewready', onPywebviewReady)
        onPywebviewReady()
      }
    }, 200)
    // 10s 还没 api 说明是浏览器预览，保持按钮禁用并停掉轮询
    window.setTimeout(() => {
      window.clearInterval(timer)
      window.removeEventListener('pywebviewready', onPywebviewReady)
    }, 10000)
  }
}

const agentsStore = useAgentsStore()
const chatStore = useChatStore()
const toolsStore = useToolsStore()
const { isDark, toggleDark } = useTheme()

function reloadPage() {
  window.location.reload()
}

const hasMessages = computed(() => chatStore.messages.length > 0)
const sessionModel = computed(() => {
  if (agentsStore.isCodeAgent) return '代码内定义'
  const model = toolsStore.currentModel || agentsStore.currentAgent?.default_model || ''
  return model
})

defineProps<{
  appName: string
  modelName: string
}>()

const emit = defineEmits<{
  manageAgents: []
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
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 桌面无标题栏模式：只有带 .pywebview-drag-region 的节点才参与窗口拖拽。
   pywebview 注入的 customize.js 在 body mousedown 时实时 querySelectorAll，
   所以 Vue 动态渲染的节点同样生效（6.x 事件委托，已验证）。
   拖拽类只加在三段手柄上（logo 块 / 左 spacer 已并入 logo 块 / 中央 spacer），
   header 自身、按钮、选择器一律不加，否则 drag 会吞掉点击
   （DRAG_REGION_DIRECT_TARGET_ONLY 默认为 False，子节点点击也会触发拖拽）。 */
.desktop-drag-block,
.desktop-drag-spacer {
  -webkit-user-select: none;
  user-select: none;
}
.desktop-drag-block {
  display: inline-flex;
  align-items: center;
  align-self: stretch;
  padding-right: 8px;
  cursor: default;
}
.desktop-drag-spacer {
  display: inline-block;
  width: 72px;
  min-width: 24px;
  flex: 0 1 160px;
  align-self: stretch;
  cursor: default;
}

.header-center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-sidebar-btn,
.mobile-tools-btn,
.mobile-new-chat-btn,
.mobile-only {
  display: none;
}

.desktop-only {
  display: inline-flex;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex-wrap: nowrap;
}

.agent-select-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}


.agent-select {
  width: 260px;
}

.agent-select :deep(.el-select__wrapper) {
  min-width: 0;
  min-height: 36px;
  padding: 0 32px 0 10px;
  border-radius: 12px;
  border: 1.5px solid var(--el-color-primary);
  background: var(--el-bg-color);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  transition: all 0.2s ease;
}

.agent-select :deep(.el-select__wrapper:hover) {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--el-color-primary) 16%, transparent);
}

.agent-select :deep(.el-select__wrapper.is-focused) {
  border-color: var(--el-color-primary);
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--el-color-primary) 12%, transparent),
    0 4px 14px color-mix(in srgb, var(--el-color-primary) 16%, transparent);
}

.agent-select :deep(.el-select__prefix) {
  color: var(--el-color-primary);
  margin-right: 4px;
}

.agent-select :deep(.el-select__selected-item) {
  min-width: 0;
  display: block;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--el-text-color-primary);
}

.agent-select :deep(.el-select__caret) {
  color: var(--el-color-primary);
  font-size: 13px;
  opacity: 0.7;
  transition: opacity 0.2s, transform 0.2s;
}

.agent-select :deep(.el-select__wrapper:hover .el-select__caret) {
  opacity: 1;
}

:global(html.dark) .agent-select :deep(.el-select__wrapper) {
  background: rgba(15, 23, 42, 0.9);
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

:global(html.dark) .agent-select :deep(.el-select__wrapper:hover) {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 18px color-mix(in srgb, var(--el-color-primary) 24%, transparent);
}

:global(html.dark) .agent-select :deep(.el-select__wrapper.is-focused) {
  border-color: var(--el-color-primary);
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--el-color-primary) 16%, transparent),
    0 6px 20px color-mix(in srgb, var(--el-color-primary) 24%, transparent);
}

.model-badge {
  font-size: 12px;
  padding: 3px 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  color: var(--el-text-color-secondary);
}

.header-model-select {
  width: 164px;
}

.header-model-select :deep(.el-select__wrapper) {
  min-height: 26px;
  border-radius: 14px;
  border: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
  box-shadow: none;
}

.header-model-select :deep(.el-select__selected-item) {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-model-option-provider {
  float: right;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}


.agent-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 2px 0;
}

.agent-option-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 22px;
  text-align: center;
}

.agent-option-content {
  flex: 1;
  min-width: 0;
}

.agent-option-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
}

.source-tag {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 10px;
  font-weight: 600;
  flex-shrink: 0;
  letter-spacing: 0.02em;
}

.source-tag--builtin {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1));
  color: #7c3aed;
  border: 1px solid rgba(124, 58, 237, 0.2);
}

.source-tag--code {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.1));
  color: #059669;
  border: 1px solid rgba(5, 150, 105, 0.2);
}

.source-tag--user {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(249, 115, 22, 0.1));
  color: #d97706;
  border: 1px solid rgba(217, 119, 6, 0.2);
}

.source-tag--project {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(6, 182, 212, 0.1));
  color: #0284c7;
  border: 1px solid rgba(2, 132, 199, 0.2);
}

:global(html.dark) .source-tag--builtin {
  background: rgba(124, 58, 237, 0.15);
  color: #a78bfa;
  border-color: rgba(167, 139, 250, 0.25);
}

:global(html.dark) .source-tag--code {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border-color: rgba(110, 231, 183, 0.25);
}

:global(html.dark) .source-tag--user {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.25);
}

:global(html.dark) .source-tag--project {
  background: rgba(14, 165, 233, 0.15);
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.25);
}

.header-btn {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease, color 0.18s ease, opacity 0.18s ease;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

.header-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.header-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 5px 14px rgba(15, 23, 42, 0.10);
}

.header-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 18%, transparent), 0 8px 20px rgba(15, 23, 42, 0.12);
}

.btn-manage-agents {
  color: #f5f3ff;
  background: linear-gradient(135deg, #4f46e5, #6366f1);
  border-color: rgba(99, 102, 241, 0.42);
}

.btn-manage-agents:hover {
  background: linear-gradient(135deg, #4338ca, #4f46e5);
  border-color: rgba(99, 102, 241, 0.55);
}

.btn-new-chat,
.mobile-new-chat-btn {
  color: #ffffff;
  background: linear-gradient(135deg, #059669, #10b981);
  border-color: rgba(5, 150, 105, 0.36);
}

.btn-new-chat:hover,
.mobile-new-chat-btn:hover {
  background: linear-gradient(135deg, #047857, #059669);
}

:deep(.copy-rounds-trigger) {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  background: linear-gradient(135deg, #ea580c, #f59e0b);
  color: #ffffff;
  border: 1px solid rgba(234, 88, 12, 0.34);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

:deep(.copy-rounds-trigger:hover) {
  transform: translateY(-1px);
  background: linear-gradient(135deg, #c2410c, #ea580c);
  border-color: rgba(194, 65, 12, 0.4);
}

:global(html.dark) .header-btn,
:global(html.dark) .copy-rounds-trigger {
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.34);
}

:global(html.dark) .btn-manage-agents {
  color: #ede9fe;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.9), rgba(99, 102, 241, 0.85));
  border-color: rgba(129, 140, 248, 0.3);
}

:global(html.dark) .btn-manage-agents:hover {
  background: linear-gradient(135deg, rgba(67, 56, 202, 0.95), rgba(79, 70, 229, 0.95));
  border-color: rgba(165, 180, 252, 0.42);
}

/* Mobile Agents管理 icon button — hidden on desktop */
.mobile-agents-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 50%;
  font-size: 16px;
  color: #ffffff;
  background: linear-gradient(135deg, #4f46e5, #8b5cf6);
  border: 1px solid rgba(99, 102, 241, 0.55);
  cursor: pointer;
  box-shadow: 0 3px 8px rgba(79, 70, 229, 0.28);
  transition: background 0.18s, border-color 0.18s, box-shadow 0.18s, color 0.18s;
}
.mobile-agents-btn:hover {
  background: linear-gradient(135deg, #4338ca, #7c3aed);
  border-color: rgba(129, 140, 248, 0.78);
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(79, 70, 229, 0.38);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@media (max-width: 900px) {
  /* 桌面无标题栏模式下移动端布局不启用（窗口最小 800x600 且应横屏使用）；
     拖拽手柄/三按钮在窄屏下隐藏，避免挤占。 */
  .desktop-drag-block,
  .desktop-drag-spacer,
  .desktop-window-controls {
    display: none;
  }

  /* Show Agents管理 icon button on mobile */
  .mobile-agents-btn {
    display: flex;
  }

  .app-header {
    padding: 8px 10px;
    gap: 6px;
  }

  .mobile-sidebar-btn,
  .mobile-tools-btn,
  .mobile-new-chat-btn,
  .mobile-only {
    display: inline-flex;
    flex-shrink: 0;
  }

  .desktop-only {
    display: none;
  }

  .header-left {
    flex-shrink: 0;
  }

  .logo {
    display: none;
  }

  .header-center {
    justify-content: flex-start;
    overflow: hidden;
  }

  .header-right {
    gap: 0;
  }

  /* agent 选择器行全宽填充 */
  .agent-select-wrapper {
    width: 100%;
    flex: 1;
  }

  .agent-select {
    display: inline-flex;
    flex: 1;
    width: 100%;
    min-width: 0;
    max-width: none;
  }

  .agent-select :deep(.el-select__wrapper) {
    width: 100%;
    min-width: 0;
    padding-right: 24px;
  }

  .header-btn,
  .model-badge,
  .header-model-select,
  .status-dot,
  .status-text {
    display: none;
  }

  /* mobile-agents-btn 也有 header-btn class，需在 header-btn 规则之后重新显示 */
  .mobile-agents-btn {
    display: flex;
  }

  .mobile-new-chat-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    min-height: 28px;
    min-width: 28px;
    padding: 0;
    white-space: nowrap;
    font-size: 12px;
    flex-shrink: 0;
    border-radius: 50%;
  }
  .mobile-new-chat-btn .mobile-btn-text {
    display: none;
  }
  .mobile-new-chat-btn .mobile-btn-icon {
    font-size: 14px;
  }

  .header-right :deep(.el-button.is-circle) {
    width: 28px;
    height: 28px;
    --el-button-size: 28px;
    margin: 0;
  }

  .header-right :deep(.el-button + .el-button) {
    margin-left: 0;
  }

  :deep(.copy-rounds-trigger) {
    width: 28px;
    height: 28px;
    min-height: 28px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }

}
</style>

<style>
.agent-select-popper.el-popper {
  border-radius: 14px !important;
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 18%, var(--el-border-color-lighter)) !important;
  box-shadow:
    0 20px 48px rgba(15, 23, 42, 0.12),
    0 8px 20px rgba(15, 23, 42, 0.06) !important;
  overflow: hidden;
  padding: 6px !important;
  max-height: 65vh;
}

.agent-select-popper .el-select-dropdown {
  max-height: 65vh !important;
}

/* Override Element Plus internal scrollbar max-height */
.agent-select-popper .el-select-dropdown__wrap,
.agent-select-popper .el-scrollbar__wrap {
  max-height: calc(65vh - 20px) !important;
}

.agent-select-popper .el-select-dropdown__list {
  padding: 4px 0 !important;
}

.agent-select-popper .el-select-dropdown__item {
  border-radius: 8px;
  margin: 2px 0;
  padding: 10px 12px;
  height: auto;
  line-height: normal;
  transition: background 0.15s ease;
}

.agent-select-popper .el-select-dropdown__item.is-selected {
  background: linear-gradient(135deg, color-mix(in srgb, var(--el-color-primary) 10%, transparent), color-mix(in srgb, var(--el-color-primary) 6%, transparent));
  font-weight: 600;
}

.agent-select-popper .el-select-dropdown__item:hover {
  background: var(--el-fill-color-light);
}

html.dark .agent-select-popper.el-popper {
  border-color: rgba(148, 163, 184, 0.15) !important;
  box-shadow:
    0 24px 56px rgba(0, 0, 0, 0.4),
    0 10px 24px rgba(0, 0, 0, 0.2) !important;
}
</style>
