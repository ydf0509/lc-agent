import { defineStore } from 'pinia'
import { ref, computed, shallowReactive } from 'vue'
import { ChatSseClient, type SseMessage } from '@/api/sse-client'
import { useSessionsStore } from '@/stores/sessions'
import { useFileChangesStore } from '@/stores/file-changes'
import { api } from '@/api/http'
import { createClientId } from '@/utils/client-id'
import { createSessionState } from './chat-session-state'
import type { SessionState } from './chat-session-state'
import type { ContentBlock } from '@/utils/fileUpload'

const INITIAL_MESSAGE_LIMIT = 6

export interface LlmRoundUsage {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  cacheReadTokens: number
  reasoningTokens: number
  duration?: number
}

export interface MessageUsage {
  rounds: LlmRoundUsage[]
  toolCallCount: number
  totalDuration?: number
}

export interface HttpTraceMessagePart {
  method?: string
  url?: string
  headers: Record<string, string>
  body: string
  bodyFormat?: 'json' | 'text' | 'empty' | 'unknown'
}

export interface HttpTraceResponsePart {
  status?: number
  headers: Record<string, string>
  body: string
  bodyFormat?: 'json' | 'text' | 'empty' | 'unknown'
  ok?: boolean
}

export interface HttpTrace {
  id: string
  sequence: number
  kind: 'llm_http'
  provider?: string
  model?: string
  startedAt: number
  durationMs?: number
  request: HttpTraceMessagePart
  response: HttpTraceResponsePart
  error?: string | null
}

export interface ErrorInfo {
  title: string
  detail: string
  suggestions?: string[]
  techDetail?: string
  errorCode?: string
}

export interface ContentSegment {
  type: 'text' | 'tool'
  text?: string
  toolCall?: ToolCall
}

export interface SubAgentEntry {
  tool_call_id: string
  name: string
  sub_session_id: string
  query: string
  status: 'running' | 'done' | 'error' | 'cancelled' | 'interrupted'
  tokenPreview: string
  toolCallCount: number
  tokenCount: number
  tokens: string
  thinking: string
  thinkCount: number
  innerToolCalls: Array<{ name: string; status: string; args?: unknown; result?: string }>
  duration?: number
  httpTraces?: HttpTrace[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string | ContentBlock[]
  timestamp: number
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  subAgents?: Record<string, SubAgentEntry>
  isStreaming?: boolean
  isSystem?: boolean
  usage?: MessageUsage
  httpTraces?: HttpTrace[]
  httpTracesCount?: number
}

export interface FileDiffData {
  file: string
  start_line: number
  context_before: string[]
  removed: string[]
  added: string[]
  context_after: string[]
}

export interface FilePreviewData {
  file: string
  mode: string
  preview_lines: string[]
  total_lines: number
  start_line?: number
}

export interface ToolCall {
  name: string
  runId?: string
  args?: Record<string, any>
  result?: string
  streamingOutput?: string
  pid?: number
  bgProcessRunning?: boolean
  fileDiff?: FileDiffData
  filePreview?: FilePreviewData
  status: 'pending' | 'running' | 'done' | 'error' | 'cancelled' | 'interrupted'
  startTime?: number
  duration?: number
  resultLength?: number
  is_subagent?: boolean
  sub_session_id?: string
}

export interface InterruptInfo {
  actionRequests: any[]
  reviewConfigs: any[]
  data: any[]
}

export interface ReplayMessage {
  role: 'user' | 'assistant'
  content: string | ContentBlock[]
}

export interface SendMessageOptions {
  replaceFromMessageId?: string
  history?: ReplayMessage[]
  llmParams?: Record<string, any> | null
}

function normalizeToolStatus(status: any): ToolCall['status'] {
  if (status === 'pending' || status === 'running' || status === 'done' || status === 'error') {
    return status
  }
  if (status === 'cancelled' || status === 'interrupted') return status
  if (status === 'success') return 'done'
  return 'done'
}

function normalizeSubAgentDoneStatus(status: any): SubAgentEntry['status'] {
  if (status === 'error' || status === 'cancelled' || status === 'interrupted') return status
  return 'done'
}

function ensureToolMarkers(content: string, toolCalls?: ToolCall[]): string {
  if (!toolCalls?.length) return content
  const missingIndexes = toolCalls
    .map((_, idx) => idx)
    .filter(idx => !content.includes(`<!--TOOL:${idx}-->`))
  if (missingIndexes.length === 0) return content
  return `${content}\n${missingIndexes.map(idx => `<!--TOOL:${idx}-->`).join('\n')}\n`
}

function ensureHttpMarkers(content: string, traceCount: number): string {
  if (traceCount <= 0) return content
  const missing = Array.from({ length: traceCount }, (_, i) => i)
    .filter(i => !content.includes(`<!--HTTP:${i}-->`))
  if (missing.length === 0) return content
  return `${content}\n${missing.map(i => `<!--HTTP:${i}-->`).join('\n')}\n`
}

function normalizeHistoryUsage(rawUsage: any): MessageUsage | undefined {
  if (!rawUsage) return undefined
  const rounds = (rawUsage.rounds || []).map((round: any) => ({
    inputTokens: round.inputTokens ?? round.input_tokens ?? 0,
    outputTokens: round.outputTokens ?? round.output_tokens ?? 0,
    totalTokens: round.totalTokens ?? round.total_tokens ?? 0,
    cacheReadTokens: round.cacheReadTokens ?? round.cache_read_tokens ?? 0,
    reasoningTokens: round.reasoningTokens ?? round.reasoning_tokens ?? 0,
    duration: round.duration ?? round.duration_ms,
  }))
  return {
    rounds,
    toolCallCount: rawUsage.toolCallCount ?? rawUsage.tool_call_count ?? 0,
    totalDuration: rawUsage.totalDuration ?? rawUsage.total_duration_ms,
  }
}

function normalizeHttpTrace(raw: any): HttpTrace {
  return {
    id: raw.id || createClientId(),
    sequence: raw.sequence ?? 0,
    kind: 'llm_http',
    provider: raw.provider || undefined,
    model: raw.model || undefined,
    startedAt: raw.startedAt ?? raw.started_at ?? Date.now(),
    durationMs: raw.durationMs ?? raw.duration_ms,
    request: {
      method: raw.request?.method || undefined,
      url: raw.request?.url || undefined,
      headers: raw.request?.headers || {},
      body: raw.request?.body || '空',
      bodyFormat: raw.request?.bodyFormat ?? raw.request?.body_format ?? 'unknown',
    },
    response: {
      status: raw.response?.status,
      headers: raw.response?.headers || {},
      body: raw.response?.body || '未返回',
      bodyFormat: raw.response?.bodyFormat ?? raw.response?.body_format ?? 'unknown',
      ok: raw.response?.ok,
    },
    error: raw.error ?? null,
  }
}

function normalizeHttpTraces(raw: any): HttpTrace[] | undefined {
  if (!Array.isArray(raw) || raw.length === 0) return undefined
  return raw.map(normalizeHttpTrace)
}

function normalizeHistoryMessage(msg: any): ChatMessage | null {
  if (msg.role === 'system') {
    const rawContent = msg.content
    let content = ''
    if (Array.isArray(rawContent)) {
      content = rawContent.find((b: any) => b.type === 'text')?.text || ''
    } else {
      content = rawContent || ''
    }
    return {
      id: msg.id || createClientId(),
      role: 'user',
      content,
      timestamp: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
      isSystem: true,
    }
  }

  const role = msg.role === 'human' ? 'user' : msg.role === 'ai' ? 'assistant' : msg.role
  if (!['user', 'assistant', 'tool'].includes(role)) return null

  const toolCalls = (msg.tool_calls || msg.toolCalls || []).map((tc: any) => ({
    name: tc.name || '',
    runId: tc.runId || tc.run_id || tc.id,
    args: tc.args || {},
    result: tc.result,
    status: normalizeToolStatus(tc.status),
    startTime: tc.startTime ?? tc.start_time,
    duration: tc.duration,
    resultLength: tc.resultLength ?? tc.result_length ?? tc.result?.length,
    is_subagent: tc.is_subagent || false,
    sub_session_id: tc.sub_session_id || '',
    // 后端入库时已把当时的 diff 挂在 tool_call 上，刷新后直接渲染
    fileDiff: tc.fileDiff ?? tc.file_diff,
    filePreview: tc.filePreview ?? tc.file_preview,
  }))
  const usage = normalizeHistoryUsage(msg.usage)
  if (usage && toolCalls.length > usage.toolCallCount) {
    usage.toolCallCount = toolCalls.length
  }

  const subAgents: Record<string, SubAgentEntry> = {}
  for (const tc of toolCalls) {
    if (tc.is_subagent && tc.runId) {
      subAgents[tc.runId] = {
        tool_call_id: tc.runId,
        name: tc.name,
        sub_session_id: tc.sub_session_id || '',
        query: typeof tc.args === 'object' ? (tc.args?.query || '') : '',
        status: tc.status === 'running' ? 'running' : normalizeSubAgentDoneStatus(tc.status),
        tokenPreview: tc.result || '',
        toolCallCount: 0,
        tokenCount: 0,
        tokens: '',
        thinking: '',
        thinkCount: 0,
        innerToolCalls: [],
        duration: tc.duration,
      }
    }
  }

  const httpTraces = normalizeHttpTraces(msg.http_traces || msg.httpTraces)
  const httpTracesCount = msg.http_traces_count ?? msg.httpTracesCount ?? httpTraces?.length ?? 0
  let content: string | ContentBlock[]
  if (role === 'user') {
    content = Array.isArray(msg.content)
      ? msg.content
      : [{ type: 'text', text: String(msg.content || '') }]
  } else {
    const rawContent = msg.content
    let textContent = ''
    if (Array.isArray(rawContent)) {
      textContent = rawContent.find((b: any) => b.type === 'text')?.text || ''
    } else {
      textContent = rawContent || ''
    }
    textContent = ensureToolMarkers(textContent, toolCalls)
    if (httpTracesCount > 0) {
      textContent = ensureHttpMarkers(textContent, httpTracesCount)
    }
    content = textContent
  }

  return {
    id: msg.id || createClientId(),
    role,
    content,
    timestamp: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
    toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
    subAgents: Object.keys(subAgents).length > 0 ? subAgents : undefined,
    usage,
    httpTraces,
    httpTracesCount,
  }
}

function normalizeHistoryMessages(rawMessages: any[]): ChatMessage[] {
  const loaded: ChatMessage[] = []
  for (const msg of rawMessages) {
    const chatMsg = normalizeHistoryMessage(msg)
    if (!chatMsg) continue
    if (chatMsg.role === 'tool') {
      const lastAssistant = [...loaded].reverse().find(m => m.role === 'assistant')
      if (lastAssistant?.toolCalls) {
        const tc = lastAssistant.toolCalls.find(t => t.name === msg.name && !t.result)
        if (tc) {
          const resultStr = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
          tc.result = resultStr
          tc.status = 'done'
          tc.resultLength = resultStr.length
        }
      }
      continue
    }
    loaded.push(chatMsg)
  }
  return loaded
}

function mergeFinalUsageRounds(targetRounds: LlmRoundUsage[], rawRounds: any[]) {
  rawRounds.forEach((round: any, idx: number) => {
    const normalized = {
      inputTokens: round.input_tokens || 0,
      outputTokens: round.output_tokens || 0,
      totalTokens: round.total_tokens || 0,
      cacheReadTokens: round.cache_read_tokens || 0,
      reasoningTokens: round.reasoning_tokens || 0,
      duration: round.duration_ms || undefined,
    }
    if (targetRounds[idx]) {
      Object.assign(targetRounds[idx], normalized)
    } else {
      targetRounds.push(normalized)
    }
  })
}

export interface SubAgentReducerResult {
  changed: boolean
  shouldRefresh: boolean
}

const SUBAGENT_UNCHANGED: SubAgentReducerResult = { changed: false, shouldRefresh: false }

type SubAgentReducer = (
  message: ChatMessage | undefined,
  msg: SseMessage,
  parentThreadId?: string | null,
) => SubAgentReducerResult

function getSubAgentToolCallId(msg: SseMessage): string {
  return msg.tool_call_id || msg.run_id || ''
}

function findSubAgentMessage(
  messages: ChatMessage[],
  toolCallId: string,
  allowLastAssistantFallback = false,
): ChatMessage | undefined {
  if (!toolCallId) return undefined
  let lastAssistant: ChatMessage | undefined
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message.role !== 'assistant') continue
    if (allowLastAssistantFallback && message.role === 'assistant' && !lastAssistant) {
      lastAssistant = message
    }
    if (message.subAgents?.[toolCallId]) return message
    if (message.toolCalls?.some(t => t.runId === toolCallId)) return message
  }
  return allowLastAssistantFallback ? lastAssistant : undefined
}

export function applySubAgentEventToMessages(
  messages: ChatMessage[],
  msg: SseMessage,
  reducer: SubAgentReducer,
  parentThreadId?: string | null,
): SubAgentReducerResult {
  const toolCallId = getSubAgentToolCallId(msg)
  const message = findSubAgentMessage(messages, toolCallId, msg.type === 'subagent_start')
  return reducer(message, msg, parentThreadId)
}

export function applySubAgentStart(
  message: ChatMessage | undefined,
  msg: SseMessage,
  parentThreadId?: string | null,
): SubAgentReducerResult {
  if (!message || message.role !== 'assistant') return SUBAGENT_UNCHANGED

  const toolCallId = msg.tool_call_id || msg.run_id || ''
  if (!toolCallId) return SUBAGENT_UNCHANGED
  const subSessionId = msg.sub_session_id
    || (parentThreadId ? `${parentThreadId}--sa--${toolCallId}` : '')

  const existing = message.subAgents?.[toolCallId]
  const entry: SubAgentEntry = {
    tool_call_id: toolCallId,
    name: msg.name || msg.subagent_type || existing?.name || '子 Agent',
    sub_session_id: subSessionId || existing?.sub_session_id || '',
    query: msg.query || msg.description || existing?.query || '',
    status: 'running',
    tokenPreview: existing?.tokenPreview || '',
    toolCallCount: existing?.toolCallCount || 0,
    tokenCount: existing?.tokenCount || 0,
    tokens: existing?.tokens || '',
    thinking: existing?.thinking || '',
    thinkCount: existing?.thinkCount || 0,
    innerToolCalls: existing?.innerToolCalls || [],
    duration: existing?.duration,
    httpTraces: existing?.httpTraces,
  }
  if (!message.subAgents) {
    message.subAgents = {}
  }
  message.subAgents[toolCallId] = entry

  let tc = message.toolCalls?.find(t => t.runId === toolCallId)
  if (!tc) {
    message.toolCalls = message.toolCalls || []
    tc = {
      name: 'task',
      runId: toolCallId,
      args: msg.description ? { description: msg.description } : undefined,
      status: 'running',
      startTime: Date.now(),
      is_subagent: true,
      sub_session_id: subSessionId,
    }
    message.toolCalls.push(tc)
  }
  tc.is_subagent = true
  tc.sub_session_id = subSessionId
  return { changed: true, shouldRefresh: true }
}

export function applySubAgentToken(
  message: ChatMessage | undefined,
  msg: SseMessage,
): SubAgentReducerResult {
  if (!message?.subAgents) return SUBAGENT_UNCHANGED
  const toolCallId = msg.tool_call_id
  if (!toolCallId) return SUBAGENT_UNCHANGED
  const sa = message.subAgents[toolCallId]
  if (!sa) return SUBAGENT_UNCHANGED

  const newCount = sa.tokenCount + 1
  message.subAgents[toolCallId] = { ...sa, tokens: sa.tokens + (msg.content || ''), tokenCount: newCount }
  return { changed: true, shouldRefresh: newCount % 3 === 0 }
}

export function applySubAgentThinking(
  message: ChatMessage | undefined,
  msg: SseMessage,
): SubAgentReducerResult {
  if (!message?.subAgents) return SUBAGENT_UNCHANGED
  const toolCallId = msg.tool_call_id
  if (!toolCallId) return SUBAGENT_UNCHANGED
  const sa = message.subAgents[toolCallId]
  if (!sa) return SUBAGENT_UNCHANGED

  const newThinkCount = sa.thinkCount + 1
  message.subAgents[toolCallId] = {
    ...sa,
    thinking: sa.thinking + (msg.content || ''),
    thinkCount: newThinkCount,
  }
  return { changed: true, shouldRefresh: newThinkCount % 5 === 0 }
}

export function applySubAgentToolCall(
  message: ChatMessage | undefined,
  msg: SseMessage,
): SubAgentReducerResult {
  if (!message?.subAgents) return SUBAGENT_UNCHANGED
  const toolCallId = msg.tool_call_id
  if (!toolCallId) return SUBAGENT_UNCHANGED
  const sa = message.subAgents[toolCallId]
  if (!sa) return SUBAGENT_UNCHANGED

  message.subAgents[toolCallId] = {
    ...sa,
    innerToolCalls: [...sa.innerToolCalls, {
      name: msg.name || '',
      status: 'running',
      args: msg.args,
    }],
    toolCallCount: sa.toolCallCount + 1,
  }
  return { changed: true, shouldRefresh: true }
}

export function applySubAgentToolResult(
  message: ChatMessage | undefined,
  msg: SseMessage,
): SubAgentReducerResult {
  if (!message?.subAgents) return SUBAGENT_UNCHANGED
  const toolCallId = msg.tool_call_id
  if (!toolCallId) return SUBAGENT_UNCHANGED
  const sa = message.subAgents[toolCallId]
  if (!sa) return SUBAGENT_UNCHANGED

  const updatedCalls = [...sa.innerToolCalls]
  const idx = [...updatedCalls].reverse().findIndex(
    t => t.name === msg.name && t.status === 'running',
  )
  if (idx === -1) return SUBAGENT_UNCHANGED

  const resultStatus = msg.status === 'error' || msg.is_error ? 'error' : 'done'
  const realIdx = updatedCalls.length - 1 - idx
  updatedCalls[realIdx] = { ...updatedCalls[realIdx], result: msg.result, status: resultStatus }
  message.subAgents[toolCallId] = { ...sa, innerToolCalls: updatedCalls }
  return { changed: true, shouldRefresh: true }
}

export function applySubAgentDone(
  message: ChatMessage | undefined,
  msg: SseMessage,
): SubAgentReducerResult {
  if (!message) return SUBAGENT_UNCHANGED
  const toolCallId = msg.tool_call_id
  if (!toolCallId) return SUBAGENT_UNCHANGED
  const sa = message.subAgents?.[toolCallId]
  const rawHttpTraces = msg.http_traces
  const saHttpTraces = rawHttpTraces?.length ? normalizeHttpTraces(rawHttpTraces) : undefined
  const doneStatus = normalizeSubAgentDoneStatus(msg.status)
  if (sa) {
    message.subAgents![toolCallId] = {
      ...sa,
      status: doneStatus,
      tokens: sa.tokens,
      tokenPreview: sa.tokens || msg.result_preview || '',
      duration: msg.duration ?? sa.duration,
      httpTraces: saHttpTraces,
    }
  }
  const tc = message.toolCalls?.find(t => t.runId === toolCallId)
  if (tc) {
    tc.status = doneStatus
    tc.result = sa?.tokens || msg.result_preview || ''
    tc.duration = tc.startTime ? Date.now() - tc.startTime : msg.duration
    tc.resultLength = (tc.result || '').length
  }
  return { changed: !!sa || !!tc, shouldRefresh: true }
}

export interface TodoItem {
  content: string
  status: 'pending' | 'in_progress' | 'completed'
}

export const useChatStore = defineStore('chat', () => {
  // --- Session Registry ---
  // shallowReactive() makes Map.get/set/delete/has reactive (so sidebar streaming
  // indicators update automatically) without deep-unwrapping the Ref fields
  // inside SessionState.
  const activeSessions = shallowReactive(new Map<string, SessionState>())
  const activeSessionId = ref<string | null>(null)
  const sessionOffsets = new Map<string, number>()

  // --- Computed delegates to active session (API unchanged for components) ---
  const _active = (): SessionState | undefined =>
    activeSessionId.value ? activeSessions.get(activeSessionId.value) : undefined

  const messages = computed<ChatMessage[]>(() => _active()?.messages.value ?? [])
  const isStreaming = computed(() => _active()?.isStreaming.value ?? false)
  const interrupt = computed(() => _active()?.interrupt.value ?? null)
  const todos = computed(() => _active()?.todos.value ?? [])
  const errorMessage = computed(() => _active()?.errorMessage.value ?? null)
  const totalMessageCount = computed(() => _active()?.totalMessageCount.value ?? 0)
  const hasOlderMessages = computed(() => _active()?.hasOlderMessages.value ?? false)
  const loadingOlder = computed(() => _active()?.loadingOlder.value ?? false)
  const isHistoryLoading = computed(() => _active()?.isHistoryLoading.value ?? false)
  const isConnected = computed(() => !!activeSessionId.value)
  const threadId = computed(() => activeSessionId.value)
  const lastMessage = computed(() => {
    const msgs = messages.value
    return msgs[msgs.length - 1] ?? null
  })
  const streamStartTime = computed(() => _active()?.streamStartTime ?? null)

  function _createClientForSession(state: SessionState, sessionId: string): ChatSseClient {
    const client = new ChatSseClient()
    state.client = client
    _registerHandlers(client, state, sessionId)
    return client
  }

  function _releaseBackgroundSession(sessionId: string, state: SessionState): void {
    state.client?.disconnect()
    state.client = null
    sessionOffsets.delete(sessionId)
    activeSessions.delete(sessionId)
  }

  function _registerHandlers(client: ChatSseClient, state: SessionState, sessionId: string) {
    client.on('thinking', (msg: SseMessage) => {
      if (!state.isStreaming.value) {
        state.isStreaming.value = true
        state.streamStartTime = Date.now()
        state.currentRoundStart = Date.now()
        state.messages.value.push({
          id: createClientId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = state.messages.value[state.messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (!state.inThinking) {
          state.inThinking = true
          last.content = (last.content as string) + '<!--THINK_START-->'
        }
        last.content = (last.content as string) + (msg.content || '')
      }
    })

    client.on('token', (msg: SseMessage) => {
      if (!state.isStreaming.value) {
        state.isStreaming.value = true
        state.streamStartTime = Date.now()
        state.currentRoundStart = Date.now()
        state.messages.value.push({
          id: createClientId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = state.messages.value[state.messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (state.inThinking) {
          state.inThinking = false
          last.content = (last.content as string) + '<!--THINK_END-->'
        }
        last.content = (last.content as string) + (msg.content || '')
      }
    })

    client.on('content', (msg: SseMessage) => {
      const last = state.messages.value[state.messages.value.length - 1]
      if (last && last.role === 'assistant') {
        last.content = (last.content as string) + (msg.content || '')
      }
    })

    client.on('llm_usage', (msg: SseMessage) => {
      const last = state.messages.value[state.messages.value.length - 1]
      if (last?.usage) {
        const roundDuration = state.currentRoundStart ? Date.now() - state.currentRoundStart : undefined
        last.usage.rounds.push({
          inputTokens: msg.input_tokens || 0,
          outputTokens: msg.output_tokens || 0,
          totalTokens: msg.total_tokens || 0,
          cacheReadTokens: msg.cache_read_tokens || 0,
          reasoningTokens: msg.reasoning_tokens || 0,
          duration: roundDuration,
        })
        state.currentRoundStart = Date.now()
      }
    })

    client.on('tool_call', (msg: SseMessage) => {
      if (!state.isStreaming.value) {
        state.isStreaming.value = true
        state.streamStartTime = Date.now()
        state.currentRoundStart = Date.now()
        state.messages.value.push({
          id: createClientId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = state.messages.value[state.messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (state.inThinking) {
          state.inThinking = false
          last.content = (last.content as string) + '<!--THINK_END-->'
        }
        if (!last.toolCalls) last.toolCalls = []

        const toolCallId = msg.tool_call_id || msg.run_id
        if (!toolCallId) {
          console.warn('[Chat] Ignored tool_call without tool_call_id', msg)
          return
        }
        const existingByToolCallId = last.toolCalls.find(t => t.runId === toolCallId)
        if (existingByToolCallId) {
          return
        }

        const tcIdx = last.toolCalls.length
        const tc: ToolCall = {
          name: msg.name || '',
          runId: toolCallId,
          args: msg.args,
          status: 'running',
          startTime: Date.now(),
          is_subagent: msg.is_subagent,
          sub_session_id: msg.sub_session_id,
        }
        last.toolCalls.push(tc)
        last.content = (last.content as string) + `\n<!--TOOL:${tcIdx}-->\n`
        if (last.usage) {
          last.usage.toolCallCount++
        }
        if (msg.name === 'write_todos' && msg.args?.todos) {
          state.todos.value = msg.args.todos as TodoItem[]
        }
      }
    })

    client.on('tool_result', (msg: SseMessage) => {
      const last = state.messages.value[state.messages.value.length - 1]
      if (last?.toolCalls) {
        const toolCallId = msg.tool_call_id
        if (!toolCallId) {
          console.warn('[Chat] Ignored tool_result without tool_call_id', msg)
          return
        }
        const tc = last.toolCalls.find(t => t.runId === toolCallId)
        if (tc) {
          tc.result = msg.result
          tc.status = (msg.status === 'error' || msg.is_error) ? 'error' : 'done'
          tc.duration = tc.startTime ? Date.now() - tc.startTime : undefined
          tc.resultLength = msg.result?.length || 0
          const isBgRunning = tc.name === 'command__start_background_process'
            && tc.pid
            && msg.result?.includes('Status: running')
          if (isBgRunning) {
            tc.bgProcessRunning = true
          } else {
            delete tc.streamingOutput
          }
          if (tc.name === 'command__start_background_process' || tc.name === 'command__kill_process') {
            window.dispatchEvent(new Event('bg-process-changed'))
          }
        }
      }
    })

    client.on('tool_output_chunk', (msg: SseMessage) => {
      const last = state.messages.value[state.messages.value.length - 1]
      if (last?.toolCalls) {
        const toolCallId = msg.tool_call_id
        if (!toolCallId) return
        const tc = last.toolCalls.find(t => t.runId === toolCallId)
        if (tc && tc.status === 'running') {
          tc.streamingOutput = (tc.streamingOutput || '') + (msg.content || '')
        }
      }
    })

    client.on('tool_process_info', (msg: SseMessage) => {
      const last = state.messages.value[state.messages.value.length - 1]
      if (last?.toolCalls) {
        const toolCallId = msg.tool_call_id
        if (!toolCallId) return
        const tc = last.toolCalls.find(t => t.runId === toolCallId)
        if (tc) {
          tc.pid = msg.pid
        }
      }
    })

    client.on('tool_file_diff', (msg: SseMessage) => {
      const last = state.messages.value[state.messages.value.length - 1]
      if (last?.toolCalls) {
        const toolCallId = msg.tool_call_id
        if (!toolCallId) return
        const tc = last.toolCalls.find(t => t.runId === toolCallId)
        if (tc) {
          tc.fileDiff = {
            file: (msg as any).file || '',
            start_line: (msg as any).start_line || 1,
            context_before: (msg as any).context_before || [],
            removed: (msg as any).removed || [],
            added: (msg as any).added || [],
            context_after: (msg as any).context_after || [],
          }
        }
      }
    })

    client.on('tool_file_preview', (msg: SseMessage) => {
      const last = state.messages.value[state.messages.value.length - 1]
      if (last?.toolCalls) {
        const toolCallId = msg.tool_call_id
        if (!toolCallId) return
        const tc = last.toolCalls.find(t => t.runId === toolCallId)
        if (tc) {
          tc.filePreview = {
            file: (msg as any).file || '',
            mode: (msg as any).mode || 'rewrite',
            preview_lines: (msg as any).preview_lines || [],
            total_lines: (msg as any).total_lines || 0,
            start_line: (msg as any).start_line || 1,
          }
        }
      }
    })

    client.on('file_change', (msg: SseMessage) => {
      if (sessionId !== activeSessionId.value) return
      const filePath = (msg as any).file_path || ''
      if (!filePath) return
      const eventSessionId = (msg as any).session_id || ''
      const isSubAgent = eventSessionId && eventSessionId !== sessionId && eventSessionId.includes('--sa--')
      const fileChangesStore = useFileChangesStore()
      if (isSubAgent) {
        // Sub-agent change — will be fully loaded on drawer open via fetchFileChanges
        return
      }
      fileChangesStore.addFileChange({
        file_path: filePath,
        change_type: (msg as any).change_type || 'edit',
        move_destination: (msg as any).move_destination,
        round_number: (msg as any).round_number ?? null,
        old_string: (msg as any).old_string,
        new_string: (msg as any).new_string,
      })
    })

    client.on('file_change_git_snapshot', (msg: SseMessage) => {
      if (sessionId !== activeSessionId.value) return
      const eventSessionId = (msg as any).session_id || ''
      if (eventSessionId && eventSessionId !== sessionId) return
      const fileChangesStore = useFileChangesStore()
      const hash = (msg as any).git_base_hash
      if (hash) fileChangesStore.gitBaseHash = hash
    })

    client.on('subagent_start', (msg: SseMessage) => {
      const result = applySubAgentEventToMessages(state.messages.value, msg, applySubAgentStart, sessionId)
      if (result.shouldRefresh) {
        state.messages.value = [...state.messages.value]
      }
    })

    client.on('subagent_token', (msg: SseMessage) => {
      const result = applySubAgentEventToMessages(state.messages.value, msg, applySubAgentToken, sessionId)
      if (result.shouldRefresh) {
        state.messages.value = [...state.messages.value]
      }
    })

    client.on('subagent_thinking', (msg: SseMessage) => {
      const result = applySubAgentEventToMessages(state.messages.value, msg, applySubAgentThinking, sessionId)
      if (result.shouldRefresh) {
        state.messages.value = [...state.messages.value]
      }
    })

    client.on('subagent_tool_call', (msg: SseMessage) => {
      const result = applySubAgentEventToMessages(state.messages.value, msg, applySubAgentToolCall, sessionId)
      if (result.shouldRefresh) {
        state.messages.value = [...state.messages.value]
      }
    })

    client.on('subagent_tool_result', (msg: SseMessage) => {
      const result = applySubAgentEventToMessages(state.messages.value, msg, applySubAgentToolResult, sessionId)
      if (result.shouldRefresh) {
        state.messages.value = [...state.messages.value]
      }
    })

    client.on('subagent_done', (msg: SseMessage) => {
      const result = applySubAgentEventToMessages(state.messages.value, msg, applySubAgentDone, sessionId)
      if (result.shouldRefresh) {
        state.messages.value = [...state.messages.value]
      }
    })

    client.on('interrupt', (msg: SseMessage) => {
      state.interrupt.value = {
        actionRequests: msg.action_requests || [],
        reviewConfigs: msg.review_configs || [],
        data: msg.data || [],
      }
    })

    client.on('done', (msg: SseMessage) => {
      state.errorMessage.value = null
      state.isStreaming.value = false
      state.inThinking = false
      const last = state.messages.value[state.messages.value.length - 1]
      if (last) {
        last.isStreaming = false
        const isResume = !!msg.is_resume
        const usageData = msg.usage as any[] | undefined
        if (usageData && usageData.length > 0) {
          if (last.usage && state.streamStartTime) {
            last.usage.totalDuration = Date.now() - state.streamStartTime
          }
          if (last.usage) {
            if (isResume) {
              const offset = last.usage.rounds.length - usageData.length
              usageData.forEach((round: any, idx: number) => {
                const normalized = {
                  inputTokens: round.input_tokens || 0,
                  outputTokens: round.output_tokens || 0,
                  totalTokens: round.total_tokens || 0,
                  cacheReadTokens: round.cache_read_tokens || 0,
                  reasoningTokens: round.reasoning_tokens || 0,
                  duration: round.duration_ms || undefined,
                }
                const targetIdx = offset + idx
                if (targetIdx >= 0 && last.usage!.rounds[targetIdx]) {
                  Object.assign(last.usage!.rounds[targetIdx], normalized)
                } else {
                  last.usage!.rounds.push(normalized)
                }
              })
            } else {
              mergeFinalUsageRounds(last.usage.rounds, usageData)
            }
          }
        }
        const rawTraces = (msg as any).http_traces || (msg as any).httpTraces
        if (rawTraces) {
          const newTraces = normalizeHttpTraces(rawTraces) || []
          if (isResume && newTraces.length) {
            last.httpTraces = [...(last.httpTraces || []), ...newTraces]
          } else if (newTraces.length) {
            last.httpTraces = newTraces
          }
          if (last.httpTraces?.length) {
            last.content = ensureHttpMarkers(last.content as string, last.httpTraces.length)
          }
        }
      }
      setTimeout(() => {
        const sessionsStore = useSessionsStore()
        sessionsStore.refreshSessionTitle(sessionId)
      }, 3000)
      // Auto-cleanup: if this session is no longer the active one, release resources
      if (sessionId !== activeSessionId.value) {
        useSessionsStore().markCompletedUnseen(sessionId)
        _releaseBackgroundSession(sessionId, state)
      }
    })

    client.on('cancelled', () => {
      state.errorMessage.value = null
      state.isStreaming.value = false
      state.inThinking = false
      const last = state.messages.value[state.messages.value.length - 1]
      if (last) last.isStreaming = false
      // Auto-cleanup: if this session is no longer the active one, release resources
      if (sessionId !== activeSessionId.value) {
        _releaseBackgroundSession(sessionId, state)
      }
    })

    client.on('error', (msg: SseMessage) => {
      state.isStreaming.value = false
      if (state.inThinking) {
        const last = state.messages.value[state.messages.value.length - 1]
        if (last && last.role === 'assistant') {
          last.content = (last.content as string) + '<!--THINK_END-->'
        }
        state.inThinking = false
      }
      const lastMsg = state.messages.value[state.messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.isStreaming = false
      }
      if (msg.title) {
        state.errorMessage.value = {
          title: msg.title,
          detail: msg.detail || '',
          suggestions: msg.suggestions,
          techDetail: msg.tech_detail,
          errorCode: msg.error_code,
        }
      } else {
        state.errorMessage.value = {
          title: 'AI 模型接口请求失败',
          detail: msg.message || '',
          suggestions: ['请稍后重试，如问题持续请联系管理员'],
          errorCode: 'UNKNOWN',
        }
      }
      console.error('[Chat] Error:', msg.message || msg.title)
      // Auto-cleanup: if this session is no longer the active one, release resources
      if (sessionId !== activeSessionId.value) {
        _releaseBackgroundSession(sessionId, state)
      }
    })

    client.on('title_update', (msg: SseMessage) => {
      if (msg.thread_id && msg.title) {
        const sessionsStore = useSessionsStore()
        sessionsStore.updateTitleLocal(msg.thread_id, msg.title)
      }
    })
  }

  /**
   * Switch the active session. If the departing session is streaming, it stays
   * in the registry and continues in the background. If it is idle, it is
   * released immediately. The arriving session is loaded from DB unless it is
   * already in the registry (was streaming in background).
   */
  async function switchToSession(sessionId: string): Promise<void> {
    if (activeSessionId.value === sessionId) return

    // Departing session
    const oldId = activeSessionId.value
    if (oldId) {
      const old = activeSessions.get(oldId)
      if (old && !old.isStreaming.value) {
        _releaseBackgroundSession(oldId, old)
      }
      // Streaming session: keep in map — SSE continues in background
    }

    activeSessionId.value = sessionId
    useSessionsStore().markSessionViewed(sessionId)
    const fcStore = useFileChangesStore()
    fcStore.reset()
    fcStore.fetchFileChanges(sessionId)

    // Arriving session: already in registry means it was streaming in background
    if (activeSessions.has(sessionId)) return

    // New session: create state, load messages, connect client
    const state = createSessionState()
    activeSessions.set(sessionId, state)
    await _loadMessagesIntoState(sessionId, state)

    // Stale switch guard: verify this is still the current state object for
    // this session. Catches the A→B→A rapid-switch case where a second
    // switchToSession(A) created a new state and replaced ours in the map.
    // Only return — do NOT delete from the map (that would evict the
    // replacement state that is still loading).
    if (activeSessions.get(sessionId) !== state) {
      return
    }

    const client = _createClientForSession(state, sessionId)
    client.setThreadId(sessionId)
  }

  /** Expose session streaming state for sidebar indicators */
  function isSessionStreaming(sessionId: string): boolean {
    return activeSessions.get(sessionId)?.isStreaming.value ?? false
  }

  function getStreamingSessionIds(): string[] {
    return [...activeSessions.keys()].filter(id =>
      activeSessions.get(id)?.isStreaming.value
    )
  }

  async function sendMessage(
    content: ContentBlock[],
    presetId: string = 'chat',
    modelId: string = '',
    options: SendMessageOptions = {},
  ) {
    if (!content.length) return

    const sessionsStore = useSessionsStore()
    const sessionId = sessionsStore.currentSessionId
    if (sessionId && sessionsStore.isLocalSession(sessionId)) {
      const isFirstMessage = sessionsStore.currentSession?.message_count === 0
      const realId = await sessionsStore.persistSession(sessionId, modelId)
      await switchToSession(realId)
      if (isFirstMessage) {
        const firstText = content.find(b => b.type === 'text')?.text || ''
        sessionsStore.updateTitleLocal(realId, firstText.slice(0, 30))
      }
    } else if (!activeSessionId.value) {
      if (sessionId) await switchToSession(sessionId)
    }

    const state = activeSessionId.value ? activeSessions.get(activeSessionId.value) : undefined
    if (!state?.client) return

    state.errorMessage.value = null

    state.messages.value.push({
      id: createClientId(),
      role: 'user',
      content,
      timestamp: Date.now(),
    })

    state.client.sendMessage(content, presetId, modelId, {
      replaceFromMessageId: options.replaceFromMessageId,
      history: options.history,
      llmParams: options.llmParams,
    })
  }

  function respondToInterrupt(
    approved: boolean,
    presetId: string = 'chat',
    permanentlyAllow?: string,
    llmParams?: Record<string, any> | null,
  ) {
    const state = _active()
    if (!state?.client) return
    const count = state.interrupt.value?.actionRequests?.length || 1
    const decisions = Array.from({ length: count }, () => ({
      type: approved ? 'approve' : 'reject',
    }))
    const resumePayload: Record<string, any> = { decisions }
    if (permanentlyAllow) {
      resumePayload.permanently_allow = permanentlyAllow
    }
    state.client.sendInterruptResume(resumePayload, presetId, undefined, llmParams)
    state.interrupt.value = null
    state.isStreaming.value = true
    state.currentRoundStart = Date.now()
    const last = state.messages.value[state.messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.isStreaming = true
    }
  }

  function resumeInterrupt(
    resumeValue: any,
    presetId: string = 'chat',
    model?: string,
    llmParams?: Record<string, any> | null,
  ) {
    const state = _active()
    if (!state?.client) return
    state.client.sendInterruptResume(resumeValue, presetId, model, llmParams)
    state.interrupt.value = null
    state.isStreaming.value = true
    state.currentRoundStart = Date.now()
    const last = state.messages.value[state.messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.isStreaming = true
    }
  }

  async function _loadMessagesIntoState(sessionId: string, state: SessionState): Promise<void> {
    const sessionsStore = useSessionsStore()
    state.isHistoryLoading.value = true
    try {
      if (sessionsStore.isLocalSession(sessionId)) {
        state.totalMessageCount.value = 0
        sessionOffsets.set(sessionId, 0)
        state.messages.value = []
        state.hasOlderMessages.value = false
        state.errorMessage.value = null
        return
      }

      const resp = await api.getSessionMessages(sessionId, { limit: INITIAL_MESSAGE_LIMIT })
      const total = resp?.total ?? 0
      const rawMessages = resp?.messages ?? resp
      state.totalMessageCount.value = total
      sessionOffsets.set(sessionId, resp?.offset ?? 0)

      // Always set messages on API success — this ensures session switches always
      // replace the current messages, even when the target session returns empty.
      state.messages.value = normalizeHistoryMessages(
        Array.isArray(rawMessages) ? rawMessages : []
      )
      state.hasOlderMessages.value = total > state.messages.value.length
      const session = sessionsStore.sessions.find(item => item.id === sessionId)
      if (session && session.message_count > 0 && state.messages.value.length === 0) {
        state.errorMessage.value = {
          title: '会话内容未返回',
          detail: '该会话已有保存的消息，但本次没有读取到内容。内容未被删除。',
          suggestions: ['请重新加载会话内容。'],
          errorCode: 'HISTORY_EMPTY',
        }
      } else {
        state.errorMessage.value = null
      }
    } catch (e) {
      console.error('[Chat] Failed to load messages:', e)
      state.errorMessage.value = {
        title: '会话内容加载失败',
        detail: '无法读取已保存的会话内容。内容未被删除。',
        suggestions: ['请重新加载会话内容。'],
        techDetail: e instanceof Error ? e.message : String(e),
        errorCode: 'HISTORY_LOAD_FAILED',
      }
    } finally {
      state.isHistoryLoading.value = false
    }
  }

  async function loadMessages(sessionId: string): Promise<void> {
    // If the target session is in the registry, load into its own state.
    // Otherwise fall back to the currently active session — this supports
    // temporary display of sub-session messages without a full session switch.
    const targetState = activeSessions.get(sessionId) ?? _active()
    if (targetState) {
      await _loadMessagesIntoState(sessionId, targetState)
    }
  }

  async function loadOlderMessages(sessionId: string) {
    const state = _active()
    if (!state) return
    const currentOffset = sessionOffsets.get(sessionId) ?? 0
    if (!state.hasOlderMessages.value || state.loadingOlder.value || currentOffset <= 0) return
    state.loadingOlder.value = true
    try {
      const olderPageSize = INITIAL_MESSAGE_LIMIT
      const newOffset = Math.max(0, currentOffset - olderPageSize)
      const newLimit = currentOffset - newOffset
      if (newLimit <= 0) return

      const resp = await api.getSessionMessages(sessionId, { limit: newLimit, offset: newOffset })
      const olderRaw = resp?.messages ?? []
      if (olderRaw.length === 0) return

      sessionOffsets.set(sessionId, newOffset)
      const olderNormalized = normalizeHistoryMessages(olderRaw)
      state.messages.value = [...olderNormalized, ...state.messages.value]
      state.hasOlderMessages.value = state.totalMessageCount.value > state.messages.value.length
    } catch (e) {
      console.error('[Chat] Failed to load older messages:', e)
    } finally {
      state.loadingOlder.value = false
    }
  }

  function stopGeneration() {
    const state = _active()
    if (state?.client && state.isStreaming.value) {
      state.client.sendCancel()
    }
  }

  function clearMessages() {
    const state = _active()
    if (state) {
      state.messages.value = []
      state.todos.value = []
      state.interrupt.value = null
      state.errorMessage.value = null
    }
  }

  function truncateAfterMessage(messageId: string) {
    const state = _active()
    if (!state) return
    const idx = state.messages.value.findIndex(m => m.id === messageId)
    if (idx < 0) return
    state.messages.value = state.messages.value.slice(0, idx)
  }

  return {
    messages,
    isStreaming,
    isConnected,
    threadId,
    streamStartTime,
    interrupt,
    lastMessage,
    todos,
    errorMessage,
    totalMessageCount,
    hasOlderMessages,
    loadingOlder,
    isHistoryLoading,
    switchToSession,
    isSessionStreaming,
    getStreamingSessionIds,
    loadMessages,
    loadOlderMessages,
    sendMessage,
    stopGeneration,
    respondToInterrupt,
    resumeInterrupt,
    clearMessages,
    truncateAfterMessage,
  }
})
