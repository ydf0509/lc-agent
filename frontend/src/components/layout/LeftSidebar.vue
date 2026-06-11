<template>
  <aside class="left-sidebar">
    <div class="sidebar-section">
      <el-button type="primary" size="small" style="width:100%" @click="$emit('newChat')">
        + 新对话
      </el-button>
    </div>
    <div class="sidebar-section">
      <h4>会话历史</h4>
      <div class="session-list">
        <div class="session-item active">
          <span>当前对话</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
defineEmits<{ newChat: [] }>()
</script>

<style scoped>
.left-sidebar {
  width: 240px;
  background: var(--lc-bg-secondary);
  border-right: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 16px;
}

.sidebar-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
}

.session-item {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--lc-text-primary);
}

.session-item:hover {
  background: var(--lc-bg-tertiary);
}

.session-item.active {
  background: var(--lc-bg-tertiary);
  border-left: 2px solid var(--lc-accent);
}
</style>
