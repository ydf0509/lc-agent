<template>
  <div v-if="usage && (usage.rounds.length > 0 || usage.toolCallCount > 0 || usage.totalDuration)" class="token-usage-panel">
    <div class="usage-header" @click="expanded = !expanded">
      <span class="usage-title">Token 用量</span>
      <div class="usage-badges">
        <span class="badge badge-rounds">🔄 {{ usage.rounds.length }} Rounds</span>
        <span v-if="usage.toolCallCount" class="badge badge-tools">🔧 {{ usage.toolCallCount }} 工具</span>
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

    <div v-if="expanded && usage.rounds.length > 1" class="usage-details">
      <div class="details-header">
        <span class="detail-toggle" @click="expanded = !expanded">▾ Per-round Details</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { MessageUsage } from '@/stores/chat'

const props = defineProps<{ usage: MessageUsage | undefined }>()
const expanded = ref(false)

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
</script>

<style scoped>
.token-usage-panel {
  margin-top: 12px;
  background: rgba(22, 27, 34, 0.8);
  border: 1px solid #30363d;
  border-radius: 10px;
  padding: 12px 16px;
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
  color: #e6edf3;
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
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
  border: 1px solid rgba(88, 166, 255, 0.3);
}

.badge-tools {
  background: rgba(163, 113, 247, 0.15);
  color: #a371f7;
  border: 1px solid rgba(163, 113, 247, 0.3);
}

.badge-time {
  background: rgba(56, 211, 159, 0.15);
  color: #38d39f;
  border: 1px solid rgba(56, 211, 159, 0.3);
}

.usage-summary {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px;
}

.summary-card {
  background: rgba(13, 17, 23, 0.6);
  border: 1px solid #21262d;
  border-radius: 8px;
  padding: 10px 12px;
  text-align: center;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #e6edf3;
  font-family: 'JetBrains Mono', monospace;
}

.summary-label {
  font-size: 11px;
  color: #8b949e;
  margin-top: 2px;
}

.summary-sub {
  font-size: 10px;
  margin-top: 2px;
}

.card-cached .summary-value {
  color: #3fb950;
}

.summary-sub.cached {
  color: #3fb950;
}

.summary-sub.reasoning {
  color: #a371f7;
}

.summary-sub.time {
  color: #8b949e;
}

.usage-details {
  margin-top: 12px;
  border-top: 1px solid #21262d;
  padding-top: 10px;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-toggle {
  color: #8b949e;
  font-size: 11px;
  cursor: pointer;
}

.rounds-badge {
  font-size: 10px;
  color: #58a6ff;
  background: rgba(88, 166, 255, 0.1);
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
  color: #8b949e;
  font-weight: 500;
  text-align: right;
  padding: 4px 8px;
  border-bottom: 1px solid #21262d;
}

.details-table th:first-child {
  text-align: left;
}

.details-table td {
  color: #c9d1d9;
  text-align: right;
  padding: 4px 8px;
}

.col-num {
  text-align: left !important;
  color: #8b949e !important;
  font-weight: 600;
}

.col-duration {
  color: #f0883e !important;
}

.row-sum {
  border-top: 1px solid #30363d;
}

.row-sum td {
  font-weight: 700;
  color: #e6edf3;
}

.usage-summary-minimal {
  display: flex;
  gap: 6px;
  align-items: center;
  color: #8b949e;
  font-size: 12px;
}

.minimal-info {
  font-family: 'JetBrains Mono', monospace;
}
</style>
