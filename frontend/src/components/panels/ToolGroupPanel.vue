<template>
  <div class="tool-group-panel">
    <div v-for="group in groups" :key="group.name" class="group-item">
      <div class="group-header">
        <span class="group-name">{{ group.name }}</span>
        <el-switch
          v-model="group.enabled"
          size="small"
          @change="$emit('toggle', group.name)"
        />
      </div>
      <div class="group-tools">
        <el-tag
          v-for="tool in group.tools"
          :key="tool.name"
          size="small"
          :type="group.enabled ? '' : 'info'"
          :effect="group.enabled ? 'dark' : 'plain'"
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
defineEmits<{ toggle: [groupName: string] }>()
</script>

<style scoped>
.group-item {
  margin-bottom: 12px;
  padding: 8px;
  background: var(--lc-bg-tertiary);
  border-radius: 6px;
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
}
</style>
