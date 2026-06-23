<script setup lang="ts">
import { computed } from 'vue'
import type { HttpTrace } from '@/stores/chat'

const props = defineProps<{
  trace: HttpTrace
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

function formatBody(body: string | undefined) {
  if (!body) return '空'
  try {
    return JSON.stringify(JSON.parse(body), null, 2)
  } catch {
    return body
  }
}
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
      <span class="http-summary-toggle">展开</span>
    </summary>

    <div class="http-body">
      <div class="http-row">
        <span class="http-label">URL</span>
        <code class="http-url">{{ urlText }}</code>
      </div>
      <div v-if="trace.provider || trace.model" class="http-row">
        <span class="http-label">模型</span>
        <code>{{ [trace.provider, trace.model].filter(Boolean).join(' / ') }}</code>
      </div>

      <details class="http-section">
        <summary class="http-section-title">Request Headers</summary>
        <pre class="http-code">{{ formatBody(JSON.stringify(trace.request.headers || {}, null, 2)) }}</pre>
      </details>
      <details class="http-section">
        <summary class="http-section-title">Request Body</summary>
        <pre class="http-code">{{ formatBody(trace.request.body) }}</pre>
      </details>
      <details class="http-section">
        <summary class="http-section-title">Response Headers</summary>
        <pre class="http-code">{{ formatBody(JSON.stringify(trace.response.headers || {}, null, 2)) }}</pre>
      </details>
      <details class="http-section">
        <summary class="http-section-title">Response Body</summary>
        <pre class="http-code">{{ formatBody(trace.response.body) }}</pre>
      </details>
      <div v-if="trace.error" class="http-error">请求失败：{{ trace.error }}</div>
    </div>
  </details>
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
}
.http-summary-tag {
  flex-shrink: 0;
}
.http-summary-duration {
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
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
.http-summary-toggle:empty::before {
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
</style>
