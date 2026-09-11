<template>
  <div class="tool-file-card" :class="[toolCall.status, { 'is-collapsed': isCollapsed }]">
    <div class="tf-header" @click.stop="toggleCollapse">
      <span class="collapse-icon">{{ isCollapsed ? '▸' : '▾' }}</span>
      <span class="tf-badge" :class="`tf-badge--${badgeTone}`">{{ badgeText }}</span>
      <span class="tf-title" :title="fullTitle">{{ title }}</span>
      <span v-if="statText" class="tf-stat">{{ statText }}</span>
      <el-tag size="small" :type="statusType">{{ statusText }}</el-tag>
      <span v-if="toolCall.status === 'running'" class="live-timer">
        <span class="live-dot"></span>{{ liveElapsed }}
      </span>
      <span v-else-if="toolCall.duration != null" class="meta-item">{{ formatDuration(toolCall.duration) }}</span>
      <span v-if="toolCall.status === 'done' && resultSizeText" class="meta-item" title="工具返回内容大小（字符 / 估算 token）">
        📦 {{ resultSizeText }}<template v-if="tokenText"> | {{ tokenText }}</template>
      </span>
    </div>

    <div v-if="!isCollapsed || errorText" class="tf-body">
      <ToolField
        v-if="!isCollapsed"
        label="工具"
        :value="toolName"
        copy
        :copy-label="copyLabel(COPY_KEY_TOOL)"
        copy-title="复制工具名"
        @copy="copyText(toolName, COPY_KEY_TOOL)"
      />

      <ToolField v-if="errorText" label="错误" :offset="isCollapsed ? 0 : 8">
        <div class="tf-error">{{ errorText }}</div>
      </ToolField>

      <template v-else-if="hasDiff">
        <ToolField label="文件">
          <div
            class="tf-filepath clickable"
            :title="`点击查看完整文件：${filePath}`"
            @click.stop="openFileModal(filePath)"
          >{{ filePath }}</div>
        </ToolField>
        <ToolField label="改动">
          <div class="tf-diff">
            <div class="diff-body" :class="{ collapsed: diffCollapsed && totalLines > 30 }">
              <div v-for="(line, i) in diffLines" :key="i" class="diff-line" :class="line.type">
                <span class="diff-linenum">{{ line.num }}</span>
                <span class="diff-prefix">{{ line.prefix }}</span>
                <span class="diff-content">{{ line.text }}</span>
              </div>
            </div>
            <button v-if="totalLines > 30" class="diff-expand-btn" @click.stop="diffCollapsed = !diffCollapsed">
              {{ diffCollapsed ? `展开全部 (${totalLines} 行)` : '折叠' }}
            </button>
            <div class="tf-actions">
              <button class="tf-link-btn" @click.stop="openFileModal(filePath)">看全文</button>
              <button class="tf-link-btn" @click.stop="openInDrawer">在抽屉里看</button>
            </div>
          </div>
        </ToolField>
      </template>

      <template v-else-if="hasPreview">
        <ToolField label="文件">
          <div
            class="tf-filepath clickable"
            :title="`点击查看完整文件：${filePath}`"
            @click.stop="openFileModal(filePath)"
          >{{ filePath }}（{{ modeLabel }}）</div>
        </ToolField>
        <ToolField label="内容">
          <div class="tf-diff">
            <div class="diff-body" :class="{ collapsed: diffCollapsed && totalLines > 20 }">
              <div v-for="(line, i) in displayPreviewLines" :key="i" class="diff-line added">
                <span class="diff-linenum">{{ (toolCall.filePreview!.start_line || 1) + i }}</span>
                <span class="diff-prefix">+</span>
                <span class="diff-content">{{ line }}</span>
              </div>
              <div
                v-if="hasMorePreview && !previewExpanded"
                class="diff-line context clickable-more"
                @click.stop="expandPreview"
              >
                <span class="diff-linenum"></span>
                <span class="diff-prefix"></span>
                <span class="diff-content">{{ previewLoading ? '加载中...' : `还有 ${totalLines - previewCount} 行没显示（点开看全文）` }}</span>
              </div>
            </div>
            <div class="tf-actions">
              <button class="tf-link-btn" @click.stop="openFileModal(filePath)">看全文</button>
              <button class="tf-link-btn" @click.stop="openInDrawer">在抽屉里看</button>
            </div>
          </div>
        </ToolField>
      </template>

      <div v-else-if="toolCall.status === 'running'" class="tf-skeleton">
        <div v-for="i in 3" :key="i" class="skeleton-line" />
      </div>
    </div>

    <CodeBlockModal
      :visible="showFileModal"
      :code="fileModalCode"
      :language="fileModalLang"
      :title="fileModalPath"
      kicker="文件内容"
      @close="showFileModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { fetchApi } from '@/api/http'
import { useFileChangesStore } from '@/stores/file-changes'
import type { ToolCall } from '@/stores/chat'
import CodeBlockModal from '../CodeBlockModal.vue'
import ToolField from './ToolField.vue'
import {
  baseName, formatDuration, shortPath, statusLabel, statusTagType, useToolCard,
} from './useToolCard'

const EXT_LANG_MAP: Record<string, string> = {
  py: 'python', ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
  vue: 'xml', yml: 'yaml', md: 'markdown', sh: 'bash', zsh: 'bash', ps1: 'powershell',
  rs: 'rust', rb: 'ruby', kt: 'kotlin', cs: 'csharp', h: 'c', hpp: 'cpp', cc: 'cpp',
}

function langFromPath(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase() || ''
  return EXT_LANG_MAP[ext] || ext
}

const props = defineProps<{
  toolCall: ToolCall
  collapsed?: boolean
  /** 'edit' = edit_block（红绿 diff），'write' = write_file（只贴新增行） */
  variant: 'edit' | 'write'
}>()

const { isCollapsed, toggleCollapse, liveElapsed, copyLabel, copyText, resultSizeText, tokenText } = useToolCard({
  toolCall: () => props.toolCall,
  collapsed: props.collapsed,
  keepExpanded: true,
})

const COPY_KEY_TOOL = 'tool'
const toolName = computed(() => props.toolCall.name || '(未知工具)')

const diffCollapsed = ref(true)
const previewExpanded = ref(false)
const previewExpandedLines = ref<string[]>([])
const previewLoading = ref(false)
const showFileModal = ref(false)
const fileModalCode = ref('')
const fileModalLang = ref('')
const fileModalPath = ref('')
const fileChangesStore = useFileChangesStore()

const statusType = computed(() => statusTagType(props.toolCall.status))
const statusText = computed(() => statusLabel(props.toolCall.status))

const badgeText = computed(() => (props.variant === 'edit' ? '改' : '新'))
const badgeTone = computed(() => (props.variant === 'edit' ? 'green' : 'blue'))

const filePath = computed(() => {
  const tc = props.toolCall
  if (tc.fileDiff?.file) return tc.fileDiff.file
  if (tc.filePreview?.file) return tc.filePreview.file
  const args = tc.args || {}
  const raw = (args.file_path ?? args.path ?? '') as unknown
  return typeof raw === 'string' ? raw : ''
})

const modeLabel = computed(() => {
  const mode = props.toolCall.filePreview?.mode
  if (mode === 'append') return '追加'
  return '写入'
})

const title = computed(() => {
  const name = baseName(filePath.value) || (props.variant === 'edit' ? '编辑文件' : '写入文件')
  if (props.variant === 'edit') return `改 ${name}`
  if (props.toolCall.filePreview?.mode === 'append') return `追加到 ${name}`
  return `写入 ${name}`
})

const fullTitle = computed(() => (
  filePath.value ? `${title.value}（${shortPath(filePath.value)}）` : title.value
))

const statText = computed(() => {
  const tc = props.toolCall
  if (tc.fileDiff) {
    const added = tc.fileDiff.added.length
    const removed = tc.fileDiff.removed.length
    if (added || removed) return `+${added} −${removed}`
    return ''
  }
  if (tc.filePreview) {
    const total = tc.filePreview.total_lines
    if (total > 0) return `${total} 行`
    return ''
  }
  return ''
})

const errorText = computed(() => {
  const tc = props.toolCall
  if (tc.status !== 'error') return ''
  const text = (tc.result || '').trim()
  if (!text) return '执行失败'
  const firstTwo = text.split('\n').slice(0, 2).join('\n')
  return firstTwo.length > 300 ? `${firstTwo.slice(0, 300)}…` : firstTwo
})

interface DiffLine {
  type: 'context' | 'removed' | 'added'
  num: string
  prefix: string
  text: string
}

const hasDiff = computed(() => Boolean(props.toolCall.fileDiff))
const hasPreview = computed(() => Boolean(props.toolCall.filePreview) && !hasDiff.value)

const diffLines = computed<DiffLine[]>(() => {
  const diff = props.toolCall.fileDiff
  if (!diff) return []
  const lines: DiffLine[] = []
  let lineNum = diff.start_line
  for (const line of diff.context_before) {
    lines.push({ type: 'context', num: String(lineNum++), prefix: ' ', text: line })
  }
  for (const line of diff.removed) {
    lines.push({ type: 'removed', num: String(lineNum++), prefix: '−', text: line })
  }
  lineNum = diff.start_line + diff.context_before.length
  for (const line of diff.added) {
    lines.push({ type: 'added', num: String(lineNum++), prefix: '+', text: line })
  }
  for (const line of diff.context_after) {
    lines.push({ type: 'context', num: String(lineNum++), prefix: ' ', text: line })
  }
  return lines
})

const previewCount = computed(() => props.toolCall.filePreview?.preview_lines.length || 0)

const hasMorePreview = computed(() => {
  const fp = props.toolCall.filePreview
  return Boolean(fp && fp.total_lines > previewCount.value)
})

const displayPreviewLines = computed(() => {
  const fp = props.toolCall.filePreview
  if (!fp) return []
  return previewExpanded.value ? previewExpandedLines.value : fp.preview_lines
})

const totalLines = computed(() => {
  if (hasDiff.value) return diffLines.value.length
  if (hasPreview.value) return props.toolCall.filePreview?.total_lines || 0
  return 0
})

async function expandPreview(): Promise<void> {
  const fp = props.toolCall.filePreview
  if (!fp || previewLoading.value) return
  try {
    const data = await fetchApi<{ lines: string[]; truncated?: boolean; error?: string }>(
      `/tools/file/read?path=${encodeURIComponent(fp.file)}&max_lines=500`,
    )
    if (data.error) {
      openFileModal(fp.file)
      return
    }
    previewExpandedLines.value = data.lines
    previewExpanded.value = true
  } catch {
    openFileModal(fp.file)
  } finally {
    previewLoading.value = false
  }
}

async function openFileModal(path: string): Promise<void> {
  if (!path) return
  try {
    const data = await fetchApi<{ lines: string[]; truncated?: boolean; error?: string }>(
      `/tools/file/read?path=${encodeURIComponent(path)}&max_lines=2000`,
    )
    fileModalPath.value = path
    fileModalLang.value = langFromPath(path)
    if (data.error) {
      fileModalCode.value = `Error: ${data.error}`
      fileModalLang.value = 'text'
    } else {
      let code = data.lines.join('\n')
      if (data.truncated) code += '\n\n// … 文件过大，仅显示前 2000 行'
      fileModalCode.value = code
    }
    showFileModal.value = true
  } catch (e) {
    fileModalPath.value = path
    fileModalCode.value = `Failed to load file: ${e}`
    fileModalLang.value = 'text'
    showFileModal.value = true
  }
}

function openInDrawer(): void {
  if (!filePath.value) return
  fileChangesStore.pendingOpenFile = filePath.value
  fileChangesStore.openDrawer()
}
</script>

<style scoped>
.tool-file-card {
  position: relative;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 6px 0;
  background: var(--el-fill-color-light);
  border-left: 3px solid var(--el-text-color-secondary);
  overflow: hidden;
}

.tool-file-card.running { border-left-color: var(--el-color-primary); }
.tool-file-card.done { border-left-color: var(--el-color-success); }
.tool-file-card.error { border-left-color: var(--el-color-danger); }

.tf-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.collapse-icon {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  width: 12px;
  flex-shrink: 0;
}

.is-collapsed { padding: 6px 14px; }

.tf-badge {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
}

.tf-badge--green {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success-dark-2);
  border: 1px solid var(--el-color-success-light-7);
}

.tf-badge--blue {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary-dark-2);
  border: 1px solid var(--el-color-primary-light-7);
}

.tf-title {
  flex: 1 1 140px;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tf-stat {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.live-timer {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 10px;
  border-radius: 999px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--el-color-warning-dark-2);
  background: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning-light-5);
  white-space: nowrap;
}

.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--el-color-warning);
  animation: tf-pulse 1s ease-in-out infinite;
}

@keyframes tf-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.meta-item {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.tf-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.tf-error {
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--el-color-danger-light-9);
  border: 1px solid var(--el-color-danger-light-7);
  color: var(--el-color-danger-dark-2);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.tf-diff {
  background: #0d1117;
  border-radius: 6px;
  border: 1px solid var(--el-border-color);
  overflow: hidden;
}

.tf-filepath {
  font-size: 12px;
  line-height: 18px;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  color: var(--el-text-color-primary);
  overflow-wrap: anywhere;
}

.tf-filepath.clickable { cursor: pointer; }
.tf-filepath.clickable:hover {
  color: var(--el-color-primary);
  text-decoration: underline;
}

.diff-body {
  overflow-y: auto;
  max-height: 380px;
}

.diff-body.collapsed { max-height: 200px; }

.diff-line {
  display: flex;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.7;
  padding: 0 8px;
}

.diff-line.context { color: #8b949e; }
.diff-line.removed {
  background: rgba(248, 81, 73, 0.1);
  color: #f85149;
}
.diff-line.added {
  background: rgba(63, 185, 80, 0.1);
  color: #3fb950;
}

.diff-linenum {
  width: 36px;
  flex-shrink: 0;
  text-align: right;
  padding-right: 8px;
  color: #484f58;
  user-select: none;
}

.diff-prefix {
  width: 14px;
  flex-shrink: 0;
  text-align: center;
  font-weight: 500;
}

.diff-content {
  flex: 1;
  min-width: 0;
  white-space: pre;
  overflow: hidden;
  text-overflow: ellipsis;
}

.diff-expand-btn {
  width: 100%;
  padding: 4px 0;
  border: none;
  border-top: 1px solid #30363d;
  background: #161b22;
  color: var(--el-color-primary);
  font-size: 11px;
  cursor: pointer;
}

.diff-expand-btn:hover { background: #1c2128; }

.clickable-more { cursor: pointer; }
.clickable-more:hover { background: rgba(88, 166, 255, 0.08); }
.clickable-more .diff-content { color: #58a6ff; }

.tf-actions {
  display: flex;
  gap: 8px;
  padding: 6px 12px;
  background: #161b22;
  border-top: 1px solid #30363d;
}

.tf-link-btn {
  border: none;
  background: transparent;
  color: var(--el-color-primary);
  font-size: 11px;
  cursor: pointer;
  padding: 2px 4px;
}

.tf-link-btn:hover { text-decoration: underline; }

.tf-skeleton { margin-top: 0; }
.skeleton-line {
  height: 12px;
  border-radius: 4px;
  margin: 6px 0;
  background: var(--el-fill-color);
  animation: tf-pulse 1.2s ease-in-out infinite;
}

@media (max-width: 520px) {
  .tool-file-card { padding: 9px 10px; }
  .is-collapsed { padding: 7px 10px; }
  .tf-title {
    flex-basis: 100%;
    order: 10;
    padding-left: 24px;
  }
}
</style>
