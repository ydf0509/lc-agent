<template>
  <div class="tool-call-card" :class="[toolCall.status, { 'is-collapsed': isCollapsed }]">
    <div class="tool-header" @click="toggleCollapse">
      <span class="collapse-icon">{{ isCollapsed ? '▸' : '▾' }}</span>
      <el-icon v-if="toolCall.status === 'running'" class="spinning">
        <Loading />
      </el-icon>
      <el-icon v-else-if="toolCall.status === 'done'" style="color: var(--lc-success)">
        <Check />
      </el-icon>
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
import { computed, ref } from 'vue'
import { Loading, Check } from '@element-plus/icons-vue'
import type { ToolCall } from '@/stores/chat'

const props = defineProps<{ toolCall: ToolCall; collapsed?: boolean }>()
const showModal = ref(false)
const renderMode = ref(false)
const isCollapsed = ref(props.collapsed ?? false)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

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
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-md);
  padding: 10px 14px;
  margin: 6px 0;
  background: var(--lc-glass-bg);
  border-left: 3px solid var(--lc-text-secondary);
  transition: border-color var(--lc-transition-normal), box-shadow var(--lc-transition-normal);
  animation: float-in var(--lc-transition-slow) ease both;
}

.tool-call-card.running {
  border-left-color: var(--lc-accent);
  box-shadow: 0 0 12px rgba(88, 166, 255, 0.08);
}

.tool-call-card.done {
  border-left-color: var(--lc-success);
}

.tool-call-card.error {
  border-left-color: var(--lc-danger);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.tool-header:hover {
  opacity: 0.85;
}

.collapse-icon {
  font-size: 10px;
  color: #8b949e;
  width: 12px;
  flex-shrink: 0;
}

.is-collapsed {
  padding: 6px 14px;
}

.tool-name {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--lc-accent);
  font-weight: 500;
}

.tool-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.meta-item {
  font-size: 11px;
  color: #8b949e;
  white-space: nowrap;
}

.tool-args {
  margin-top: 6px;
  padding: 5px 8px;
  background: rgba(0, 0, 0, 0.15);
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
  color: #79c0ff;
  flex-shrink: 0;
  font-weight: 500;
}

.arg-value {
  color: #d2a8ff;
  word-break: break-all;
}

.tool-result {
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--lc-radius-sm);
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--lc-glass-border);
  position: relative;
}

.tool-result pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--lc-text-secondary);
}

.fullscreen-btn {
  position: sticky;
  bottom: 0;
  float: right;
  padding: 2px 8px;
  font-size: 14px;
  color: #58a6ff;
  background: rgba(13, 17, 23, 0.9);
  border: 1px solid rgba(88, 166, 255, 0.3);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.fullscreen-btn:hover {
  background: rgba(88, 166, 255, 0.15);
  border-color: #58a6ff;
}

.tool-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.tool-modal {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
  min-width: 500px;
}

.tool-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #30363d;
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
  border: 1px solid #30363d;
  border-radius: 6px;
  background: #21262d;
  color: #c9d1d9;
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-toggle-btn:hover {
  background: #30363d;
}

.modal-toggle-btn.active {
  background: #1f3d5e;
  border-color: #58a6ff;
  color: #58a6ff;
}

.tool-modal-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #58a6ff;
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
  color: #8b949e;
  font-size: 16px;
  cursor: pointer;
}

.tool-modal-close:hover {
  background: #21262d;
  color: #e6edf3;
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
  color: #c9d1d9;
}

.tool-modal-body.rendered {
  white-space: normal;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.spinning {
  animation: spin 1s linear infinite;
  color: var(--lc-accent);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
