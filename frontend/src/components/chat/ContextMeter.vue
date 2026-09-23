<template>
  <div v-if="visible" class="context-orb-wrap">
    <el-tooltip placement="top" :show-after="200">
      <template #content>
        <div class="meter-tip">
          <div>当前窗口：{{ fmtTokens(displayWindowTokens) }} / {{ fmtTokens(contextLimit) }} tokens（{{ percentText }}）</div>
          <template v-if="isEstimate">
            <div class="meter-tip-warn">预估 · 待下一轮更新</div>
            <div>压缩后 checkpoint 历史约 {{ fmtTokens(checkpointAfter) }}（不含 system / 工具开销）</div>
            <div>真实用量要等下一轮请求结束才回来，届时自动恢复</div>
          </template>
          <div v-else-if="cacheReadTokens > 0">缓存命中：{{ fmtTokens(cacheReadTokens) }} tokens</div>
          <div v-if="compactionCount > 0">本次会话已手动压缩 {{ compactionCount }} 次</div>
          <div class="meter-tip-hint">点击加速球可手动压缩上下文（等效 /compact）</div>
        </div>
      </template>
      <button
        class="context-orb"
        :class="[bandClass, { 'is-locked': compactDisabled }]"
        :style="{ '--orb-angle': orbAngle }"
        type="button"
        :aria-disabled="compactDisabled"
        :title="compactTitle"
        @click="requestCompact"
      >
        <span class="orb-highlight" aria-hidden="true" />
        <span class="orb-core">
          <span v-if="compacting" class="orb-spinner" aria-hidden="true" />
          <span v-else class="orb-pct">{{ percentText }}</span>
        </span>
      </button>
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import { useSessionsStore } from '@/stores/sessions'
import { useAgentsStore } from '@/stores/agents'
import { useToolsStore } from '@/stores/tools'
import { useChatUiStateStore } from '@/stores/chat-ui-state'

const emit = defineEmits<{ compact: [arg: string] }>()

const chatStore = useChatStore()
const sessionsStore = useSessionsStore()
const agentsStore = useAgentsStore()
const toolsStore = useToolsStore()
const chatUiState = useChatUiStateStore()

const { messages, isStreaming } = storeToRefs(chatStore)

const compacting = ref(false)

/** 运行中（流式输出）不允许压缩：避免在模型正在用这份上下文时重写 checkpoint */
const compactDisabled = computed(() => compacting.value || isStreaming.value)

const compactTitle = computed(() => {
  if (compacting.value) return '压缩中…'
  if (isStreaming.value) return '运行中不可压缩，请等待本轮结束'
  return '压缩上下文（等效 /compact）'
})

function requestCompact() {
  if (compactDisabled.value) return
  emit('compact', '')
}

const sessionId = computed(() => sessionsStore.effectiveThreadId || sessionsStore.currentSessionId || '')

// 当前窗口 ≈ 最后一轮的 input tokens（每轮 input 都是完整 prompt）
const windowScan = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const msg = messages.value[i]
    const rounds = msg?.usage?.rounds
    if (rounds && rounds.length > 0) {
      const last = rounds[rounds.length - 1]
      return { tokens: last.inputTokens || 0, timestamp: msg.timestamp || 0 }
    }
  }
  return { tokens: 0, timestamp: 0 }
})

const windowTokens = computed(() => windowScan.value.tokens)

/** 最后一次带 usage 的消息时间：用来判断压缩后是否已有新一轮真实用量回来 */
const lastUsageTimestamp = computed(() => windowScan.value.timestamp)

const cacheReadTokens = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const rounds = messages.value[i]?.usage?.rounds
    if (rounds && rounds.length > 0) {
      return rounds[rounds.length - 1].cacheReadTokens || 0
    }
  }
  return 0
})

const contextLimit = computed(() => {
  const modelId = toolsStore.currentModel || agentsStore.currentAgent?.default_model || ''
  const model = toolsStore.models.find(m => m.model_id === modelId) || toolsStore.models[0]
  return model?.context_limit || 0
})

const compaction = computed(() => {
  return sessionId.value ? chatUiState.getCompaction(sessionId.value) : undefined
})

const checkpointBefore = computed(() => positiveOrZero(compaction.value?.checkpointTokensBefore))
const checkpointAfter = computed(() => positiveOrZero(compaction.value?.checkpointTokensAfter))

/**
 * 压缩成功后，供应商上报的 input_tokens 要等下一轮请求结束才更新，这期间水位球
 * 按“压缩比例”给一个预估并标记待更新；一旦出现比压缩更晚的 usage 轮次就恢复真实值。
 */
const isEstimate = computed(() => {
  const record = compaction.value
  if (!record) return false
  if (windowTokens.value <= 0) return false
  if (!hasCheckpointEstimate.value) return false
  return lastUsageTimestamp.value <= record.timestamp
})

const hasCheckpointEstimate = computed(() => checkpointAfter.value > 0)

/**
 * 预估 = 按压缩比例折算到供应商口径：checkpoint 估算(B→A) 与供应商 input_tokens
 * 不是同一把尺子（后者含 system/tools），所以按比例缩放而不是直接相减。
 * 缺少 before 时退回“等于压缩后 checkpoint”，并标预估提醒用户尚未校准。
 * 下限取 checkpointAfter：预估不至于低于压缩后历史本身。
 */
const displayWindowTokens = computed(() => {
  if (!isEstimate.value) return windowTokens.value
  const base = windowTokens.value
  const after = checkpointAfter.value
  const before = checkpointBefore.value
  if (before <= 0 || after <= 0 || before <= after) return after
  const predicted = Math.round(base * (after / before))
  return Math.min(base, Math.max(predicted, after))
})

const percent = computed(() => {
  if (contextLimit.value <= 0 || displayWindowTokens.value <= 0) return 0
  return displayWindowTokens.value / contextLimit.value
})

const percentText = computed(() => `${Math.min(100, Math.round(percent.value * 100))}%`)

/** 加速球环形进度角度（conic-gradient 用） */
const orbAngle = computed(() => `${Math.min(100, percent.value * 100) * 3.6}deg`)

// 没开过对话、没有 usage 数据或拿不到模型上限时整个球隐藏（输入行不占位）
const visible = computed(() => Boolean(sessionId.value) && displayWindowTokens.value > 0 && contextLimit.value > 0)

/** 五档水位：绿<60 / 蓝<70 / 黄<80 / 橙<90 / 红≥90；预估态走蓝色待更新语义 */
const bandClass = computed(() => {
  if (isEstimate.value) return 'is-estimate'
  if (percent.value >= 0.9) return 'is-critical'
  if (percent.value >= 0.8) return 'is-hot'
  if (percent.value >= 0.7) return 'is-warm'
  if (percent.value >= 0.6) return 'is-cool'
  return 'is-fresh'
})

const compactionCount = computed(() => (compaction.value ? 1 : 0))

function positiveOrZero(value: number | null | undefined): number {
  return typeof value === 'number' && value > 0 ? value : 0
}

function fmtTokens(n: number): string {
  if (n >= 10000) return `${(n / 1000).toFixed(0)}k`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

defineExpose({
  setCompacting(v: boolean) {
    compacting.value = v
  },
})
</script>

<style scoped>
.context-orb-wrap {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

/* 32px 加速球：conic-gradient 环形进度 + 同色系外发光 */
.context-orb {
  --orb-angle: 0deg;
  position: relative;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  background: conic-gradient(
    from -90deg,
    var(--orb-color) 0 var(--orb-angle),
    var(--el-fill-color-darker) var(--orb-angle) 360deg
  );
  box-shadow: 0 0 8px var(--orb-glow), inset 0 0 4px rgba(0, 0, 0, 0.4);
  transition: transform 0.12s ease, box-shadow 0.3s ease;
}

.context-orb:hover {
  box-shadow: 0 0 12px var(--orb-glow), inset 0 0 4px rgba(0, 0, 0, 0.4);
}

.context-orb:active {
  transform: scale(0.88);
}

/* 五档配色 */
.context-orb.is-fresh {
  --orb-color: #34d399;
  --orb-glow: rgba(52, 211, 153, 0.35);
}
.context-orb.is-cool {
  --orb-color: #38bdf8;
  --orb-glow: rgba(56, 189, 248, 0.35);
}
.context-orb.is-warm {
  --orb-color: #facc15;
  --orb-glow: rgba(250, 204, 21, 0.35);
}
.context-orb.is-hot {
  --orb-color: #fb923c;
  --orb-glow: rgba(251, 146, 60, 0.45);
}
.context-orb.is-critical {
  --orb-color: #ef4444;
  --orb-glow: rgba(239, 68, 68, 0.55);
  animation: orb-breathe 1.6s ease-in-out infinite;
}

/* 预估态：蓝色待更新语义 + 缓慢旋转虚线环 */
.context-orb.is-estimate {
  --orb-color: #60a5fa;
  --orb-glow: rgba(96, 165, 250, 0.4);
}
.context-orb.is-estimate::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 1.5px dashed var(--orb-color);
  animation: orb-spin 6s linear infinite;
  pointer-events: none;
}

/* 深色球心 + 顶部高光点（360 球质感） */
.orb-core {
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 32%, #2e2e33, #17171a 72%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.orb-pct {
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.2px;
  white-space: nowrap;
  color: #fff;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 6px var(--orb-glow);
}

.orb-highlight {
  position: absolute;
  z-index: 1;
  top: 2px;
  left: 6px;
  width: 12px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0));
  transform: rotate(-18deg);
  pointer-events: none;
}

/* 压缩中：中心菊花转 */
.orb-spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-top-color: #fff;
  animation: orb-spin 0.8s linear infinite;
}

/* 流式/禁用：整球置灰 + 不可点（不用 disabled 属性，保证 tooltip 照常弹出） */
.context-orb.is-locked {
  cursor: not-allowed;
  filter: grayscale(0.6);
  opacity: 0.55;
}
.context-orb.is-locked:active {
  transform: none;
}

@keyframes orb-spin {
  to { transform: rotate(360deg); }
}

@keyframes orb-breathe {
  0%, 100% { box-shadow: 0 0 6px var(--orb-glow), inset 0 0 4px rgba(0, 0, 0, 0.4); }
  50% { box-shadow: 0 0 16px var(--orb-glow), 0 0 4px #ef4444, inset 0 0 4px rgba(0, 0, 0, 0.4); }
}

@media (prefers-reduced-motion: reduce) {
  .context-orb {
    transition: none;
  }
  .context-orb.is-critical {
    animation: none;
  }
  .context-orb.is-estimate::after,
  .orb-spinner {
    animation: none;
  }
}

.meter-tip {
  font-size: 12px;
  line-height: 1.8;
}

.meter-tip-hint {
  color: var(--el-text-color-secondary);
}

.meter-tip-warn {
  color: var(--el-color-primary);
}
</style>
