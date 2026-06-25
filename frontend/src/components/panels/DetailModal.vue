<template>
  <teleport to="body">
    <div v-if="visible" class="detail-modal-backdrop" @click="close">
      <div class="detail-modal" role="dialog" aria-modal="true" @click.stop>
        <div class="detail-modal-header">
          <div class="detail-modal-title-wrap">
            <span class="detail-modal-kicker">{{ modeKicker }}</span>
            <span class="detail-modal-title">{{ title }}</span>
          </div>
          <button class="detail-modal-close" aria-label="关闭" @click="close">✕</button>
        </div>
        <div class="detail-modal-toolbar">
          <input
            v-model="searchQuery"
            class="detail-search-input"
            type="text"
            placeholder="搜索关键字..."
            @keydown.enter.prevent="jumpToNextMatch"
          />
          <div class="detail-search-actions">
            <span v-if="searchQuery" class="detail-search-count">{{ activeMatchLabel }}</span>
            <button class="detail-search-btn" :disabled="!matchCount" @click="jumpToPrevMatch">↑</button>
            <button class="detail-search-btn" :disabled="!matchCount" @click="jumpToNextMatch">↓</button>
          </div>
        </div>
        <div class="detail-modal-content">
          <div ref="modalBodyRef" class="detail-modal-body" v-html="displayHtml" />
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  visible: boolean
  title: string
  mode: 'tool-group' | 'mcp' | 'skill'
  data: any
}>()

const emit = defineEmits<{ 'update:visible': [value: boolean] }>()

const searchQuery = ref('')
const activeMatchIndex = ref(0)
const modalBodyRef = ref<HTMLElement | null>(null)

const modeKicker = computed(() => {
  switch (props.mode) {
    case 'tool-group': return '工具组'
    case 'mcp': return 'MCP 服务器'
    case 'skill': return 'Skill'
    default: return '详情'
  }
})

function close() {
  emit('update:visible', false)
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

function highlightText(text: string, query: string): string {
  const escaped = escapeHtml(text)
  if (!query) return escaped
  const highlighted = text.replace(
    new RegExp(escapeRegExp(query), 'gi'),
    (match) => `@@HIT_START@@${match}@@HIT_END@@`,
  )
  return escapeHtml(highlighted)
    .replace(/@@HIT_START@@/g, '<mark class="detail-search-hit">')
    .replace(/@@HIT_END@@/g, '</mark>')
}

function buildToolGroupHtml(data: any, query: string): string {
  let html = ''
  if (data.description) {
    html += `<div class="detail-section-desc">${highlightText(data.description, query)}</div>`
  }
  for (const tool of data.tools || []) {
    html += '<div class="detail-tool-item">'
    html += `<div class="detail-tool-name">${highlightText(tool.name, query)}</div>`
    if (tool.description) {
      html += `<div class="detail-tool-desc">${highlightText(tool.description, query)}</div>`
    }
    if (tool.input_schema) {
      const schemaJson = JSON.stringify(tool.input_schema, null, 2)
      html += `<details class="detail-schema"><summary>参数 Schema</summary><pre class="detail-schema-pre">${highlightText(schemaJson, query)}</pre></details>`
    }
    html += '</div>'
  }
  return html
}

function buildMcpHtml(data: any, query: string): string {
  let html = '<div class="detail-info-grid">'
  html += `<div class="detail-info-row"><span class="detail-info-label">类型</span><span>${highlightText(data.type || '', query)}</span></div>`
  if (data.command) {
    html += `<div class="detail-info-row"><span class="detail-info-label">命令</span><span class="detail-mono">${highlightText(data.command, query)}</span></div>`
  }
  if (data.url) {
    html += `<div class="detail-info-row"><span class="detail-info-label">URL</span><span class="detail-mono">${highlightText(data.url, query)}</span></div>`
  }
  html += `<div class="detail-info-row"><span class="detail-info-label">状态</span><span>${highlightText(data.status || '', query)}</span></div>`
  if (data.error) {
    html += `<div class="detail-info-row detail-error"><span class="detail-info-label">错误</span><span>${highlightText(data.error, query)}</span></div>`
  }
  html += '</div>'

  const schemas = data.tool_schemas || []
  if (schemas.length > 0) {
    html += '<div class="detail-tools-section"><div class="detail-tools-heading">工具列表</div>'
    for (const tool of schemas) {
      html += '<div class="detail-tool-item">'
      html += `<div class="detail-tool-name">${highlightText(tool.name, query)}</div>`
      if (tool.description) {
        html += `<div class="detail-tool-desc">${highlightText(tool.description, query)}</div>`
      }
      if (tool.input_schema) {
        const schemaJson = JSON.stringify(tool.input_schema, null, 2)
        html += `<details class="detail-schema"><summary>参数 Schema</summary><pre class="detail-schema-pre">${highlightText(schemaJson, query)}</pre></details>`
      }
      html += '</div>'
    }
    html += '</div>'
  } else if (data.tools?.length) {
    html += '<div class="detail-tools-section"><div class="detail-tools-heading">工具列表</div><div class="detail-tool-tags">'
    for (const name of data.tools) {
      html += `<span class="detail-tool-tag">${highlightText(name, query)}</span>`
    }
    html += '</div></div>'
  }
  return html
}

function buildSkillHtml(data: any, query: string): string {
  let html = ''
  if (data.description) {
    html += `<div class="detail-section-desc">${highlightText(data.description, query)}</div>`
  }
  const body = data.body || data.content
  if (body) {
    const mdHtml = renderMarkdown(body)
    if (query) {
      const highlighted = body.replace(
        new RegExp(escapeRegExp(query), 'gi'),
        (match: string) => `@@HIT_START@@${match}@@HIT_END@@`,
      )
      const rendered = renderMarkdown(highlighted)
        .replace(/@@HIT_START@@/g, '<mark class="detail-search-hit">')
        .replace(/@@HIT_END@@/g, '</mark>')
      html += `<div class="detail-skill-content markdown-body">${rendered}</div>`
    } else {
      html += `<div class="detail-skill-content markdown-body">${mdHtml}</div>`
    }
  } else {
    html += `<div class="detail-section-desc" style="color:var(--el-text-color-secondary)">暂无详细内容</div>`
  }
  return html
}

const baseHtml = computed(() => {
  if (!props.data) return ''
  const query = searchQuery.value.trim()
  switch (props.mode) {
    case 'tool-group': return buildToolGroupHtml(props.data, query)
    case 'mcp': return buildMcpHtml(props.data, query)
    case 'skill': return buildSkillHtml(props.data, query)
    default: return ''
  }
})

const displayHtml = computed(() => baseHtml.value)

const searchableText = computed(() => {
  if (!props.data) return ''
  switch (props.mode) {
    case 'tool-group': {
      const parts = [props.data.description || '']
      for (const tool of props.data.tools || []) {
        parts.push(tool.name, tool.description || '')
        if (tool.input_schema) parts.push(JSON.stringify(tool.input_schema))
      }
      return parts.join('\n')
    }
    case 'mcp': {
      const parts = [props.data.type || '', props.data.command || '', props.data.url || '', props.data.status || '', props.data.error || '']
      for (const tool of props.data.tool_schemas || []) {
        parts.push(tool.name, tool.description || '')
        if (tool.input_schema) parts.push(JSON.stringify(tool.input_schema))
      }
      for (const name of props.data.tools || []) parts.push(name)
      return parts.join('\n')
    }
    case 'skill': {
      return [props.data.description || '', props.data.body || ''].join('\n')
    }
    default:
      return ''
  }
})

const matchCount = computed(() => {
  const query = searchQuery.value.trim()
  if (!query) return 0
  const matches = searchableText.value.match(new RegExp(escapeRegExp(query), 'gi'))
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
  const hits = Array.from(container.querySelectorAll('mark.detail-search-hit')) as HTMLElement[]
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

watch(() => props.visible, (visible) => {
  if (!visible) {
    searchQuery.value = ''
    activeMatchIndex.value = 0
    return
  }
  syncSearchHighlights()
})

watch(baseHtml, () => {
  syncSearchHighlights()
})
</script>

<style scoped>
.detail-modal-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--el-bg-color-page) 70%, transparent);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.detail-modal {
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

.detail-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  gap: 12px;
  flex: 0 0 auto;
}

.detail-modal-title-wrap {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-modal-kicker {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.detail-modal-title {
  min-width: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-modal-close {
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
  flex-shrink: 0;
}

.detail-modal-close:hover {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.detail-modal-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: color-mix(in srgb, var(--el-fill-color-light) 78%, transparent);
}

.detail-search-input {
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

.detail-search-input:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--el-color-primary) 14%, transparent);
}

.detail-search-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.detail-search-count {
  min-width: 42px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: right;
}

.detail-search-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
}

.detail-search-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.detail-modal-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.detail-modal-body {
  min-height: 100%;
  padding: 16px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}

.detail-modal-body :deep(.detail-section-desc) {
  margin-bottom: 12px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.detail-modal-body :deep(.detail-tool-item) {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.detail-modal-body :deep(.detail-tool-item:last-child) {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.detail-modal-body :deep(.detail-tool-name) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.detail-modal-body :deep(.detail-tool-desc) {
  font-size: 12px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin-bottom: 6px;
}

.detail-modal-body :deep(.detail-schema) {
  margin-top: 6px;
}

.detail-modal-body :deep(.detail-schema summary) {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  user-select: none;
}

.detail-modal-body :deep(.detail-schema-pre) {
  margin: 6px 0 0;
  padding: 10px 12px;
  background: var(--el-fill-color);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.detail-modal-body :deep(.detail-info-grid) {
  margin-bottom: 16px;
}

.detail-modal-body :deep(.detail-info-row) {
  display: flex;
  gap: 10px;
  padding: 4px 0;
  font-size: 12px;
  line-height: 1.5;
}

.detail-modal-body :deep(.detail-info-label) {
  flex-shrink: 0;
  min-width: 48px;
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

.detail-modal-body :deep(.detail-mono) {
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}

.detail-modal-body :deep(.detail-error) {
  color: var(--el-color-danger);
}

.detail-modal-body :deep(.detail-tools-section) {
  margin-top: 8px;
}

.detail-modal-body :deep(.detail-tools-heading) {
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.detail-modal-body :deep(.detail-tool-tags) {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail-modal-body :deep(.detail-tool-tag) {
  padding: 2px 8px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  background: var(--el-fill-color);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}

.detail-modal-body :deep(.detail-file-path) {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-bottom: 10px;
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}

.detail-modal-body :deep(.detail-skill-content) {
  margin-top: 8px;
}

.detail-modal-body :deep(.detail-search-hit) {
  background: rgba(250, 204, 21, 0.35);
  color: inherit;
  padding: 0 1px;
  border-radius: 2px;
}

.detail-modal-body :deep(.detail-search-hit.is-active) {
  background: rgba(245, 158, 11, 0.78);
}

@media (max-width: 520px) {
  .detail-modal-backdrop {
    align-items: stretch;
    justify-content: stretch;
    padding: max(8px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left));
    background: color-mix(in srgb, var(--el-bg-color-page) 88%, transparent);
  }

  .detail-modal {
    width: 100%;
    max-height: none;
    height: 100%;
    border-radius: 12px;
    min-width: 0;
  }

  .detail-modal-header {
    padding: 10px 10px 9px;
    gap: 8px;
  }

  .detail-modal-kicker {
    display: none;
  }

  .detail-modal-toolbar {
    padding: 8px 10px;
    flex-wrap: wrap;
  }

  .detail-search-input {
    width: 100%;
    height: 36px;
  }

  .detail-search-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .detail-search-count {
    margin-right: auto;
    text-align: left;
  }

  .detail-modal-body {
    padding: 12px 10px 18px;
    font-size: 12px;
  }
}
</style>
