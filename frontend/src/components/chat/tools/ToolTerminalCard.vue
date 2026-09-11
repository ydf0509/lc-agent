<template>
  <div class="tool-terminal-card" :class="[toolCall.status, { 'is-collapsed': isCollapsed }]">
    <div class="tt-header" @click.stop="toggleCollapse">
      <span class="collapse-icon">{{ isCollapsed ? '▸' : '▾' }}</span>
      <span class="tt-dot" :class="dotClass"></span>
      <span class="tt-title" :title="headerFullTitle">{{ headerTitle }}</span>
      <span v-if="exitBadge" class="tt-exit" :class="{ 'is-error': exitIsError }">{{ exitBadge }}</span>
      <span v-else-if="toolCall.status === 'running'" class="live-timer">
        <span class="live-dot"></span>{{ liveElapsed }}
      </span>
      <span v-else-if="toolCall.duration != null" class="meta-item">{{ formatDuration(toolCall.duration) }}</span>
      <span v-if="toolCall.status === 'done' && resultSizeText" class="meta-item" title="命令输出大小（字符 / 估算 token）">
        📦 {{ resultSizeText }}<template v-if="tokenText"> | {{ tokenText }}</template>
      </span>
      <span
        v-if="toolCall.pid && !processKilled && (toolCall.bgProcessRunning || toolCall.status === 'running')"
        class="process-info"
      >
        <span class="pid-badge">PID {{ toolCall.pid }}</span>
        <button class="stop-btn" title="终止进程" :disabled="killing" @click.stop="killProcess">
          {{ killing ? '...' : '■ 停止' }}
        </button>
      </span>
      <el-tag size="small" :type="statusType">{{ statusText }}</el-tag>
    </div>

    <!-- 折叠状态下错误仍要直接露出，失败不能被藏起来 -->
    <div v-if="!isCollapsed || (errorText && !hasOutput)" class="tt-fields">
      <ToolField
        v-if="!isCollapsed"
        label="工具"
        tone="dark"
        :value="toolNameText"
        copy
        :copy-label="copyLabel(COPY_KEY_TOOL)"
        copy-title="复制工具名"
        @copy="copyText(toolNameText, COPY_KEY_TOOL)"
      />

      <ToolField v-if="!isCollapsed" label="命令" tone="dark" :offset="6">
        <div class="tt-cmdline" :title="commandText">
          <span class="tt-prompt">$</span>
          <span class="tt-cmd">{{ commandText || '(无命令)' }}</span>
          <button class="tt-copy" :title="copyLabel(COPY_KEY_CMD)" @click.stop="copyText(commandText, COPY_KEY_CMD)">{{ copyLabel(COPY_KEY_CMD) }}</button>
        </div>
      </ToolField>

      <ToolField v-if="errorText && !hasOutput" label="错误" tone="dark" :offset="isCollapsed ? 0 : 8">
        <div class="tt-error">{{ errorText }}</div>
      </ToolField>

      <ToolField v-if="!isCollapsed && hasOutput" label="输出" tone="dark" :offset="1">
        <div ref="bodyRef" class="tt-body" @scroll="onBodyScroll">
          <div class="tt-output" v-html="renderedOutput" />
          <div v-if="stderrHtml" class="tt-stderr" v-html="stderrHtml" />
          <div v-if="statusLine" class="tt-statusline" :class="{ 'is-error': exitIsError }">{{ statusLine }}</div>
        </div>
      </ToolField>
    </div>

    <div v-if="!isCollapsed && hasOutput" class="tt-footer">
      <button v-if="!followBottom && isStreaming" class="tt-link-btn" @click.stop="scrollToBottom">回到底部</button>
      <button v-if="isLong" class="tt-link-btn" @click.stop="showModal = true">全屏查看</button>
    </div>

    <CodeBlockModal
      :visible="showModal"
      :code="modalText"
      language="bash"
      :title="commandText"
      kicker="命令输出"
      @close="showModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { AnsiUp } from 'ansi_up'
import { fetchApi } from '@/api/http'
import type { ToolCall } from '@/stores/chat'
import CodeBlockModal from '../CodeBlockModal.vue'
import ToolField from './ToolField.vue'
import {
  formatDuration, statusLabel, statusTagType, useToolCard,
} from './useToolCard'

const ansiUp = new AnsiUp()

const props = defineProps<{
  toolCall: ToolCall
  collapsed?: boolean
}>()

const { isCollapsed, toggleCollapse, liveElapsed, copyLabel, copyText, resultSizeText, tokenText } = useToolCard({
  toolCall: () => props.toolCall,
  collapsed: props.collapsed,
})

const COPY_KEY_TOOL = 'tool'
const COPY_KEY_CMD = 'cmd'

const statusType = computed(() => statusTagType(props.toolCall.status))
const statusText = computed(() => statusLabel(props.toolCall.status))
const showModal = ref(false)
const killing = ref(false)
const processKilled = ref(false)
const bodyRef = ref<HTMLElement | null>(null)
const followBottom = ref(true)

const toolName = computed(() => props.toolCall.name || '')
const toolNameText = computed(() => props.toolCall.name || '(未知工具)')

const commandText = computed(() => {
  const args = props.toolCall.args || {}
  if (typeof args.command === 'string' && args.command) return args.command
  // kill / read 只有 pid，把 result 里的 Command 行捞出来当标题
  const m = (props.toolCall.result || '').match(/^Command:\s*(.+)$/m)
  if (m) return m[1].trim()
  if (args.pid != null) return `PID ${args.pid}`
  return ''
})

function shortCommand(cmd: string, maxLen = 42): string {
  const oneLine = cmd.replace(/\s+/g, ' ').trim()
  return oneLine.length > maxLen ? `${oneLine.slice(0, maxLen)}…` : oneLine
}

const headerTitle = computed(() => {
  const name = toolName.value
  const cmd = commandText.value
  if (name === 'command__run_command' || name.endsWith('__run_command') || name === 'run_command') {
    return `运行 ${shortCommand(cmd) || '命令'}`
  }
  if (name === 'command__start_background_process' || name.endsWith('__start_background_process')) {
    return `后台运行 ${shortCommand(cmd) || '命令'}`
  }
  if (name.endsWith('__read_process_output') || name === 'read_process_output') {
    const pid = (props.toolCall.args as any)?.pid ?? props.toolCall.pid ?? ''
    return `看后台输出 PID ${pid}`
  }
  if (name.endsWith('__kill_process') || name === 'kill_process') {
    const pid = (props.toolCall.args as any)?.pid ?? props.toolCall.pid ?? ''
    return `停止进程 PID ${pid}`
  }
  if (name.endsWith('__list_all_processes') || name.endsWith('__list_agent_started_processes')) {
    return '进程列表'
  }
  return shortCommand(cmd) || name
})

const headerFullTitle = computed(() => {
  const raw = toolName.value
  return commandText.value ? `${headerTitle.value}\n${commandText.value}\n(${raw})` : `${headerTitle.value} (${raw})`
})

const dotClass = computed(() => {
  if (props.toolCall.status === 'running') return 'is-running'
  if (props.toolCall.status === 'done') return exitIsError.value ? 'is-error' : 'is-done'
  if (props.toolCall.status === 'error') return 'is-error'
  return 'is-idle'
})

function normalizeResult(value?: string): string {
  if (!value) return ''
  return value.replace(/\\u3000/g, '　').replace(/\\n/g, '\n')
}

const rawOutput = computed(() => {
  const tc = props.toolCall
  const text = normalizeResult(tc.streamingOutput || tc.result || '')
  // 后台进程返回头 "PID:..\nStatus:..\nCommand:..\n---\n正文"：只显示正文
  const sepIdx = text.indexOf('\n---\n')
  if ((toolName.value.endsWith('__start_background_process') || toolName.value.endsWith('__read_process_output'))
    && (text.startsWith('PID:') && sepIdx >= 0)) {
    return text.slice(sepIdx + 5)
  }
  return text
})

const exitInfo = computed(() => {
  const text = rawOutput.value
  const m = text.match(/\[exit_code=(-?\d+),\s*duration=(\d+)ms\]\s*$/)
  if (m) return { code: Number(m[1]), durationMs: Number(m[2]), timedOut: false }
  const t = text.match(/\[Command timed out after (\d+)ms, process killed\]\s*$/)
  if (t) return { code: -1, durationMs: Number(t[1]), timedOut: true }
  return null
})

const exitIsError = computed(() => {
  if (props.toolCall.status === 'error') return true
  return exitInfo.value != null && (exitInfo.value.timedOut || exitInfo.value.code !== 0)
})

const exitBadge = computed(() => {
  if (exitInfo.value == null) return ''
  if (exitInfo.value.timedOut) return '超时'
  return `退出码 ${exitInfo.value.code}`
})

const statusLine = computed(() => {
  if (exitInfo.value == null) return ''
  if (exitInfo.value.timedOut) return `[超时 · ${formatDuration(exitInfo.value.durationMs)} · 进程已杀掉]`
  return `[退出码 ${exitInfo.value.code} · ${formatDuration(exitInfo.value.durationMs)}]`
})

function stripStatusTail(text: string): string {
  return text
    .replace(/\[exit_code=-?\d+,\s*duration=\d+ms\]\s*$/, '')
    .replace(/\[Command timed out after \d+ms, process killed\]\s*$/, '')
    .replace(/\n{3,}$/, '\n\n')
}

const mainText = computed(() => {
  const text = stripStatusTail(rawOutput.value)
  // kill 工具成功只有一行，也当正文显示
  return text.trimEnd()
})

const hasOutput = computed(() => mainText.value.length > 0)

const isStreaming = computed(() =>
  props.toolCall.status === 'running' || Boolean(props.toolCall.bgProcessRunning),
)

const errorText = computed(() => {
  if (props.toolCall.status !== 'error') return ''
  const text = (props.toolCall.result || '').trim()
  if (!text) return '执行失败'
  return text.length > 300 ? `${text.slice(0, 300)}…` : text
})

function renderAnsiBlock(value: string): string {
  return ansiUp.ansi_to_html(value).replace(/\n/g, '<br>').replace(/ {2}/g, '&nbsp;&nbsp;')
}

const renderedOutput = computed(() => {
  const [main] = mainText.value.split('[stderr]')
  return renderAnsiBlock(main || '')
})

const stderrHtml = computed(() => {
  const idx = mainText.value.indexOf('[stderr]')
  if (idx < 0) return ''
  const err = mainText.value.slice(idx + '[stderr]'.length)
  if (!err.trim()) return ''
  return `<span class="stderr-tag">[stderr]</span><br>${renderAnsiBlock(err)}`
})

const modalText = computed(() => mainText.value.slice(0, 200000))

const isLong = computed(() => mainText.value.length > 2000)

function onBodyScroll(): void {
  const el = bodyRef.value
  if (!el) return
  followBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40
}

function scrollToBottom(): void {
  const el = bodyRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
  followBottom.value = true
}

watch([() => props.toolCall.streamingOutput, () => props.toolCall.result], async () => {
  await nextTick()
  if (followBottom.value) scrollToBottom()
})

// --- kill + 后台输出轮询（终端卡接管 command__* 后的保留逻辑，原 ToolCallCard 同款） ---
let bgPollTimer: ReturnType<typeof setInterval> | null = null
let bgPollOffset = 0
let bgPollStartTime = 0
let pollInFlight = false
const BG_POLL_DURATION_MS = 5 * 60 * 1000

async function killProcess(): Promise<void> {
  if (!props.toolCall.pid || killing.value) return
  killing.value = true
  try {
    const res = await fetchApi<{ success: boolean }>(`/tools/process/${props.toolCall.pid}/kill`, { method: 'POST' })
    if (res.success) {
      processKilled.value = true
      stopBgPolling()
    }
  } catch (e) {
    console.error('Failed to kill process:', e)
  } finally {
    killing.value = false
  }
}

function startBgPolling(): void {
  if (bgPollTimer) return
  bgPollOffset = (props.toolCall.streamingOutput || '').length
  bgPollStartTime = Date.now()
  bgPollTimer = setInterval(pollProcessOutput, 1000)
  void pollProcessOutput()
}

function stopBgPolling(): void {
  if (bgPollTimer) {
    clearInterval(bgPollTimer)
    bgPollTimer = null
  }
  pollInFlight = false
  const tc = props.toolCall
  if (tc.bgProcessRunning) {
    tc.bgProcessRunning = false
    if (tc.streamingOutput) {
      tc.result = (tc.result ? `${tc.result}\n` : '') + tc.streamingOutput
      tc.resultLength = tc.result.length
      delete tc.streamingOutput
    }
  }
}

async function pollProcessOutput(): Promise<void> {
  const tc = props.toolCall
  if (!tc.pid) { stopBgPolling(); return }
  if (pollInFlight) return
  if (Date.now() - bgPollStartTime > BG_POLL_DURATION_MS) {
    stopBgPolling()
    return
  }
  pollInFlight = true
  try {
    const data = await fetchApi<{ pid: number; status: string; output: string; offset: number }>(
      `/tools/process/${tc.pid}/output?offset=${bgPollOffset}`,
    )
    if (!tc.bgProcessRunning) return
    if (data.output) {
      tc.streamingOutput = (tc.streamingOutput || '') + data.output
      bgPollOffset = data.offset
    }
    if (!data.status.startsWith('running')) stopBgPolling()
  } catch {
    // 瞬时错误，下一 tick 重试
  } finally {
    pollInFlight = false
  }
}

watch(() => props.toolCall.bgProcessRunning, (val) => {
  if (val) startBgPolling()
  else stopBgPolling()
}, { immediate: true })

onBeforeUnmount(() => {
  stopBgPolling()
})
</script>

<style scoped>
.tool-terminal-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  margin: 6px 0;
  background: #0d1117;
  overflow: hidden;
}

.tool-terminal-card.error { border-color: var(--el-color-danger); }

.tt-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 14px 0;
  cursor: pointer;
  user-select: none;
}

.is-collapsed .tt-header { padding-bottom: 10px; }

.collapse-icon {
  font-size: 10px;
  color: #8b949e;
  width: 12px;
  flex-shrink: 0;
}

.tt-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #484f58;
  flex-shrink: 0;
}

.tt-dot.is-running {
  background: var(--el-color-primary);
  animation: tt-pulse 1s ease-in-out infinite;
}

.tt-dot.is-done { background: var(--el-color-success); }
.tt-dot.is-error { background: var(--el-color-danger); }

@keyframes tt-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.tt-title {
  flex: 1 1 140px;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: #e6edf3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tt-exit {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: #8b949e;
  white-space: nowrap;
}

.tt-exit.is-error { color: #f85149; }

.live-timer {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 10px;
  border-radius: 999px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: #e6edf3;
  background: rgba(88, 166, 255, 0.12);
  border: 1px solid rgba(88, 166, 255, 0.4);
  white-space: nowrap;
}

.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--el-color-primary);
  animation: tt-pulse 1s ease-in-out infinite;
}

.meta-item {
  font-size: 11px;
  color: #8b949e;
  white-space: nowrap;
}

.process-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.pid-badge {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: #8b949e;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 4px;
  padding: 1px 6px;
}

.stop-btn {
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid rgba(248, 81, 73, 0.5);
  border-radius: 4px;
  background: transparent;
  color: #f85149;
  cursor: pointer;
}

.stop-btn:hover { background: rgba(248, 81, 73, 0.12); }

.tt-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 8px 14px 0;
}

.tt-cmdline {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  min-width: 0;
}

.tt-prompt {
  color: #58a6ff;
  font-weight: 500;
  flex-shrink: 0;
}

.tt-cmd {
  flex: 1;
  min-width: 0;
  color: #e6edf3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tt-copy {
  flex-shrink: 0;
  border: 1px solid #30363d;
  background: transparent;
  color: #8b949e;
  font-size: 11px;
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
}

.tt-copy:hover {
  color: #e6edf3;
  border-color: #58a6ff;
}

.tt-error {
  margin: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid rgba(248, 81, 73, 0.4);
  color: #f85149;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.tt-body {
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.65;
  color: #c9d1d9;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.tt-stderr {
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(248, 81, 73, 0.08);
  border-left: 2px solid rgba(248, 81, 73, 0.6);
  border-radius: 0 4px 4px 0;
}

/* v-html 渲染的内容拿不到 scoped 属性，标签要单独用 :deep 上色 */
.tt-stderr :deep(.stderr-tag) {
  color: #f85149;
  font-weight: 500;
}

.tt-statusline {
  margin-top: 6px;
  font-size: 11px;
  color: #8b949e;
}

.tt-statusline.is-error { color: #f85149; }

.tt-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 6px 14px 10px;
}

.tt-link-btn {
  border: none;
  background: transparent;
  color: #58a6ff;
  font-size: 11px;
  cursor: pointer;
  padding: 2px 4px;
}

.tt-link-btn:hover { text-decoration: underline; }

@media (max-width: 520px) {
  .tt-header { gap: 6px; }
  .tt-title {
    flex-basis: 100%;
    order: 10;
    padding-left: 24px;
  }
  .tt-fields { margin: 8px 10px 0; }
}
</style>
