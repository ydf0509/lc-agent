import { ref, onMounted, onBeforeUnmount } from 'vue'

const STORAGE_KEY_LEFT = 'lc-agent:layout:leftWidth'
const STORAGE_KEY_RIGHT = 'lc-agent:layout:rightWidth'

const DEFAULT_LEFT_WIDTH = 230
/* 右侧承担文件代码/diff 展示，默认给宽些 */
const DEFAULT_RIGHT_WIDTH = 810
const MIN_WIDTH = 200
const MAX_LEFT_WIDTH = 600
/* 右侧面板内容多为长路径/diff/表格，上限放宽，只受"给聊天区留多少"约束 */
const MAX_RIGHT_WIDTH = 1400
/* 无论怎么拖，中间聊天区至少留这么宽，否则拖到极限会把对话挤没 */
const MIN_CHAT_WIDTH = 420

/** 右侧面板实际可用上限：受固定上限和"必须给聊天区留白"两者约束 */
function resolveMaxRightWidth(leftWidth: number): number {
  if (typeof window === 'undefined') return MAX_RIGHT_WIDTH
  const available = window.innerWidth - leftWidth - MIN_CHAT_WIDTH
  return Math.max(MIN_WIDTH, Math.min(MAX_RIGHT_WIDTH, available))
}

function loadWidth(key: string, fallback: number): number {
  try {
    const v = localStorage.getItem(key)
    if (v !== null) {
      const n = parseInt(v, 10)
      if (!isNaN(n) && n >= MIN_WIDTH) return n
    }
  } catch { /* ignore */ }
  return fallback
}

function saveWidth(key: string, value: number) {
  try {
    localStorage.setItem(key, String(Math.round(value)))
  } catch { /* ignore */ }
}

export function usePanelResize() {
  const leftWidth = ref(loadWidth(STORAGE_KEY_LEFT, DEFAULT_LEFT_WIDTH))
  const rightWidth = ref(loadWidth(STORAGE_KEY_RIGHT, DEFAULT_RIGHT_WIDTH))

  let dragging: 'left' | 'right' | null = null
  let startX = 0
  let startWidth = 0

  function onMouseMove(e: MouseEvent) {
    if (!dragging) return
    const delta = e.clientX - startX
    if (dragging === 'left') {
      const next = Math.min(MAX_LEFT_WIDTH, Math.max(MIN_WIDTH, startWidth + delta))
      leftWidth.value = next
      saveWidth(STORAGE_KEY_LEFT, next)
    } else {
      const maxRight = resolveMaxRightWidth(leftWidth.value)
      const next = Math.min(maxRight, Math.max(MIN_WIDTH, startWidth - delta))
      rightWidth.value = next
      saveWidth(STORAGE_KEY_RIGHT, next)
    }
  }

  function onMouseUp() {
    if (!dragging) return
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    dragging = null
  }

  function startResize(side: 'left' | 'right', e: MouseEvent) {
    e.preventDefault()
    dragging = side
    startX = e.clientX
    startWidth = side === 'left' ? leftWidth.value : rightWidth.value
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  onMounted(() => {
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  })

  return {
    leftWidth,
    rightWidth,
    startResize,
  }
}