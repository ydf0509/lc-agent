import { computed, onBeforeUnmount, ref, watch, type ComputedRef, type Ref } from 'vue'
import type { ToolCall } from '@/stores/chat'

export type ToolCardStatus = ToolCall['status']

export interface UseToolCardOptions {
  toolCall: () => ToolCall
  collapsed?: boolean
  /** 编辑/写入文件卡传 true：完成也不自动折叠，始终展开，只有用户手动点才收 */
  keepExpanded?: boolean
}

export function shortPath(filePath: string): string {
  if (!filePath) return ''
  const normalized = filePath.replace(/\\/g, '/')
  const parts = normalized.split('/').filter(Boolean)
  if (parts.length <= 2) return parts.join('/')
  return `${parts[0]}/…/${parts[parts.length - 1]}`
}

export function baseName(filePath: string): string {
  if (!filePath) return ''
  const idx = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'))
  return idx >= 0 ? filePath.slice(idx + 1) : filePath
}

export function formatDuration(ms?: number): string {
  if (ms == null) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function statusLabel(status: ToolCardStatus): string {
  switch (status) {
    case 'running': return '执行中'
    case 'done': return '完成'
    case 'error': return '错误'
    case 'cancelled': return '已取消'
    case 'interrupted': return '已中断'
    default: return '等待'
  }
}

export function statusTagType(status: ToolCardStatus): 'warning' | 'success' | 'danger' | 'info' {
  switch (status) {
    case 'running': return 'warning'
    case 'done': return 'success'
    case 'error': return 'danger'
    default: return 'info'
  }
}

export function formatSize(len: number): string {
  if (len < 1024) return `${len} chars`
  return `${(len / 1024).toFixed(1)}K chars`
}

export function formatTokenCount(count: number): string {
  if (count < 1000) return `~${count}`
  return `~${(count / 1000).toFixed(1)}K`
}

// lazy-load js-tiktoken only when the first tool result arrives
let _encPromise: Promise<{ encode: (text: string) => ArrayLike<number> }> | null = null
function getTiktokenEnc() {
  if (!_encPromise) {
    _encPromise = import('js-tiktoken').then(({ getEncoding }) => getEncoding('cl100k_base'))
  }
  return _encPromise
}

export function useToolCard(options: UseToolCardOptions): {
  isCollapsed: Ref<boolean>
  toggleCollapse: () => void
  liveElapsed: ComputedRef<string>
  copyLabel: (key?: string) => string
  copyText: (text: string, key?: string) => Promise<void>
  resultSizeText: ComputedRef<string>
  tokenText: ComputedRef<string>
} {
  const isCollapsed = ref(options.keepExpanded ? false : (options.collapsed ?? false))
  const userToggled = ref(false)

  function toggleCollapse(): void {
    userToggled.value = true
    isCollapsed.value = !isCollapsed.value
  }

  watch(
    () => options.toolCall().status,
    (status, prev) => {
      // keepExpanded 的卡（编辑/写入文件）不自动折叠
      if (options.keepExpanded) return
      // done 默认收起，其余默认展开；用户手动切换过就不再自动改
      if (userToggled.value) return
      if (status === prev) return
      isCollapsed.value = status === 'done'
    },
  )

  const liveNow = ref(Date.now())
  let liveTimer: ReturnType<typeof setInterval> | null = null

  function startLiveTimer(): void {
    if (liveTimer) return
    liveTimer = setInterval(() => { liveNow.value = Date.now() }, 100)
  }

  function stopLiveTimer(): void {
    if (liveTimer) {
      clearInterval(liveTimer)
      liveTimer = null
    }
  }

  const liveElapsed = computed(() => {
    const start = options.toolCall().startTime
    if (!start) return '--'
    const ms = Math.max(0, liveNow.value - start)
    if (ms < 1000) return `${ms}ms`
    const totalSec = Math.floor(ms / 1000)
    const tenths = Math.floor((ms % 1000) / 100)
    const min = Math.floor(totalSec / 60)
    const sec = totalSec % 60
    if (min === 0) return `${sec}.${tenths}s`
    return `${min}:${String(sec).padStart(2, '0')}.${tenths}`
  })

  watch(() => options.toolCall().status, (status) => {
    if (status === 'running') {
      liveNow.value = Date.now()
      startLiveTimer()
    } else {
      stopLiveTimer()
    }
  }, { immediate: true })

  onBeforeUnmount(() => {
    stopLiveTimer()
  })

  // --- 工具返回内容大小 / 估算 token（旧 ToolCallCard 的头部徽章，卡片拆分后保留） ---
  const tokenCount = ref<number | null>(null)

  watch(
    [() => options.toolCall().result, () => options.toolCall().status],
    async ([result, status]) => {
      if (!result || status !== 'done' || result.length > 500_000) {
        tokenCount.value = null
        return
      }
      try {
        const enc = await getTiktokenEnc()
        tokenCount.value = enc.encode(result).length
      } catch {
        tokenCount.value = null
      }
    },
    { immediate: true },
  )

  const resultSizeText = computed(() => {
    const len = options.toolCall().resultLength ?? options.toolCall().result?.length ?? 0
    return len > 0 ? formatSize(len) : ''
  })

  const tokenText = computed(() => (
    tokenCount.value !== null ? `${formatTokenCount(tokenCount.value)} tokens` : ''
  ))

  // --- 复制按钮：一张卡里可能有多个复制点（工具名 / 命令），按 key 各存各的状态 ---
  const copyStates = ref<Record<string, string>>({})
  const copyTimers: Record<string, ReturnType<typeof setTimeout>> = {}

  function copyLabel(key = 'default'): string {
    return copyStates.value[key] || '复制'
  }

  async function copyText(text: string, key = 'default'): Promise<void> {
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      copyStates.value[key] = '已复制'
    } catch {
      copyStates.value[key] = '复制失败'
    }
    if (copyTimers[key]) clearTimeout(copyTimers[key])
    copyTimers[key] = setTimeout(() => {
      copyStates.value[key] = '复制'
      delete copyTimers[key]
    }, 1500)
  }

  onBeforeUnmount(() => {
    for (const timer of Object.values(copyTimers)) clearTimeout(timer)
  })

  return {
    isCollapsed, toggleCollapse, liveElapsed, copyLabel, copyText,
    resultSizeText, tokenText,
  }
}
