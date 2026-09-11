<template>
  <div class="tool-field" :class="{ 'is-dark': tone === 'dark' }">
    <span class="tool-field-label" :style="offsetStyle">{{ label }}</span>
    <div class="tool-field-body" :class="{ 'is-slot': value === undefined }">
      <span v-if="value !== undefined" class="tool-field-value">{{ value }}</span>
      <slot v-else />
      <button
        v-if="copy"
        class="tool-field-copy"
        :title="copyTitle"
        @click.stop="emit('copy')"
      >{{ copyLabel }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** 左列标签文字，如「工具」「入参」「结果」 */
  label: string
  /** 直接给值走内置渲染；不给则渲染默认插槽 */
  value?: string
  /** 标签下移像素，用于和右侧带内边距的内容盒子对齐 */
  offset?: number
  /** dark 用于终端卡这种深色底 */
  tone?: 'default' | 'dark'
  /** 右侧是否给一个复制按钮（配合 value 使用） */
  copy?: boolean
  copyLabel?: string
  copyTitle?: string
}>(), {
  value: undefined,
  offset: 0,
  tone: 'default',
  copy: false,
  copyLabel: '复制',
  copyTitle: '复制',
})

const emit = defineEmits<{ copy: [] }>()

const offsetStyle = computed(() => (props.offset ? { marginTop: `${props.offset}px` } : undefined))
</script>

<style scoped>
.tool-field {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
}

.tool-field-label {
  flex-shrink: 0;
  width: 32px;
  font-size: 11px;
  line-height: 18px;
  color: var(--el-text-color-secondary);
  user-select: none;
}

.is-dark .tool-field-label { color: #7d8590; }

.tool-field-body {
  flex: 1 1 auto;
  min-width: 0;
}

/* 插槽模式走普通块流，盒子的满宽交给块级默认行为，不靠 flex 撑 */
.tool-field-body:not(.is-slot) {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-field-value {
  flex: 1 1 auto;
  min-width: 0;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
  line-height: 18px;
  color: var(--el-text-color-primary);
  overflow-wrap: anywhere;
}

.is-dark .tool-field-value { color: #e6edf3; }

.tool-field-copy {
  flex: 0 0 auto;
  height: 18px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
}

.tool-field-copy:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-5);
}

.is-dark .tool-field-copy {
  border-color: #30363d;
  color: #7d8590;
}

.is-dark .tool-field-copy:hover {
  color: #e6edf3;
  border-color: #58a6ff;
}
</style>
