<script setup lang="ts">
import { computed } from 'vue'
import type { HttpTrace, LlmRoundUsage } from '@/stores/chat'
import HttpTraceBlock from './HttpTraceBlock.vue'

const props = defineProps<{
  traces: HttpTrace[]
  rounds?: LlmRoundUsage[]
}>()

const totalDuration = computed(() => {
  const ms = props.traces.reduce((sum, t) => sum + (t.durationMs || 0), 0)
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms}ms`
})

const errorCount = computed(() =>
  props.traces.filter(t => Boolean(t.error) || t.response.ok === false).length,
)
</script>

<template>
  <details class="http-traces-group">
    <summary class="http-group-summary">
      <span class="http-group-icon">🌐</span>
      <span class="http-group-label">HTTP 交互</span>
      <span class="http-group-stats">
        {{ traces.length }} 步 · {{ totalDuration }}
      </span>
      <span v-if="errorCount > 0" class="http-group-errors">
        {{ errorCount }} 失败
      </span>
      <span class="http-group-toggle" />
    </summary>
    <div class="http-group-body">
      <HttpTraceBlock
        v-for="(trace, idx) in traces"
        :key="trace.id"
        :trace="trace"
        :usage-round="rounds?.[idx]"
      />
    </div>
  </details>
</template>

<style scoped>
.http-traces-group {
  margin: 8px 0;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-color-primary);
  border-radius: 8px;
  background: var(--el-fill-color-light);
  overflow: hidden;
}

.http-group-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.http-group-summary::-webkit-details-marker {
  display: none;
}

.http-group-icon {
  font-size: 14px;
}
.http-group-label {
  font-weight: 600;
}
.http-group-stats {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.http-group-errors {
  font-size: 12px;
  color: var(--el-color-danger);
  font-weight: 500;
}
.http-group-toggle {
  margin-left: auto;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
.http-traces-group[open] .http-group-toggle::before {
  content: '收起';
}
.http-traces-group:not([open]) .http-group-toggle::before {
  content: '展开';
}

.http-group-body {
  padding: 4px 8px 8px;
}
</style>
