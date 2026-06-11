<template>
  <div class="tool-call-card" :class="toolCall.status">
    <div class="tool-header">
      <el-icon v-if="toolCall.status === 'running'" class="spinning">
        <Loading />
      </el-icon>
      <el-icon v-else-if="toolCall.status === 'done'" style="color: var(--lc-success)">
        <Check />
      </el-icon>
      <span class="tool-name">{{ toolCall.name }}</span>
      <el-tag size="small" :type="statusType">{{ statusLabel }}</el-tag>
    </div>
    <div v-if="toolCall.result" class="tool-result">
      <pre>{{ toolCall.result }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading, Check } from '@element-plus/icons-vue'
import type { ToolCall } from '@/stores/chat'

const props = defineProps<{ toolCall: ToolCall }>()

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
  border: 1px solid var(--lc-border);
  border-radius: 6px;
  padding: 8px 12px;
  margin: 4px 0;
  background: var(--lc-bg-secondary);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-name {
  font-family: monospace;
  font-size: 13px;
  color: var(--lc-accent);
}

.tool-result {
  margin-top: 8px;
  padding: 8px;
  background: var(--lc-bg-primary);
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.tool-result pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
