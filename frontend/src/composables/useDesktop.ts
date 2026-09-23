import { computed, onMounted, ref } from 'vue'

function readQueryFlag(name: string): boolean {
  try {
    return new URLSearchParams(window.location.search).get(name) === '1'
  } catch {
    return false
  }
}

function hasBridge(): boolean {
  const w = window as unknown as Record<string, unknown>
  const pv = w.pywebview as { api?: Record<string, unknown> } | undefined
  return !!pv?.api
}

/**
 * 桌面端（pywebview）检测：URL 参数 + bridge 双确认。
 *
 * - `?desktop=1`（Python 侧 desktop.py 拼接）：同步、无首屏闪烁
 * - `window.pywebview.api` 存在：确认真的在桌面壳里，而不是浏览器手动敲参数冒充
 *
 * 浏览器开发时手动加 `?desktop=1` 可预览桌面版标题栏，按钮调用会被 guard 拦截为 no-op。
 */
export function useDesktop() {
  const bridgeReady = ref(hasBridge())
  const wantDesktop = readQueryFlag('desktop')

  const isFrameless = computed(() => readQueryFlag('frameless'))
  // 疑似桌面：有参数就算，先渲染 desktop 布局，bridge 确认后再启用按钮
  const isDesktop = computed(() => wantDesktop || bridgeReady.value)

  onMounted(() => {
    if (bridgeReady.value) return
    // bridge 在 pywebviewready 之后才注入；等 1.5s 没来就认定是浏览器冒充
    const onReady = () => {
      bridgeReady.value = true
    }
    window.addEventListener('pywebviewready', onReady, { once: true })
    window.setTimeout(() => {
      window.removeEventListener('pywebviewready', onReady)
      if (!hasBridge()) bridgeReady.value = false
    }, 1500)
  })

  return { isDesktop, isFrameless, bridgeReady }
}

interface DesktopApi {
  minimize: () => Promise<void>
  maximize: () => Promise<void>
  restore: () => Promise<void>
  toggle_max: () => Promise<void>
}

/**
 * 调用 pywebview js_api。注意 bridge 的坑：JS 侧永远把 `arguments` 整体发过去，
 * Python 侧 `func(*params)` 展开——无参方法必须零参调用，带个 undefined 都算多一个参数。
 */
export async function callDesktopApi<K extends keyof DesktopApi>(fn: K): Promise<void> {
  const w = window as unknown as { pywebview?: { api?: DesktopApi } }
  const api = w.pywebview?.api
  if (!api || typeof api[fn] !== 'function') {
    console.warn(`[desktop] bridge not ready, ignore ${fn}`)
    return
  }
  await api[fn]()
}
