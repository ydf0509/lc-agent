<template>
  <div class="tool-group-panel">
    <div v-for="group in groups" :key="group.id" class="group-item" :class="{ 'not-allowed': !(group as any).allowed && (group as any).allowed !== undefined }">
      <div class="group-header">
        <span class="group-name">{{ group.description || group.id }}</span>
        <el-switch
          :model-value="group.enabled"
          :disabled="(group as any).allowed === false"
          size="small"
          @change="$emit('toggle', group.id)"
        />
      </div>
      <div class="group-tools">
        <el-tag
          v-for="tool in group.tools"
          :key="tool.name"
          size="small"
          :class="group.enabled ? 'tool-tag-enabled' : 'tool-tag-disabled'"
        >
          {{ tool.name.split('__').pop() }}
        </el-tag>
      </div>
    </div>
    <p v-if="!groups.length" class="empty">暂无工具</p>
  </div>
</template>

<script setup lang="ts">
import type { ToolGroup } from '@/stores/tools'

defineProps<{ groups: ToolGroup[] }>()
defineEmits<{ toggle: [groupId: string] }>()
</script>

<style scoped>
.group-item {
  margin-bottom: 8px;
  padding: 10px;
  background: var(--lc-glass-bg-hover);
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-sm);
  transition: border-color var(--lc-transition-fast), background var(--lc-transition-fast);
}

.group-item:hover {
  border-color: var(--lc-glass-border-hover);
  background: var(--lc-glass-bg-active);
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.group-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--lc-text-primary);
}

.group-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.empty {
  color: var(--lc-text-secondary);
  font-size: 12px;
  opacity: 0.6;
}

.not-allowed {
  opacity: 0.4;
  border-style: dashed;
  border-color: rgba(255, 255, 255, 0.06) !important;
}
</style>
