import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { callDesktopApi } from '@/composables/useDesktop'

function readQueryFlag(name: string): boolean {
  try {
    return new URLSearchParams(window.location.search).get(name) === '1'
  } catch {
    return false
  }
}

/**
 * 桌面模式全局状态（单例）。
 *
 * 之所以用 pinia store 而不是直接用 useDesktop()：标题栏双击最大化需要切图标
 * （□/❐），状态要在 AppHeader（双击手柄）和 DesktopWindowControls（图标）之间共享。
 *
 * 注意 isMaximized 只是前端本地记忆：任务栏右键 / Aero 吸附改了窗口状态会不同步，
 * 二期可用 window.events.maximized/restored 事件推给前端再做严谨同步。
 */
export const useDesktopMode = defineStore('desktop', () => {
  const wantDesktop = readQueryFlag('desktop')
  const frameless = readQueryFlag('frameless')
  const bridgeReady = ref(false)
  const isMaximized = ref(false)

  const isDesktop = computed(() => wantDesktop || bridgeReady.value)
  const isFrameless = computed(() => frameless)

  function markBridgeReady() {
    bridgeReady.value = true
  }

  async function toggleMax() {
    await callDesktopApi('toggle_max')
    isMaximized.value = !isMaximized.value
  }

  function closeWindow() {
    // 直接关窗口：destroy 会触发后端关闭；浏览器预览模式下退回 history
    const w = window as unknown as { pywebview?: { api?: { destroy?: () => Promise<void> } } }
    const destroy = w.pywebview?.api?.destroy
    if (typeof destroy === 'function') {
      void destroy()
    } else {
      window.history.back()
    }
  }

  return {
    isDesktop,
    isFrameless,
    bridgeReady,
    isMaximized,
    markBridgeReady,
    toggleMax,
    closeWindow,
    callDesktopApi,
  }
})
