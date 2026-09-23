<template>
  <div v-if="isDesktop && isFrameless" class="desktop-window-controls">
    <button
      class="win-btn"
      title="最小化"
      :disabled="!bridgeReady"
      @click="callDesktopApi('minimize')"
    >
      <el-icon><Minus /></el-icon>
    </button>
    <button
      class="win-btn"
      :title="isMaximized ? '还原' : '最大化'"
      :disabled="!bridgeReady"
      @click="toggleMax"
    >
      <el-icon><CopyDocument v-if="isMaximized" /><Crop v-else /></el-icon>
    </button>
    <button
      class="win-btn win-btn-close"
      title="关闭"
      :disabled="!bridgeReady"
      @click="closeWindow"
    >
      <el-icon><Close /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { Minus, Crop, CopyDocument, Close } from '@element-plus/icons-vue'
import { storeToRefs } from 'pinia'
import { useDesktopMode } from '@/stores/desktop'

// 必须用 storeToRefs：pinia setup store 会解包 ref，直接解构拿到的是布尔 snapshot，
// bridgeReady 置 true 后模板永远收不到更新 → 按钮永久 disabled（灰色不可点）。
const desktop = useDesktopMode()
const { isDesktop, isFrameless, bridgeReady, isMaximized } = storeToRefs(desktop)
const { toggleMax, closeWindow, callDesktopApi } = desktop
</script>

<style scoped>
.desktop-window-controls {
  display: flex;
  align-items: stretch;
  align-self: stretch;
  flex-shrink: 0;
  /* 按钮在拖拽区外面：必须可点，不能继承 drag */
  -webkit-app-region: no-drag;
}

/* 方块按钮：占满 header 高，hover 整块变色（仿原生标题栏按钮） */
.win-btn {
  width: 46px;
  border: none;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0;
  transition: background 0.12s ease, color 0.12s ease;
}

.win-btn:hover:not(:disabled) {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.win-btn:disabled {
  opacity: 0.35;
  cursor: default;
}

.win-btn-close:hover:not(:disabled) {
  background: #e81123;
  color: #fff;
}
</style>
