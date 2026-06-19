<template>
  <div v-if="usage && (usage.rounds.length > 0 || usage.toolCallCount > 0 || usage.totalDuration)" class="token-usage-panel">
    <div class="usage-header" @click.stop="toggleRoundsDetails">
      <span class="usage-title">Token 用量</span>
      <div class="usage-badges">
        <span class="badge badge-rounds" @click.stop="toggleRoundsDetails">🔄 {{ usage.rounds.length }} Rounds</span>
        <span v-if="usage.toolCallCount" class="badge badge-tools" @click.stop="toggleToolsDetails">🔧 {{ usage.toolCallCount }} 工具</span>
        <span v-if="usage.totalDuration" class="badge badge-time">⏱ {{ formatDuration(usage.totalDuration) }}</span>
      </div>
    </div>

    <div v-if="usage.rounds.length > 0" class="usage-summary">
      <div class="summary-card">
        <div class="summary-value">{{ formatTokens(totalInput) }}</div>
        <div class="summary-label">输入</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ formatTokens(totalOutput) }}</div>
        <div class="summary-label">输出</div>
        <div v-if="totalReasoning > 0" class="summary-sub reasoning">Reasoning: {{ formatTokens(totalReasoning) }}</div>
      </div>
      <div class="summary-card card-cached">
        <div class="summary-value">{{ formatTokens(totalCached) }}</div>
        <div class="summary-label">缓存</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ formatTokens(totalAll) }}</div>
        <div class="summary-label">Total</div>
        <div v-if="usage.totalDuration" class="summary-sub time">{{ formatDuration(usage.totalDuration) }}</div>
      </div>
    </div>
    <div v-else-if="usage.totalDuration" class="usage-summary-minimal">
      <span class="minimal-info">总耗时 {{ formatDuration(usage.totalDuration) }}</span>
      <span v-if="usage.toolCallCount" class="minimal-info">· {{ usage.toolCallCount }} 次工具调用</span>
    </div>

    <Transition name="usage-details">
    <div v-if="expanded && usage.rounds.length > 1" ref="usageDetailsRef" class="usage-details">
      <div class="details-header">
        <span class="detail-toggle" @click="toggleRoundsDetails">▾ Per-round Details</span>
        <span class="rounds-badge">{{ usage.rounds.length }} Rounds</span>
      </div>
      <table class="details-table">
        <thead>
          <tr>
            <th>#</th>
            <th>输入</th>
            <th>输出</th>
            <th>Total</th>
            <th>Cached</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(round, i) in usage.rounds" :key="i">
            <td class="col-num">{{ i + 1 }}</td>
            <td>{{ formatTokens(round.inputTokens) }}</td>
            <td>{{ formatTokens(round.outputTokens) }}</td>
            <td>{{ formatTokens(round.totalTokens) }}</td>
            <td>{{ formatTokens(round.cacheReadTokens) }}</td>
            <td class="col-duration">{{ round.duration ? formatDuration(round.duration) : '-' }}</td>
          </tr>
          <tr class="row-sum">
            <td class="col-num">Sum</td>
            <td>{{ formatTokens(totalInput) }}</td>
            <td>{{ formatTokens(totalOutput) }}</td>
            <td>{{ formatTokens(totalAll) }}</td>
            <td>{{ formatTokens(totalCached) }}</td>
            <td class="col-duration">{{ usage.totalDuration ? formatDuration(usage.totalDuration) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    </Transition>

    <Transition name="usage-details">
    <div v-if="toolsExpanded && toolCalls && toolCalls.length > 0" ref="toolsDetailsRef" class="tools-details">
      <div class="details-header">
        <span class="detail-toggle" @click="toggleToolsDetails">▾ Tool Calls</span>
        <span class="tools-badge">{{ toolCalls.length }} 工具</span>
      </div>
      <table class="details-table">
        <thead>
          <tr>
            <th>#</th>
            <th class="th-name">名称</th>
            <th>状态</th>
            <th>耗时</th>
            <th>返回长度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(tc, i) in toolCalls" :key="i">
            <td class="col-num">{{ i + 1 }}</td>
            <td class="col-tool-name">{{ tc.name }}</td>
            <td><span class="status-dot" :class="tc.status" />{{ statusLabel(tc.status) }}</td>
            <td class="col-duration">{{ tc.duration ? formatDuration(tc.duration) : '-' }}</td>
            <td>{{ tc.resultLength ? formatSize(tc.resultLength) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import type { MessageUsage, ToolCall } from '@/stores/chat'

const props = defineProps<{
  usage: MessageUsage | undefined
  toolCalls?: ToolCall[]
}>()
const expanded = ref(false)
const toolsExpanded = ref(false)
const usageDetailsRef = ref<HTMLElement>()
const toolsDetailsRef = ref<HTMLElement>()

const totalInput = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.inputTokens, 0) || 0
)
const totalOutput = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.outputTokens, 0) || 0
)
const totalAll = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.totalTokens, 0) || 0
)
const totalCached = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.cacheReadTokens, 0) || 0
)
const totalReasoning = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + (r.reasoningTokens || 0), 0) || 0
)

function formatTokens(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function formatDuration(ms: number): string {
  if (ms < 1000) return ms + 'ms'
  return (ms / 1000).toFixed(1) + 's'
}

function formatSize(len: number): string {
  if (len < 1024) return `${len} chars`
  return `${(len / 1024).toFixed(1)}K`
}

function statusLabel(status: string): string {
  switch (status) {
    case 'done': return '完成'
    case 'running': return '执行中'
    case 'error': return '错误'
    default: return '等待'
  }
}

async function scrollDetailsIntoView(target: typeof usageDetailsRef) {
  await nextTick()
  target.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

function toggleRoundsDetails() {
  expanded.value = !expanded.value
  if (expanded.value) {
    scrollDetailsIntoView(usageDetailsRef)
  }
}

function toggleToolsDetails() {
  toolsExpanded.value = !toolsExpanded.value
  if (toolsExpanded.value) {
    scrollDetailsIntoView(toolsDetailsRef)
  }
}
</script>

<style scoped>
.token-usage-panel {
  margin-top: 12px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
}

.usage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  margin-bottom: 10px;
}

.usage-title {
  font-weight: 700;
  color: var(--el-text-color-primary);
  font-size: 13px;
}

.usage-badges {
  display: flex;
  gap: 8px;
}

.badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.badge-rounds {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border: 1px solid var(--el-color-primary-light-5);
}

.badge-tools {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
  border: 1px solid var(--el-border-color);
}

.badge-time {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  border: 1px solid var(--el-color-success-light-5);
}

.usage-summary {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px;
}

.summary-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px 12px;
  text-align: center;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  font-family: 'JetBrains Mono', monospace;
}

.summary-label {
  font-size: 12px;
  color: var(--el-text-color-primary);
  margin-top: 4px;
  font-weight: 600;
}

.summary-sub {
  font-size: 10px;
  margin-top: 2px;
}

.card-cached .summary-value {
  color: var(--el-color-success);
}

.summary-sub.cached {
  color: var(--el-color-success);
}

.summary-sub.reasoning {
  color: var(--el-text-color-regular);
}

.summary-sub.time {
  color: var(--el-text-color-secondary);
}

.usage-details {
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color);
  padding-top: 10px;
  scroll-margin: 72px 0 96px;
}

.usage-details-enter-active,
.usage-details-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease, max-height 0.22s ease;
  overflow: hidden;
}

.usage-details-enter-from,
.usage-details-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-6px);
}

.usage-details-enter-to,
.usage-details-leave-from {
  opacity: 1;
  max-height: 420px;
  transform: translateY(0);
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-toggle {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  cursor: pointer;
}

.rounds-badge {
  font-size: 10px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 1px 6px;
  border-radius: 8px;
}

.details-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.details-table th {
  color: var(--el-text-color-secondary);
  font-weight: 500;
  text-align: right;
  padding: 4px 8px;
  border-bottom: 1px solid var(--el-border-color);
}

.details-table th:first-child {
  text-align: left;
}

.details-table td {
  color: var(--el-text-color-regular);
  text-align: right;
  padding: 4px 8px;
}

.col-num {
  text-align: left !important;
  color: var(--el-text-color-secondary) !important;
  font-weight: 600;
}

.col-duration {
  color: var(--el-color-warning) !important;
}

.row-sum {
  border-top: 1px solid var(--el-border-color);
}

.row-sum td {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.usage-summary-minimal {
  display: flex;
  gap: 6px;
  align-items: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.minimal-info {
  font-family: 'JetBrains Mono', monospace;
}

.badge-tools {
  cursor: pointer;
  transition: all 0.15s ease;
}

.badge-tools:hover {
  background: var(--el-fill-color-light);
  transform: scale(1.05);
}

.tools-details {
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color);
  padding-top: 10px;
  scroll-margin: 72px 0 96px;
}

.tools-badge {
  font-size: 10px;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color);
  padding: 1px 6px;
  border-radius: 8px;
}

.col-tool-name {
  text-align: left !important;
  color: var(--el-color-primary) !important;
  font-weight: 500;
}

.th-name {
  text-align: left !important;
}

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.status-dot.done {
  background: var(--el-color-success);
}

.status-dot.running {
  background: var(--el-color-warning);
}

.status-dot.error {
  background: var(--el-color-danger);
}
</style>
