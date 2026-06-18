<template>
  <div class="tool-call-card" :class="[toolCall.status, { 'is-collapsed': isCollapsed }]">
    <div class="tool-header" @click.stop="toggleCollapse">
      <span class="collapse-icon">{{ isCollapsed ? '▸' : '▾' }}</span>
      <el-icon v-if="toolCall.status === 'running'" class="spinning">
        <Loading />
      </el-icon>
      <el-icon v-else-if="toolCall.status === 'done'" style="color: var(--el-color-success)">
        <Check />
      </el-icon>
      <span class="tool-kind">
        <el-icon><Tools /></el-icon>
        工具调用
      </span>
      <span class="tool-name">{{ toolCall.name }}</span>
      <el-tag size="small" :type="statusType">{{ statusLabel }}</el-tag>
      <span class="tool-meta" v-if="toolCall.status === 'done'">
        <span v-if="toolCall.duration" class="meta-item">⏱ {{ formatDuration(toolCall.duration) }}</span>
        <span v-if="toolCall.resultLength" class="meta-item">📦 {{ formatSize(toolCall.resultLength) }}</span>
      </span>
    </div>
    <template v-if="!isCollapsed">
    <div v-if="toolCall.args && Object.keys(toolCall.args).length > 0" class="tool-args">
      <div v-for="arg in formatArgs(toolCall.args)" :key="arg.key" class="arg-row">
        <span class="arg-key">{{ arg.key }}:</span>
        <span class="arg-value">{{ arg.value }}</span>
      </div>
    </div>
    <div v-if="toolCall.result" class="tool-result">
      <pre>{{ toolCall.result }}</pre>
      <button v-if="isLong" class="fullscreen-btn" @click.stop="showModal = true" title="查看完整内容">⛶</button>
    </div>
    </template>

    <teleport to="body">
      <div v-if="showModal" class="tool-modal-backdrop" @click="showModal = false">
        <div class="tool-modal" @click.stop>
          <div class="tool-modal-header">
            <span class="tool-modal-title">{{ toolCall.name }}</span>
            <div class="modal-actions">
              <button class="modal-toggle-btn" :class="{ active: renderMode }" @click="renderMode = !renderMode">
                {{ renderMode ? '📄 原文' : '✨ 渲染' }}
              </button>
              <button class="tool-modal-close" @click="showModal = false">✕</button>
            </div>
          </div>
          <pre v-if="!renderMode" class="tool-modal-body">{{ toolCall.result }}</pre>
          <div v-else class="tool-modal-body rendered" v-html="renderedResult" />
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Loading, Check, Tools } from '@element-plus/icons-vue'
import type { ToolCall } from '@/stores/chat'

const props = defineProps<{ toolCall: ToolCall; collapsed?: boolean }>()
const showModal = ref(false)
const renderMode = ref(false)
const isCollapsed = ref(props.collapsed ?? false)
const userToggled = ref(false)

function toggleCollapse() {
  userToggled.value = true
  isCollapsed.value = !isCollapsed.value
}

watch(() => props.collapsed, (collapsed) => {
  if (userToggled.value || collapsed === undefined) return
  isCollapsed.value = collapsed
}, { immediate: true })

const isLong = computed(() => (props.toolCall.result?.length || 0) > 300)

const renderedResult = computed(() => {
  if (!props.toolCall.result) return ''
  return props.toolCall.result
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\\n/g, '\n')
    .replace(/\n/g, '<br>')
    .replace(/  /g, '&nbsp;&nbsp;')
})

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatSize(len: number): string {
  if (len < 1024) return `${len} chars`
  return `${(len / 1024).toFixed(1)}K chars`
}

function formatArgs(args: Record<string, any>): { key: string; value: string }[] {
  return Object.entries(args).map(([k, v]) => {
    let val = typeof v === 'string' ? v : JSON.stringify(v)
    if (val.length > 100) val = val.slice(0, 100) + '...'
    return { key: k, value: val }
  })
}

const statusType = computed(() => {
  switch (props.toolCall.status) {
    case 'running': return 'warning'
    case 'done': return 'success'
    case 'error': return 'danger'
    default: return 'info'
  }
})

const statusLabel = computed(() => {
  switch (props.toolCall.status) {
    case 'running': return '执行中'
    case 'done': return '完成'
    case 'error': return '错误'
    default: return '等待'
  }
})
</script>

<style scoped>
.tool-call-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 6px 0;
  background: var(--el-fill-color-light);
  border-left: 3px solid var(--el-text-color-secondary);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.tool-call-card.running {
  border-left-color: var(--el-color-primary);
  box-shadow: 0 0 12px color-mix(in srgb, var(--el-color-primary) 8%, transparent);
}

.tool-call-card.done {
  border-left-color: var(--el-color-success);
}

.tool-call-card.error {
  border-left-color: var(--el-color-danger);
}

.tool-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.tool-header:hover {
  opacity: 0.85;
}

.collapse-icon {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  width: 12px;
  flex-shrink: 0;
}

.is-collapsed {
  padding: 6px 14px;
}

.tool-name {
  flex: 1 1 180px;
  min-width: 0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--el-color-primary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-kind {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 999px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.tool-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex-shrink: 0;
}

.meta-item {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.tool-args {
  margin-top: 6px;
  padding: 5px 8px;
  background: var(--el-fill-color);
  border-radius: 4px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
}

.arg-row {
  display: flex;
  gap: 6px;
  padding: 1px 0;
  line-height: 1.5;
}

.arg-key {
  color: var(--el-color-primary);
  flex-shrink: 0;
  font-weight: 500;
}

.arg-value {
  color: var(--el-text-color-regular);
  word-break: break-all;
}

.tool-result {
  margin-top: 8px;
  padding: 8px 10px;
  background: var(--el-fill-color);
  border-radius: 6px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color);
  position: relative;
}

.tool-result pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--el-text-color-secondary);
}

.fullscreen-btn {
  position: sticky;
  bottom: 0;
  float: right;
  padding: 2px 8px;
  font-size: 14px;
  color: var(--el-color-primary);
  background: var(--el-bg-color);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.fullscreen-btn:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.tool-modal-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--el-bg-color-page) 70%, transparent);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.tool-modal {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 16px 48px color-mix(in srgb, var(--el-bg-color-page) 50%, transparent);
  min-width: 500px;
}

.tool-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  gap: 12px;
}

.modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-toggle-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-toggle-btn:hover {
  background: var(--el-fill-color-light);
}

.modal-toggle-btn.active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.tool-modal-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.tool-modal-close {
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

.tool-modal-close:hover {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.tool-modal-body {
  flex: 1;
  padding: 16px;
  margin: 0;
  overflow: auto;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--el-text-color-regular);
}

.tool-modal-body.rendered {
  white-space: normal;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.spinning {
  animation: spin 1s linear infinite;
  color: var(--el-color-primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 520px) {
  .tool-call-card {
    padding: 9px 10px;
  }

  .is-collapsed {
    padding: 7px 10px;
  }

  .tool-header {
    gap: 6px;
  }

  .tool-name {
    flex-basis: 100%;
    order: 10;
    padding-left: 24px;
    max-width: 100%;
  }

  .tool-meta {
    margin-left: 0;
    gap: 7px;
  }
}
</style>
