<script setup lang="ts">
import { ref, computed } from 'vue'
import { copyRecentRounds, getRounds, copyToClipboard } from '@/utils/copy-markdown'
import type { ChatMessage } from '@/stores/chat'

const props = defineProps<{
  messages: ChatMessage[]
  modelName?: string
}>()

const visible = ref(false)
const roundCount = ref(3)
const includeThinking = ref(true)
const includeToolCalls = ref(true)
const copied = ref(false)

const totalRounds = computed(() => getRounds(props.messages).length)
const maxRounds = computed(() => Math.max(totalRounds.value, 1))

async function doCopy() {
  const md = copyRecentRounds(props.messages, roundCount.value, {
    includeThinking: includeThinking.value,
    includeToolCalls: includeToolCalls.value,
    modelName: props.modelName,
  })
  const ok = await copyToClipboard(md)
  if (ok) {
    copied.value = true
    setTimeout(() => {
      copied.value = false
      visible.value = false
    }, 1200)
  }
}
</script>

<template>
  <el-popover
    v-model:visible="visible"
    trigger="click"
    :width="260"
    placement="bottom-end"
  >
    <template #reference>
      <button class="copy-rounds-trigger">📋 复制对话</button>
    </template>

    <div class="copy-rounds-panel">
      <div class="panel-title">复制最近对话</div>

      <div class="panel-row">
        <span>轮数:</span>
        <el-input-number
          v-model="roundCount"
          :min="1"
          :max="maxRounds"
          size="small"
          controls-position="right"
          style="width: 100px"
        />
        <span class="hint">/ {{ totalRounds }}</span>
      </div>

      <div class="panel-row">
        <el-checkbox v-model="includeThinking">包含思考过程</el-checkbox>
      </div>
      <div class="panel-row">
        <el-checkbox v-model="includeToolCalls">包含工具调用</el-checkbox>
      </div>

      <el-button
        type="primary"
        size="small"
        style="width: 100%; margin-top: 8px"
        @click="doCopy"
      >
        {{ copied ? '已复制 ✓' : '复制到剪贴板' }}
      </el-button>
    </div>
  </el-popover>
</template>

<style scoped>
.copy-rounds-trigger {
  border: 1px solid color-mix(in srgb, var(--el-color-success) 36%, transparent);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: color-mix(in srgb, var(--el-color-success) 18%, transparent);
  color: var(--el-color-success);
  white-space: nowrap;
}
.copy-rounds-trigger:hover {
  background: color-mix(in srgb, var(--el-color-success) 28%, transparent);
  border-color: color-mix(in srgb, var(--el-color-success) 50%, transparent);
}

.copy-rounds-panel {
  padding: 4px 0;
}
.panel-title {
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 14px;
}
.panel-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.hint {
  color: var(--el-text-color-placeholder, #a8abb2);
  font-size: 12px;
}
</style>
