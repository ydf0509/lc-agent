<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { HttpTrace, LlmRoundUsage } from '@/stores/chat'

const props = defineProps<{
  trace: HttpTrace
  usageRound?: LlmRoundUsage
}>()

const isSuccess = computed(() => props.trace.response.ok === true)
const isError = computed(() => Boolean(props.trace.error) || props.trace.response.ok === false)
const tagType = computed(() => (isError.value ? 'danger' : isSuccess.value ? 'success' : 'info'))

const statusText = computed(() => {
  if (props.trace.error) return '失败'
  const status = props.trace.response.status
  return status != null ? String(status) : '未返回'
})

const durationText = computed(() => {
  const ms = props.trace.durationMs
  if (ms == null) return '-'
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
})

const urlText = computed(() => props.trace.request.url || props.trace.model || '未采集')

function fmtTokens(n: number | undefined): string {
  if (n == null || n === 0) return ''
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

const tokenStats = computed(() => {
  const u = props.usageRound
  if (!u) return null
  const parts: { label: string; value: string; cls: string }[] = []
  if (u.inputTokens) parts.push({ label: '输入', value: fmtTokens(u.inputTokens), cls: 'tok-input' })
  if (u.cacheReadTokens) parts.push({ label: '缓存', value: fmtTokens(u.cacheReadTokens), cls: 'tok-cache' })
  if (u.outputTokens) parts.push({ label: '输出', value: fmtTokens(u.outputTokens), cls: 'tok-output' })
  if (u.reasoningTokens) parts.push({ label: '推理', value: fmtTokens(u.reasoningTokens), cls: 'tok-reason' })
  return parts.length > 0 ? parts : null
})

function formatBody(body: string | undefined) {
  if (!body) return '空'
  try {
    return JSON.stringify(JSON.parse(body), null, 2)
  } catch {
    return body
  }
}

const copiedField = ref<string | null>(null)
let copyTimer: ReturnType<typeof setTimeout> | undefined

async function copyField(fieldKey: string, text: string) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', 'true')
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    copiedField.value = fieldKey
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copiedField.value = null }, 1400)
  } catch { /* silent */ }
}

const showModal = ref(false)
const modalTitle = ref('')
const modalContent = ref('')
const searchQuery = ref('')
const activeMatchIndex = ref(0)
const modalBodyRef = ref<HTMLElement | null>(null)

function openBodyModal(title: string, body: string) {
  modalTitle.value = title
  modalContent.value = formatBody(body)
  showModal.value = true
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function renderTextToHtml(value: string): string {
  return escapeHtml(value)
    .replace(/\n/g, '<br>')
    .replace(/ {2}/g, '&nbsp;&nbsp;')
}

const modalRenderedResult = computed(() => {
  const query = searchQuery.value.trim()
  if (!query) return renderTextToHtml(modalContent.value)

  const highlighted = modalContent.value.replace(
    new RegExp(escapeRegExp(query), 'gi'),
    (match) => `@@HIT_START@@${match}@@HIT_END@@`,
  )

  return renderTextToHtml(highlighted)
    .replace(/@@HIT_START@@/g, '<mark class="http-search-hit">')
    .replace(/@@HIT_END@@/g, '</mark>')
})

const matchCount = computed(() => {
  const query = searchQuery.value.trim()
  if (!query) return 0
  const matches = modalContent.value.match(new RegExp(escapeRegExp(query), 'gi'))
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
  const hits = Array.from(container.querySelectorAll('mark.http-search-hit')) as HTMLElement[]
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

const isReqBodyLong = computed(() => (props.trace.request.body?.length || 0) > 300)
const isRespBodyLong = computed(() => (props.trace.response.body?.length || 0) > 300)
</script>

<template>
  <details class="http-trace-block" :class="{ 'is-error': isError }">
    <summary class="http-summary">
      <span class="http-summary-icon">🌐</span>
      <span class="http-summary-title">HTTP 交互 #{{ trace.sequence }}</span>
      <el-tag size="small" :type="tagType" class="http-summary-tag">
        {{ trace.request.method || 'HTTP' }}
      </el-tag>
      <el-tag size="small" :type="tagType" class="http-summary-tag">
        {{ statusText }}
      </el-tag>
      <span class="http-summary-duration">{{ durationText }}</span>
      <span v-if="tokenStats" class="http-token-stats">
        <span v-for="stat in tokenStats" :key="stat.label" class="http-token-item" :class="stat.cls">
          {{ stat.label }} {{ stat.value }}
        </span>
      </span>
      <span class="http-summary-toggle" />
    </summary>

    <div class="http-body">
      <div class="http-row">
        <span class="http-label">URL</span>
        <div class="http-field-row">
          <code class="http-url">{{ urlText }}</code>
          <button class="http-copy-btn" @click.stop="copyField('url', urlText)" :title="copiedField === 'url' ? '已复制' : '复制'">
            {{ copiedField === 'url' ? '✓' : '📋' }}
          </button>
        </div>
      </div>
      <div v-if="trace.provider || trace.model" class="http-row">
        <span class="http-label">模型</span>
        <div class="http-field-row">
          <code>{{ [trace.provider, trace.model].filter(Boolean).join(' / ') }}</code>
          <button class="http-copy-btn" @click.stop="copyField('model', [trace.provider, trace.model].filter(Boolean).join(' / '))" :title="copiedField === 'model' ? '已复制' : '复制'">
            {{ copiedField === 'model' ? '✓' : '📋' }}
          </button>
        </div>
      </div>

      <details class="http-section">
        <summary class="http-section-title">
          <span>Request Headers</span>
          <button class="http-copy-btn" @click.stop="copyField('req-h', formatBody(JSON.stringify(trace.request.headers || {}, null, 2)))">
            {{ copiedField === 'req-h' ? '✓' : '📋' }}
          </button>
        </summary>
        <pre class="http-code">{{ formatBody(JSON.stringify(trace.request.headers || {}, null, 2)) }}</pre>
      </details>
      <details class="http-section">
        <summary class="http-section-title">
          <span>Request Body</span>
          <span class="http-section-actions">
            <button v-if="isReqBodyLong" class="http-expand-btn" @click.stop="openBodyModal('Request Body', trace.request.body)" title="全屏查看">⛶</button>
            <button class="http-copy-btn" @click.stop="copyField('req-b', formatBody(trace.request.body))">
              {{ copiedField === 'req-b' ? '✓' : '📋' }}
            </button>
          </span>
        </summary>
        <pre class="http-code">{{ formatBody(trace.request.body) }}</pre>
      </details>
      <details class="http-section">
        <summary class="http-section-title">
          <span>Response Headers</span>
          <button class="http-copy-btn" @click.stop="copyField('resp-h', formatBody(JSON.stringify(trace.response.headers || {}, null, 2)))">
            {{ copiedField === 'resp-h' ? '✓' : '📋' }}
          </button>
        </summary>
        <pre class="http-code">{{ formatBody(JSON.stringify(trace.response.headers || {}, null, 2)) }}</pre>
      </details>
      <details class="http-section">
        <summary class="http-section-title">
          <span>Response Body</span>
          <span class="http-section-actions">
            <button v-if="isRespBodyLong" class="http-expand-btn" @click.stop="openBodyModal('Response Body', trace.response.body)" title="全屏查看">⛶</button>
            <button class="http-copy-btn" @click.stop="copyField('resp-b', formatBody(trace.response.body))">
              {{ copiedField === 'resp-b' ? '✓' : '📋' }}
            </button>
          </span>
        </summary>
        <pre class="http-code">{{ formatBody(trace.response.body) }}</pre>
      </details>
      <div v-if="trace.error" class="http-error">请求失败：{{ trace.error }}</div>
    </div>
  </details>

  <teleport to="body">
    <div v-if="showModal" class="http-modal-backdrop" @click="showModal = false">
      <div class="http-modal" role="dialog" aria-modal="true" @click.stop>
        <div class="http-modal-header">
          <div class="http-modal-title-wrap">
            <span class="http-modal-kicker">HTTP #{{ trace.sequence }}</span>
            <span class="http-modal-title">{{ modalTitle }}</span>
          </div>
          <div class="http-modal-actions">
            <button class="http-copy-btn-lg" @click="copyField('modal', modalContent)">
              {{ copiedField === 'modal' ? '已复制 ✓' : '复制全部' }}
            </button>
            <button class="http-modal-close" aria-label="关闭" @click="showModal = false">✕</button>
          </div>
        </div>
        <div class="http-modal-toolbar">
          <input
            v-model="searchQuery"
            class="http-search-input"
            type="text"
            placeholder="搜索关键字..."
            @keydown.enter.prevent="jumpToNextMatch"
          />
          <div class="http-search-actions">
            <span v-if="searchQuery" class="http-search-count">{{ activeMatchLabel }}</span>
            <button class="http-search-btn" :disabled="!matchCount" @click="jumpToPrevMatch">↑</button>
            <button class="http-search-btn" :disabled="!matchCount" @click="jumpToNextMatch">↓</button>
          </div>
        </div>
        <div class="http-modal-content">
          <div ref="modalBodyRef" class="http-modal-body" v-html="modalRenderedResult" />
        </div>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.http-trace-block {
  margin: 8px 0;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-color-primary);
  border-radius: 8px;
  background: var(--el-fill-color-light);
  overflow: hidden;
}
.http-trace-block.is-error {
  border-left-color: var(--el-color-danger);
}

.http-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.http-summary::-webkit-details-marker {
  display: none;
}
.http-summary-icon {
  font-size: 13px;
}
.http-summary-title {
  font-weight: 600;
  white-space: nowrap;
}
.http-summary-tag {
  flex-shrink: 0;
}
.http-summary-duration {
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.http-token-stats {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 4px;
}
.http-token-item {
  font-size: 11px;
  padding: 0 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: nowrap;
}
.tok-input {
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
}
.tok-cache {
  color: var(--el-color-success);
  background: color-mix(in srgb, var(--el-color-success) 10%, transparent);
}
.tok-output {
  color: #c58f22;
  background: color-mix(in srgb, #c58f22 10%, transparent);
}
.tok-reason {
  color: var(--el-color-warning);
  background: color-mix(in srgb, var(--el-color-warning) 10%, transparent);
}
.http-summary-toggle {
  margin-left: auto;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}
.http-trace-block[open] .http-summary-toggle::before {
  content: '收起';
}
.http-trace-block:not([open]) .http-summary-toggle::before {
  content: '展开';
}

.http-body {
  padding: 4px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.http-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}
.http-label {
  color: var(--el-text-color-secondary);
  font-size: 11px;
}
.http-field-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.http-field-row code {
  flex: 1;
  min-width: 0;
}
.http-url {
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.http-section {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 6px;
}
.http-section-title {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-regular);
  padding: 2px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.http-section-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}
.http-copy-btn {
  flex-shrink: 0;
  padding: 1px 4px;
  font-size: 11px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  color: var(--el-text-color-secondary);
  opacity: 0.6;
  transition: all 0.15s ease;
}
.http-copy-btn:hover {
  opacity: 1;
  border-color: var(--el-border-color);
  background: var(--el-fill-color);
}
.http-expand-btn {
  flex-shrink: 0;
  padding: 1px 6px;
  font-size: 13px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  color: var(--el-color-primary);
  opacity: 0.7;
  transition: all 0.15s ease;
}
.http-expand-btn:hover {
  opacity: 1;
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}
.http-code {
  margin: 4px 0 0;
  padding: 8px;
  border-radius: 6px;
  background: var(--el-fill-color);
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
.http-error {
  color: var(--el-color-danger);
  font-size: 12px;
  padding: 6px 8px;
  background: color-mix(in srgb, var(--el-color-danger) 10%, transparent);
  border-radius: 6px;
}

/* Modal */
.http-modal-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--el-bg-color-page) 70%, transparent);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.http-modal {
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
.http-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  gap: 12px;
  flex: 0 0 auto;
}
.http-modal-title-wrap {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.http-modal-kicker {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
.http-modal-title {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
}
.http-modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.http-copy-btn-lg {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  transition: all 0.15s ease;
}
.http-copy-btn-lg:hover {
  background: var(--el-fill-color-light);
  border-color: var(--el-color-primary-light-5);
}
.http-modal-close {
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
.http-modal-close:hover {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}
.http-modal-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: color-mix(in srgb, var(--el-fill-color-light) 78%, transparent);
}
.http-search-input {
  flex: 1 1 auto;
  min-width: 0;
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  outline: none;
  font-size: 13px;
}
.http-search-input:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--el-color-primary) 14%, transparent);
}
.http-search-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.http-search-count {
  min-width: 42px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: right;
}
.http-search-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
}
.http-search-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.http-modal-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}
.http-modal-body {
  min-height: 100%;
  padding: 16px;
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  color: var(--el-text-color-regular);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.http-modal-body :deep(.http-search-hit) {
  background: rgba(250, 204, 21, 0.35);
  color: inherit;
  padding: 0 1px;
  border-radius: 2px;
}
.http-modal-body :deep(.http-search-hit.is-active) {
  background: rgba(245, 158, 11, 0.78);
}

@media (max-width: 520px) {
  .http-summary {
    flex-wrap: wrap;
    gap: 4px 6px;
    padding: 8px 10px;
  }
  .http-summary-title {
    white-space: nowrap;
  }
  .http-summary-toggle {
    order: 10;
  }
  .http-token-stats {
    width: 100%;
    margin-left: 0;
    margin-top: 2px;
    flex-wrap: wrap;
  }
}

@media (max-width: 520px) {
  .http-modal-backdrop {
    align-items: stretch;
    justify-content: stretch;
    padding: max(8px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left));
    background: color-mix(in srgb, var(--el-bg-color-page) 88%, transparent);
  }
  .http-modal {
    width: 100%;
    max-height: none;
    height: 100%;
    border-radius: 12px;
    min-width: 0;
  }
  .http-modal-header {
    position: sticky;
    top: 0;
    z-index: 1;
    padding: 10px;
    background: var(--el-bg-color);
    gap: 8px;
  }
  .http-modal-kicker {
    display: none;
  }
  .http-modal-title {
    font-size: 12px;
  }
  .http-modal-close {
    width: 34px;
    height: 34px;
    font-size: 18px;
  }
  .http-modal-toolbar {
    padding: 8px 10px;
    gap: 8px;
    flex-wrap: wrap;
  }
  .http-search-input {
    width: 100%;
    height: 36px;
  }
  .http-search-actions {
    width: 100%;
    justify-content: flex-end;
  }
  .http-search-count {
    margin-right: auto;
    text-align: left;
  }
  .http-modal-body {
    padding: 12px 10px 18px;
    font-size: 12px;
    line-height: 1.65;
  }
}
</style>
