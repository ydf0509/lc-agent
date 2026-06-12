<template>
  <div class="model-selector">
    <el-select
      :model-value="currentModel"
      placeholder="选择模型"
      size="small"
      style="width: 100%"
      @change="$emit('change', $event)"
    >
      <el-option
        v-for="model in models"
        :key="model.id"
        :label="model.id"
        :value="model.id"
      >
        <span>{{ model.id }}</span>
        <span style="float:right; color:var(--lc-text-secondary); font-size:11px">
          {{ model.provider }}
        </span>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  models: { id: string; provider: string; context_limit: number }[]
  currentModel: string
}>()
defineEmits<{ change: [modelId: string] }>()
</script>

<style scoped>
.model-selector {
  margin-bottom: 8px;
}
</style>
