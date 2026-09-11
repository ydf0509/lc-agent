<template>
  <div v-if="!isDismissed" class="tool-generic-card" :class="[toolCall.status, { 'is-collapsed': isCollapsed }]">
    <div class="tg-header" @click.stop="toggleCollapse">
      <span class="collapse-icon">{{ isCollapsed ? '▸' : '▾' }}</span>
      <span class="tg-badge"><el-icon><component :is="badgeIcon" /></el-icon></span>
      <span class="tg-title" :title="friendlyTitle">{{ friendlyTitle }}</span>
      <el-tag size="small" :type="statusType">{{ statusText }}</el-tag>
      <span v-if="toolCall.status === 'running'" class="live-timer">
        <span class="live-dot"></span>{{ liveElapsed }}
      </span>
      <span v-else-if="toolCall.duration != null" class="meta-item">{{ formatDuration(toolCall.duration) }}</span>
      <span v-if="toolCall.status === 'done' && resultSizeText" class="meta-item" title="工具返回内容大小（字符 / 估算 token）">
        📦 {{ resultSizeText }}<template v-if="tokenText"> | {{ tokenText }}</template>
      </span>
      <button
        v-if="toolCall.status === 'error'"
        class="dismiss-btn"
        title="关闭此错误"
        aria-label="关闭此错误"
        @click.stop="isDismissed = true"
      >✕</button>
    </div>

    <!-- 折叠状态下错误仍要直接露出，失败不能被藏起来 -->
    <div v-if="!isCollapsed || errorText" class="tg-body">
      <ToolField
        v-if="!isCollapsed"
        label="工具"
        :value="toolName"
        copy
        :copy-label="copyLabel(COPY_KEY_TOOL)"
        copy-title="复制工具名"
        @copy="copyText(toolName, COPY_KEY_TOOL)"
      />

      <ToolField v-if="!isCollapsed && argRows.length > 0" label="入参">
        <div class="tg-args">
          <div
            v-for="arg in argRows"
            :key="arg.key"
            class="arg-row"
            :class="{ 'is-block': !arg.inline }"
          >
            <span class="arg-key">{{ arg.key }}</span>
            <span v-if="arg.inline" class="arg-value">{{ arg.display }}</span>
            <div v-else class="arg-block">
              <pre class="arg-block-body">{{ arg.display }}</pre>
              <button class="tg-more" @click.stop="openArgModal(arg.key)">看全文</button>
            </div>
          </div>
        </div>
      </ToolField>

      <ToolField v-if="errorText" label="错误" :offset="isCollapsed ? 0 : 8">
        <div class="tg-error">{{ errorText }}</div>
      </ToolField>

      <ToolField v-else-if="!isCollapsed && previewText" label="结果" :offset="8">
        <div class="tg-result-wrap">
          <div class="tg-result">
            <div class="tg-rendered" v-html="renderedPreview" />
          </div>
          <button v-if="isLong" class="tg-more is-right" @click.stop="openResultModal">看全文</button>
        </div>
      </ToolField>
    </div>

    <CodeBlockModal
      :visible="modalTarget !== null"
      :code="modalCode"
      language="text"
      :title="modalTitle"
      :kicker="modalKicker"
      @close="modalTarget = null"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Clock, Connection, Delete, Document, Folder, InfoFilled, List, MagicStick,
  QuestionFilled, Search, Tools,
} from '@element-plus/icons-vue'
import type { ToolCall } from '@/stores/chat'
import CodeBlockModal from '../CodeBlockModal.vue'
import ToolField from './ToolField.vue'
import {
  formatDuration, statusLabel, statusTagType, useToolCard,
} from './useToolCard'

const props = defineProps<{
  toolCall: ToolCall
  collapsed?: boolean
}>()

const { isCollapsed, toggleCollapse, liveElapsed, copyLabel, copyText, resultSizeText, tokenText } = useToolCard({
  toolCall: () => props.toolCall,
  collapsed: props.collapsed,
})

const COPY_KEY_TOOL = 'tool'

const isDismissed = ref(false)
const toolName = computed(() => props.toolCall.name || '(未知工具)')

// 单行且不长 → 紧跟参数名内联；多行或过长 → 单独块 + 「看全文」
const ARG_INLINE_MAX = 160
const ARG_RENDER_MAX = 2000

const statusType = computed(() => statusTagType(props.toolCall.status))
const statusText = computed(() => statusLabel(props.toolCall.status))

// 不同工具配不同小图标，替代之前的“工”字占位
const badgeIcon = computed(() => {
  const name = props.toolCall.name || ''
  if (name === 'load_skill' || name === 'read_skill_resource' || name === 'run_skill_script') return MagicStick
  if (name.endsWith('__read_file') || name.endsWith('__read_multiple_files') || name.endsWith('__get_file_info')) return Document
  if (name.endsWith('__list_directory') || name.endsWith('__create_directory')) return Folder
  if (name.endsWith('__search_files')) return Search
  if (name.endsWith('__move_file') || name.endsWith('__delete_file')) return Delete
  if (name === 'get_system_info') return InfoFilled
  if (name === 'utility__get_current_time' || name === 'get_current_time') return Clock
  if (name.endsWith('ask_user') || name === 'ask_user') return QuestionFilled
  if (name === 'write_todos') return List
  if (name.startsWith('mcp__')) return Connection
  return Tools
})

const READABLE_NAMES: Record<string, string> = {
  file_read__read_file: '读文件',
  file_read__read_multiple_files: '读多个文件',
  file_read__list_directory: '看目录',
  file_read__search_files: '搜文件',
  file_read__get_file_info: '看文件信息',
  file_write__create_directory: '新建目录',
  file_write__move_file: '移动文件',
  file_write__delete_file: '删除文件',
  get_system_info: '看系统信息',
  utility__get_current_time: '看时间',
  load_skill: '加载技能',
  read_skill_resource: '读技能资料',
  run_skill_script: '运行技能脚本',
  ask_user: '问用户',
  write_todos: '任务清单',
}

function clipSummary(s: string, max = 48): string {
  const oneLine = s.replace(/\s+/g, ' ').trim()
  if (!oneLine) return ''
  return oneLine.length > max ? `${oneLine.slice(0, max)}…` : oneLine
}

function summarizeArgs(name: string, args: Record<string, unknown>): string {
  const get = (k: string): string => {
    const v = args[k]
    return typeof v === 'string' ? v : ''
  }
  if (name.endsWith('__read_file') || name === 'read_file') return get('path')
  if (name.endsWith('__read_multiple_files')) {
    const paths = args.paths
    if (Array.isArray(paths)) return `${paths.length} 个文件`
    return ''
  }
  if (name.endsWith('__list_directory')) return get('path')
  if (name.endsWith('__search_files')) {
    const pattern = get('pattern')
    return pattern ? `"${pattern.length > 24 ? `${pattern.slice(0, 24)}…` : pattern}"` : ''
  }
  if (name.endsWith('__get_file_info')) return get('path')
  if (name.endsWith('__create_directory')) return get('path')
  if (name.endsWith('__delete_file')) return get('path')
  if (name.endsWith('__move_file')) {
    const src = get('source')
    const dst = get('destination')
    if (src || dst) return `${src} → ${dst}`
    return ''
  }
  if (name === 'utility__get_current_time' || name === 'get_current_time') {
    return get('timezone') || 'Asia/Shanghai'
  }
  if (name === 'load_skill') return clipSummary(get('skill_name') || get('name'), 40)
  if (name === 'read_skill_resource') {
    const skill = get('skill_name')
    const res = get('resource_name')
    if (skill && res) return clipSummary(`${skill} / ${res}`, 48)
    return clipSummary(skill || res, 40)
  }
  if (name === 'run_skill_script') {
    const skill = get('skill_name')
    const script = get('script_name')
    if (skill && script) return clipSummary(`${skill} / ${script}`, 48)
    return clipSummary(skill || script, 40)
  }
  if (name.endsWith('ask_user') || name === 'ask_user') {
    const questions = (args as Record<string, unknown>).questions
    if (Array.isArray(questions)) {
      const first = questions[0]
      const firstQ = first && typeof first === 'object'
        ? clipSummary(String((first as Record<string, unknown>).question || ''), 24)
        : ''
      return firstQ ? `${questions.length} 个问题 · ${firstQ}` : `${questions.length} 个问题`
    }
    return ''
  }
  if (name === 'write_todos') {
    const todos = (args as Record<string, unknown>).todos
    if (Array.isArray(todos)) return `${todos.length} 项任务`
    return ''
  }
  // 通用兜底：取第一个有意义的参数，保证折叠后也能看出大约做了什么
  const SKIP_KEYS = new Set(['tool_call_id', 'run_id', 'runId', 'id'])
  for (const [key, value] of Object.entries(args)) {
    if (SKIP_KEYS.has(key) || value == null) continue
    if (typeof value === 'string' && value.trim()) return clipSummary(value, 48)
    if (typeof value === 'number' || typeof value === 'boolean') return clipSummary(`${key} ${String(value)}`, 48)
    if (Array.isArray(value) && value.length > 0) {
      const firstStr = value.find((v) => typeof v === 'string' && (v as string).trim())
      if (typeof firstStr === 'string') return clipSummary(`${value.length} 项 · ${firstStr as string}`, 48)
      return clipSummary(`${key} ${value.length} 项`, 48)
    }
  }
  return ''
}

function readableLabel(name: string): string {
  if (READABLE_NAMES[name]) return READABLE_NAMES[name]
  // MCP 工具：mcp__<服务>__<工具>，把服务名保留，否则只剩工具名认不出是谁
  if (name.startsWith('mcp__')) {
    const parts = name.split('__').filter(Boolean)
    if (parts.length >= 3) return `MCP ${parts[1]}/${parts.slice(2).join('__')}`
    return name
  }
  const last = /^.+__(.+)$/.exec(name)?.[1]
  return last || name
}

const friendlyTitle = computed(() => {
  const name = props.toolCall.name || '工具'
  const label = readableLabel(name)
  const summary = props.toolCall.args ? summarizeArgs(name, props.toolCall.args as Record<string, unknown>) : ''
  return summary ? `${label} ${summary}` : label
})

const errorText = computed(() => {
  if (props.toolCall.status !== 'error') return ''
  const text = (props.toolCall.result || '').trim()
  if (!text) return '执行失败'
  return text.length > 300 ? `${text.slice(0, 300)}…` : text
})

function formatArgValue(name: string, key: string, value: unknown): string {
  if (name.endsWith('ask_user') && key === 'questions' && Array.isArray(value)) {
    return (value as any[]).map((q: any, idx: number) => {
      if (!q || typeof q !== 'object') return `${idx + 1}. ${String(q)}`
      const header = `${idx + 1}. ${q.question ?? '?'}`
      if (q.type === 'multiple_choice' && Array.isArray(q.choices)) {
        const choiceLines = q.choices.map((c: string, ci: number) => `  ${String.fromCharCode(65 + ci)}. ${c}`).join('\n')
        return `${header}\n${choiceLines}`
      }
      return header
    }).join('\n\n')
  }
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') {
    // 对象/数组按缩进展开，多行会走块渲染 + 看全文，比压成一行好读
    try {
      return JSON.stringify(value, null, 2) ?? String(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

const argRows = computed(() => {
  const args = props.toolCall.args
  if (!args || Object.keys(args).length === 0) return []
  return Object.entries(args).map(([key, value]) => {
    const full = formatArgValue(props.toolCall.name, key, value)
    const inline = !/[\r\n]/.test(full) && full.length <= ARG_INLINE_MAX
    return {
      key,
      full,
      inline,
      display: full.length > ARG_RENDER_MAX ? `${full.slice(0, ARG_RENDER_MAX)}…` : full,
    }
  })
})

// --- 全文弹层：结果和某个入参共用同一个 CodeBlockModal ---
// 用带类型的 target 而不是字符串哨兵，避免某个入参正好叫 result 时串台
type ModalTarget = { kind: 'result' } | { kind: 'arg'; key: string }

const modalTarget = ref<ModalTarget | null>(null)

function openResultModal(): void {
  modalTarget.value = { kind: 'result' }
}

function openArgModal(key: string): void {
  modalTarget.value = { kind: 'arg', key }
}

const modalCode = computed(() => {
  const target = modalTarget.value
  if (!target) return ''
  if (target.kind === 'result') return (props.toolCall.result || '').slice(0, 200000)
  const arg = argRows.value.find((item) => item.key === target.key)
  return arg ? arg.full : ''
})

const modalTitle = computed(() => {
  const target = modalTarget.value
  if (!target || target.kind === 'result') return toolName.value
  return `${toolName.value} · ${target.key}`
})

const modalKicker = computed(() => (
  modalTarget.value?.kind === 'result' ? '工具结果' : '工具入参'
))

const previewText = computed(() => {
  const text = (props.toolCall.result || '').replace(/\\u3000/g, '　').replace(/\\n/g, '\n')
  if (!text) return ''
  return text.length > 2000 ? `${text.slice(0, 2000)}\n…` : text
})

const isLong = computed(() => (props.toolCall.result?.length || 0) > 2000)

function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

const renderedPreview = computed(() =>
  escapeHtml(previewText.value).replace(/\n/g, '<br>').replace(/ {2}/g, '&nbsp;&nbsp;'),
)
</script>

<style scoped>
.tool-generic-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 6px 0;
  background: var(--el-fill-color-light);
  border-left: 3px solid var(--el-text-color-secondary);
  overflow: hidden;
}

.tool-generic-card.running { border-left-color: var(--el-color-primary); }
.tool-generic-card.done { border-left-color: var(--el-color-success); }
.tool-generic-card.error { border-left-color: var(--el-color-danger); }

.tg-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.is-collapsed { padding: 6px 14px; }

.collapse-icon {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  width: 12px;
  flex-shrink: 0;
}

.tg-badge {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
  border: 1px solid var(--el-border-color-lighter);
}

.tg-badge .el-icon {
  font-size: 14px;
}

.tg-title {
  flex: 1 1 140px;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-timer {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 10px;
  border-radius: 999px;
  font-family: 'JetBrains Mono', monospace;
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
  animation: tg-pulse 1s ease-in-out infinite;
}

@keyframes tg-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.meta-item {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.dismiss-btn {
  margin-left: auto;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  cursor: pointer;
}

.dismiss-btn:hover {
  background: var(--el-color-danger-light-8);
  color: var(--el-color-danger);
}

.tg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.tg-error {
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

.tg-args {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.arg-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.arg-row.is-block {
  flex-direction: column;
  align-items: stretch;
  gap: 3px;
}

.arg-key {
  flex-shrink: 0;
  font-size: 11px;
  line-height: 18px;
  color: var(--el-text-color-secondary);
}

.arg-value {
  min-width: 0;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.arg-block { min-width: 0; }

.arg-block-body {
  margin: 0;
  padding: 7px 9px;
  max-height: 132px;
  overflow: hidden;
  border-radius: 6px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
  font-family: inherit;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.tg-more {
  border: none;
  background: transparent;
  color: var(--el-color-primary);
  font-size: 11px;
  padding: 2px 4px;
  cursor: pointer;
}

.tg-more.is-right { display: block; margin: 6px 0 0 auto; }
.tg-more:hover { text-decoration: underline; }

.tg-result {
  padding: 8px 10px;
  background: var(--el-bg-color-page);
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.tg-rendered {
  color: var(--el-text-color-regular);
  line-height: 1.65;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  word-break: break-word;
  overflow-wrap: anywhere;
}

@media (max-width: 520px) {
  .tool-generic-card { padding: 9px 10px; }
  .is-collapsed { padding: 7px 10px; }
  .tg-title {
    flex-basis: 100%;
    order: 10;
    padding-left: 24px;
  }
}
</style>
