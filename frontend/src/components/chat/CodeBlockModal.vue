<template>
  <teleport to="body">
    <div v-if="visible" class="code-modal-backdrop" @click="$emit('close')">
      <div class="code-modal" role="dialog" aria-modal="true" @click.stop>
        <div class="code-modal-header">
          <div class="code-modal-title-wrap">
            <span class="code-modal-kicker">源码</span>
            <span class="code-modal-title">{{ language }}</span>
          </div>
          <div class="code-modal-actions">
            <button class="code-modal-action-btn" @click="copyCode">{{ copyLabel }}</button>
            <button class="code-modal-close" aria-label="关闭" @click="$emit('close')">✕</button>
          </div>
        </div>
        <div class="code-modal-toolbar">
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            class="code-search-input"
            type="text"
            placeholder="搜索关键字..."
            @keydown.enter.prevent="jumpToNextMatch"
          />
          <div class="code-search-actions">
            <span v-if="searchQuery" class="code-search-count">{{ activeMatchLabel }}</span>
            <button class="code-search-btn" :disabled="!matchCount" @click="jumpToPrevMatch">↑</button>
            <button class="code-search-btn" :disabled="!matchCount" @click="jumpToNextMatch">↓</button>
          </div>
        </div>
        <div class="code-modal-content">
          <pre ref="preRef" class="code-modal-pre hljs"><code ref="codeRef" class="hljs" /></pre>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import hljs from 'highlight.js'

const props = defineProps<{
  visible: boolean
  code: string
  language: string
}>()

defineEmits<{ close: [] }>()

const searchQuery = ref('')
const activeMatchIndex = ref(0)
const matchCount = ref(0)
const codeRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const copyLabel = ref('复制')

const highlightedCode = computed(() => {
  const lang = props.language.toLowerCase()
  if (lang && lang !== 'text' && hljs.getLanguage(lang)) {
    return hljs.highlight(props.code, { language: lang }).value
  }
  return escapeHtml(props.code)
})

const activeMatchLabel = computed(() => {
  if (!matchCount.value) return '0/0'
  return `${activeMatchIndex.value + 1}/${matchCount.value}`
})

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function copyCode() {
  if (!props.code) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(props.code)
    } else {
      const ta = document.createElement('textarea')
      ta.value = props.code
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    copyLabel.value = '已复制'
  } catch {
    copyLabel.value = '复制失败'
  }
  setTimeout(() => { copyLabel.value = '复制' }, 1400)
}

function applyMarks() {
  const codeEl = codeRef.value
  if (!codeEl) return

  codeEl.innerHTML = highlightedCode.value

  const query = searchQuery.value.trim()
  if (!query) {
    matchCount.value = 0
    return
  }

  const regex = new RegExp(escapeRegExp(query), 'gi')
  const walker = document.createTreeWalker(codeEl, NodeFilter.SHOW_TEXT)
  const textNodes: Text[] = []
  let n: Node | null
  while ((n = walker.nextNode())) textNodes.push(n as Text)

  for (const tn of textNodes) {
    const text = tn.textContent || ''
    regex.lastIndex = 0
    const hits: { s: number; e: number }[] = []
    let m: RegExpExecArray | null
    while ((m = regex.exec(text))) hits.push({ s: m.index, e: m.index + m[0].length })
    if (!hits.length) continue

    const frag = document.createDocumentFragment()
    let last = 0
    for (const h of hits) {
      if (h.s > last) frag.appendChild(document.createTextNode(text.slice(last, h.s)))
      const mark = document.createElement('mark')
      mark.className = 'code-search-hit'
      mark.textContent = text.slice(h.s, h.e)
      frag.appendChild(mark)
      last = h.e
    }
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)))
    tn.parentNode!.replaceChild(frag, tn)
  }

  const allMarks = codeEl.querySelectorAll('mark.code-search-hit')
  matchCount.value = allMarks.length
  syncActive()
}

function syncActive() {
  const codeEl = codeRef.value
  if (!codeEl) return
  const marks = codeEl.querySelectorAll('mark.code-search-hit')
  marks.forEach((m, i) => m.classList.toggle('is-active', i === activeMatchIndex.value))
  const active = marks[activeMatchIndex.value]
  active?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

function jumpToNextMatch() {
  if (!matchCount.value) return
  activeMatchIndex.value = (activeMatchIndex.value + 1) % matchCount.value
}

function jumpToPrevMatch() {
  if (!matchCount.value) return
  activeMatchIndex.value = (activeMatchIndex.value - 1 + matchCount.value) % matchCount.value
}

watch(() => props.visible, async (vis) => {
  if (!vis) return
  searchQuery.value = ''
  activeMatchIndex.value = 0
  matchCount.value = 0
  await nextTick()
  applyMarks()
  searchInputRef.value?.focus()
})

watch(searchQuery, async () => {
  activeMatchIndex.value = 0
  await nextTick()
  applyMarks()
})

watch(activeMatchIndex, () => {
  syncActive()
})
</script>

<style scoped>
.code-modal-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--el-bg-color-page) 70%, transparent);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.code-modal {
  width: min(960px, calc(100vw - 80px));
  max-height: min(85vh, 800px);
  min-height: 0;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 16px 48px color-mix(in srgb, var(--el-bg-color-page) 50%, transparent);
}

.code-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  gap: 12px;
  flex: 0 0 auto;
}

.code-modal-title-wrap {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.code-modal-kicker {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.code-modal-title {
  font-family: 'JetBrains Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  text-transform: lowercase;
}

.code-modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.code-modal-action-btn {
  padding: 4px 12px;
  font-size: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  transition: all 0.15s ease;
}

.code-modal-action-btn:hover {
  background: var(--el-fill-color-light);
  border-color: var(--el-color-primary-light-5);
  color: var(--el-color-primary);
}

.code-modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 16px;
  cursor: pointer;
}

.code-modal-close:hover {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.code-modal-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: color-mix(in srgb, var(--el-fill-color-light) 78%, transparent);
}

.code-search-input {
  flex: 1 1 auto;
  min-width: 0;
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  font-size: 13px;
  outline: none;
}

.code-search-input:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--el-color-primary) 14%, transparent);
}

.code-search-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.code-search-count {
  min-width: 42px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: right;
}

.code-search-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.code-search-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.code-modal-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  background: var(--md-code-bg, #101b17);
}

.code-modal-pre {
  margin: 0;
  padding: 16px 20px;
  min-height: 100%;
  color: var(--md-code-text, #d8fff0);
  background: transparent;
  font-family: 'Cascadia Code', 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre;
  word-break: normal;
  overflow-wrap: normal;
  tab-size: 4;
}

.code-modal-pre :deep(.code-search-hit) {
  background: rgba(250, 204, 21, 0.35);
  color: inherit;
  padding: 1px 0;
  border-radius: 2px;
}

.code-modal-pre :deep(.code-search-hit.is-active) {
  background: rgba(245, 158, 11, 0.78);
}

@media (max-width: 520px) {
  .code-modal-backdrop {
    padding: max(8px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left));
    background: color-mix(in srgb, var(--el-bg-color-page) 88%, transparent);
  }

  .code-modal {
    width: 100%;
    max-height: none;
    height: 100%;
    border-radius: 12px;
  }

  .code-modal-header {
    position: sticky;
    top: 0;
    z-index: 1;
    padding: 10px 10px 9px;
    background: var(--el-bg-color);
    gap: 8px;
  }

  .code-modal-kicker {
    display: none;
  }

  .code-modal-title {
    font-size: 12px;
  }

  .code-modal-close {
    width: 34px;
    height: 34px;
    font-size: 18px;
  }

  .code-modal-toolbar {
    padding: 8px 10px;
    gap: 8px;
    flex-wrap: wrap;
  }

  .code-search-input {
    width: 100%;
    height: 36px;
  }

  .code-search-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .code-search-count {
    margin-right: auto;
    text-align: left;
  }

  .code-modal-pre {
    padding: 12px 10px;
    font-size: 12px;
    line-height: 1.6;
  }
}
</style>
