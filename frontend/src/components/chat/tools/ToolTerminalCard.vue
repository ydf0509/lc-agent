<template>
  <div class="tool-terminal-card" :class="[toolCall.status, { 'is-collapsed': isCollapsed }]">
    <div class="tt-header" @click.stop="toggleCollapse">
      <span class="collapse-icon">{{ isCollapsed ? '▸' : '▾' }}</span>
      <span class="tt-dot" :class="dotClass"></span>
      <span class="tt-title" :title="headerFullTitle">{{ headerTitle }}</span>
      <span v-if="toolCall.status === 'running'" class="live-timer">
        <span class="live-dot"></span>{{ liveElapsed }}
      </span>
      <span v-else-if="finalElapsed" class="live-timer is-finished">{{ finalElapsed }}</span>
      <span v-if="exitBadge" class="tt-exit" :class="{ 'is-error': exitIsError }">{{ exitBadge }}</span>
      <span v-if="toolCall.status === 'done' && resultSizeText" class="meta-item" title="命令输出大小（字符 · 估算 token；图片按像素单独估算）">
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

      <!-- 命令之外的全部入参（max_run_ms / working_directory / wait_ms / skill_name ...），模型传了什么就显示什么 -->
      <ToolField v-if="!isCollapsed && paramsText" label="参数" tone="dark">
        <div class="tt-params">{{ paramsText }}</div>
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
  clipForModal, formatDuration, statusLabel, statusTagType, useToolCard,
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

// 命令行工具的最终结果是 JSON 对象（run_command / skill__execute_script / 后台进程系列）；
// 流式期间 streamingOutput 是裸文本，不参与解析。
const parsedResult = computed<Record<string, any> | null>(() => {
  if (props.toolCall.streamingOutput) return null
  const text = (props.toolCall.result || '').trim()
  if (!text.startsWith('{')) return null
  try {
    const parsed = JSON.parse(text)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
})

const commandText = computed(() => {
  const args = props.toolCall.args || {}
  if (typeof args.command === 'string' && args.command) return args.command
  // kill / read 只有 pid：优先从 JSON 结果里拿 command，其次用 pid 当标题
  const parsed = parsedResult.value
  if (parsed?.command) return String(parsed.command)
  if (args.pid != null) return `PID ${args.pid}`
  return ''
})

// 命令之外的全部入参：max_run_ms / working_directory / wait_ms / skill_name / pid / tail ...
// 不猜默认值，args 里有什么就显示什么；空值不占位
const paramItems = computed<{ key: string; value: string }[]>(() => {
  const args = (props.toolCall.args || {}) as Record<string, unknown>
  const items: { key: string; value: string }[] = []
  for (const [key, value] of Object.entries(args)) {
    if (key === 'command') continue
    if (value === undefined || value === null || value === '') continue
    items.push({ key, value: formatParamValue(value) })
  }
  return items
})

const paramsText = computed(() => paramItems.value.map((item) => `${item.key}=${item.value}`).join(' · '))

function formatParamValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

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
  if (name === 'skill__execute_script') {
    const skill = (props.toolCall.args as any)?.skill_name
    return `运行技能脚本${skill ? ` · ${skill}` : ''}`
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
  if (tc.streamingOutput) return normalizeResult(tc.streamingOutput)
  const parsed = parsedResult.value
  if (parsed) {
    const parts: string[] = []
    const body = parsed.output ?? parsed.stdout ?? parsed.detail ?? ''
    if (body) parts.push(String(body))
    if (parsed.stderr) parts.push(`[stderr]\n${String(parsed.stderr)}`)
    return parts.join('\n')
  }
  return normalizeResult(tc.result || '')
})

const exitInfo = computed(() => {
  const parsed = parsedResult.value
  if (parsed && (parsed.exit_code != null || parsed.timed_out)) {
    return {
      code: parsed.exit_code ?? -1,
      durationMs: Number(parsed.duration_ms) || 0,
      timedOut: !!parsed.timed_out,
    }
  }
  return null
})

const exitIsError = computed(() => {
  if (props.toolCall.status === 'error') return true
  return exitInfo.value != null && (exitInfo.value.timedOut || exitInfo.value.code !== 0)
})

// 计时结束后把最终耗时留在头部，避免倒计时一停数字就消失
const finalElapsed = computed(() => {
  if (props.toolCall.status === 'running') return ''
  return formatDuration(props.toolCall.duration)
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

// 弹框超长内容用 clipForModal 截断并加可见标记
const modalText = computed(() => clipForModal(mainText.value))

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
      // 结果是 JSON：把轮询到的输出并入 stdout 字段，保持可解析
      let merged: string
      try {
        const parsed = JSON.parse(tc.result || '{}')
        parsed.stdout = `${parsed.stdout || ''}${tc.streamingOutput}`
        merged = JSON.stringify(parsed, null, 2)
      } catch {
        merged = (tc.result ? `${tc.result}\n` : '') + tc.streamingOutput
      }
      tc.result = merged
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
  padding: 10px 10px 0;
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

/* 计时结束后的静态耗时：与倒计时同位置同尺寸，去掉蓝色高亮改成中性灰 */
.live-timer.is-finished {
  color: #8b949e;
  background: rgba(139, 148, 158, 0.12);
  border-color: rgba(139, 148, 158, 0.3);
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
  margin: 8px 10px 0;
}

.tt-cmdline {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  min-width: 0;
}

.tt-prompt {
  color: #58a6ff;
  font-weight: 500;
  flex-shrink: 0;
}

/* 命令最多显示 3 行，再长就省略；完整内容看 title 悬浮提示 */
.tt-cmd {
  flex: 1;
  min-width: 0;
  color: #e6edf3;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

/* 命令下方的小字参数行：只读元信息，不抢正文视觉 */
.tt-params {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 11px;
  line-height: 1.6;
  color: #8b949e;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
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
  padding: 6px 10px 10px;
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
