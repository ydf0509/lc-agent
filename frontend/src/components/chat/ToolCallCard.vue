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
      <div class="tool-result-rendered" v-html="renderedResult" />
      <button v-if="isLong" class="fullscreen-btn" @click.stop="showModal = true" title="查看完整内容">⛶</button>
    </div>
    </template>

    <teleport to="body">
      <div v-if="showModal" class="tool-modal-backdrop" @click="showModal = false">
        <div class="tool-modal" role="dialog" aria-modal="true" @click.stop>
          <div class="tool-modal-header">
            <div class="tool-modal-title-wrap">
              <span class="tool-modal-kicker">工具结果</span>
              <span class="tool-modal-title">{{ toolCall.name }}</span>
            </div>
            <div class="modal-actions">
              <button class="tool-modal-close" aria-label="关闭" @click="showModal = false">✕</button>
            </div>
          </div>
          <div class="tool-modal-toolbar">
            <input
              v-model="searchQuery"
              class="tool-search-input"
              type="text"
              placeholder="搜索关键字..."
              @keydown.enter.prevent="jumpToNextMatch"
            />
            <div class="tool-search-actions">
              <span v-if="searchQuery" class="tool-search-count">{{ activeMatchLabel }}</span>
              <button class="tool-search-btn" :disabled="!matchCount" @click="jumpToPrevMatch">↑</button>
              <button class="tool-search-btn" :disabled="!matchCount" @click="jumpToNextMatch">↓</button>
            </div>
          </div>
          <div class="tool-modal-content">
            <div ref="modalBodyRef" class="tool-modal-body rendered" v-html="modalRenderedResult" />
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Loading, Check, Tools } from '@element-plus/icons-vue'
import type { ToolCall } from '@/stores/chat'

const props = defineProps<{ toolCall: ToolCall; collapsed?: boolean }>()
const showModal = ref(false)
const isCollapsed = ref(props.collapsed ?? false)
const userToggled = ref(false)
const searchQuery = ref('')
const activeMatchIndex = ref(0)
const modalBodyRef = ref<HTMLElement | null>(null)

function toggleCollapse() {
  userToggled.value = true
  isCollapsed.value = !isCollapsed.value
}

watch(() => props.collapsed, (collapsed) => {
  if (userToggled.value || collapsed === undefined) return
  isCollapsed.value = collapsed
}, { immediate: true })

const isLong = computed(() => (props.toolCall.result?.length || 0) > 300)

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizeResult(value?: string): string {
  if (!value) return ''
  return value
    .replace(/\\u3000/g, '　')
    .replace(/\\n/g, '\n')
}

function renderTextToHtml(value: string): string {
  return escapeHtml(value)
    .replace(/\n/g, '<br>')
    .replace(/ {2}/g, '&nbsp;&nbsp;')
}

const normalizedResult = computed(() => normalizeResult(props.toolCall.result))

const renderedResult = computed(() => renderTextToHtml(normalizedResult.value))

const modalRenderedResult = computed(() => {
  const query = searchQuery.value.trim()
  if (!query) return renderedResult.value

  const highlighted = normalizedResult.value.replace(
    new RegExp(escapeRegExp(query), 'gi'),
    (match) => `@@HIT_START@@${match}@@HIT_END@@`,
  )

  return renderTextToHtml(highlighted)
    .replace(/@@HIT_START@@/g, '<mark class="tool-search-hit">')
    .replace(/@@HIT_END@@/g, '</mark>')
})

const matchCount = computed(() => {
  const query = searchQuery.value.trim()
  if (!query) return 0
  const matches = normalizedResult.value.match(new RegExp(escapeRegExp(query), 'gi'))
  return matches?.length || 0
})

const activeMatchLabel = computed(() => {
  if (!matchCount.value) return '0/0'
  return `${activeMatchIndex.value + 1}/${matchCount.value}`
})

async function syncSearchHighlights() {
  await nextTick()
  const container = modalBodyRef.value
  if (!container) return
  const hits = Array.from(container.querySelectorAll('mark.tool-search-hit')) as HTMLElement[]
  hits.forEach((hit, index) => {
    hit.classList.toggle('is-active', index === activeMatchIndex.value)
  })
  if (hits.length > 0) {
    hits[activeMatchIndex.value]?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
}

function jumpToNextMatch() {
  if (!matchCount.value) return
  activeMatchIndex.value = (activeMatchIndex.value + 1) % matchCount.value
}

function jumpToPrevMatch() {
  if (!matchCount.value) return
  activeMatchIndex.value = (activeMatchIndex.value - 1 + matchCount.value) % matchCount.value
}

watch(searchQuery, () => {
  activeMatchIndex.value = 0
  syncSearchHighlights()
})

watch(activeMatchIndex, () => {
  syncSearchHighlights()
})

watch(showModal, (visible) => {
  if (!visible) {
    searchQuery.value = ''
    activeMatchIndex.value = 0
    return
  }
  syncSearchHighlights()
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

.tool-result-rendered {
  margin: 0;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  color: var(--el-text-color-secondary);
  line-height: 1.65;
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
  width: min(900px, calc(100vw - 80px));
  max-height: min(80vh, 760px);
  min-height: 0;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 16px 48px color-mix(in srgb, var(--el-bg-color-page) 50%, transparent);
}

.tool-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  gap: 12px;
  flex: 0 0 auto;
}

.tool-modal-title-wrap {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tool-modal-kicker {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
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
  min-width: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.tool-modal-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: color-mix(in srgb, var(--el-fill-color-light) 78%, transparent);
}

.tool-search-input {
  flex: 1 1 auto;
  min-width: 0;
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  outline: none;
}

.tool-search-input:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--el-color-primary) 14%, transparent);
}

.tool-search-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.tool-search-count {
  min-width: 42px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: right;
}

.tool-search-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
}

.tool-search-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tool-modal-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.tool-modal-body {
  min-height: 100%;
  padding: 16px;
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  color: var(--el-text-color-regular);
}

.tool-modal-body.rendered {
  white-space: normal;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.tool-modal-body :deep(.tool-search-hit),
.tool-modal-body.rendered :deep(.tool-search-hit) {
  background: rgba(250, 204, 21, 0.35);
  color: inherit;
  padding: 0 1px;
  border-radius: 2px;
}

.tool-modal-body :deep(.tool-search-hit.is-active),
.tool-modal-body.rendered :deep(.tool-search-hit.is-active) {
  background: rgba(245, 158, 11, 0.78);
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

  .tool-modal-backdrop {
    align-items: stretch;
    justify-content: stretch;
    padding: max(8px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left));
    background: color-mix(in srgb, var(--el-bg-color-page) 88%, transparent);
  }

  .tool-modal {
    width: 100%;
    max-height: none;
    height: 100%;
    border-radius: 12px;
    min-width: 0;
  }

  .tool-modal-header {
    position: sticky;
    top: 0;
    z-index: 1;
    padding: 10px 10px 9px;
    background: var(--el-bg-color);
    gap: 8px;
  }

  .tool-modal-title-wrap {
    flex: 1 1 auto;
  }

  .tool-modal-title {
    font-size: 12px;
  }

  .tool-modal-kicker {
    display: none;
  }

  .modal-actions {
    gap: 6px;
  }

  .modal-toggle-btn {
    padding: 5px 8px;
    font-size: 12px;
    white-space: nowrap;
  }

  .tool-modal-close {
    width: 34px;
    height: 34px;
    font-size: 18px;
  }

  .tool-modal-toolbar {
    padding: 8px 10px;
    gap: 8px;
    flex-wrap: wrap;
  }

  .tool-search-input {
    width: 100%;
    height: 36px;
  }

  .tool-search-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .tool-search-count {
    margin-right: auto;
    text-align: left;
  }

  .tool-modal-content {
    flex: 1 1 auto;
  }

  .tool-modal-body {
    padding: 12px 10px 18px;
    font-size: 12px;
    line-height: 1.65;
  }
}
</style>
