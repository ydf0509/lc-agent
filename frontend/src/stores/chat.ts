import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ChatWebSocket, type WsMessage } from '@/api/websocket'
import { useSessionsStore } from '@/stores/sessions'
import { api } from '@/api/http'
import { createClientId } from '@/utils/client-id'

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

export interface ContentSegment {
  type: 'text' | 'tool'
  text?: string
  toolCall?: ToolCall
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp: number
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  isStreaming?: boolean
  usage?: MessageUsage
  httpTraces?: HttpTrace[]
}

export interface ToolCall {
  name: string
  runId?: string
  args?: Record<string, any>
  result?: string
  status: 'pending' | 'running' | 'done' | 'error'
  startTime?: number
  duration?: number
  resultLength?: number
}

export interface InterruptInfo {
  actionRequests: any[]
  reviewConfigs: any[]
}

export interface ReplayMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SendMessageOptions {
  replaceFromMessageId?: string
  history?: ReplayMessage[]
}

function normalizeToolStatus(status: any): ToolCall['status'] {
  if (status === 'pending' || status === 'running' || status === 'done' || status === 'error') {
    return status
  }
  if (status === 'success') return 'done'
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
  }))
  const usage = normalizeHistoryUsage(msg.usage)
  if (usage && toolCalls.length > usage.toolCallCount) {
    usage.toolCallCount = toolCalls.length
  }

  const httpTraces = normalizeHttpTraces(msg.http_traces || msg.httpTraces)
  let content = role === 'assistant' ? ensureToolMarkers(msg.content || '', toolCalls) : msg.content || ''
  if (role === 'assistant' && httpTraces?.length) {
    content = ensureHttpMarkers(content, httpTraces.length)
  }

  return {
    id: msg.id || createClientId(),
    role,
    content,
    timestamp: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
    toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
    usage,
    httpTraces,
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

export interface TodoItem {
  content: string
  status: 'pending' | 'in_progress' | 'completed'
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const isConnected = ref(false)
  const threadId = ref<string | null>(null)
  const interrupt = ref<InterruptInfo | null>(null)
  const ws = ref<ChatWebSocket | null>(null)
  const todos = ref<TodoItem[]>([])

  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  async function connect(existingThreadId?: string) {
    ws.value = new ChatWebSocket()

    let streamStartTime = 0
    let currentRoundStart = 0
    let inThinking = false

    ws.value.on('thinking', (msg: WsMessage) => {
      if (!isStreaming.value) {
        isStreaming.value = true
        streamStartTime = Date.now()
        currentRoundStart = Date.now()
        messages.value.push({
          id: createClientId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (!inThinking) {
          inThinking = true
          last.content += '<!--THINK_START-->'
        }
        last.content += msg.content || ''
      }
    })

    ws.value.on('token', (msg: WsMessage) => {
      if (!isStreaming.value) {
        isStreaming.value = true
        streamStartTime = Date.now()
        currentRoundStart = Date.now()
        messages.value.push({
          id: createClientId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (inThinking) {
          inThinking = false
          last.content += '<!--THINK_END-->'
        }
        last.content += msg.content || ''
      }
    })

    ws.value.on('content', (msg: WsMessage) => {
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        last.content += msg.content || ''
      }
    })

    ws.value.on('llm_usage', (msg: WsMessage) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.usage) {
        const roundDuration = currentRoundStart ? Date.now() - currentRoundStart : undefined
        last.usage.rounds.push({
          inputTokens: msg.input_tokens || 0,
          outputTokens: msg.output_tokens || 0,
          totalTokens: msg.total_tokens || 0,
          cacheReadTokens: msg.cache_read_tokens || 0,
          reasoningTokens: msg.reasoning_tokens || 0,
          duration: roundDuration,
        })
        currentRoundStart = Date.now()
      }
    })


    ws.value.on('tool_call', (msg: WsMessage) => {
      if (!isStreaming.value) {
        isStreaming.value = true
        streamStartTime = Date.now()
        currentRoundStart = Date.now()
        messages.value.push({
          id: createClientId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (inThinking) {
          inThinking = false
          last.content += '<!--THINK_END-->'
        }
        if (!last.toolCalls) last.toolCalls = []
        const tcIdx = last.toolCalls.length
        const tc: ToolCall = {
          name: msg.name || '',
          runId: msg.run_id,
          args: msg.args,
          status: 'running',
          startTime: Date.now(),
        }
        last.toolCalls.push(tc)
        last.content += `\n<!--TOOL:${tcIdx}-->\n`
        if (last.usage) {
          last.usage.toolCallCount++
        }
        if (msg.name === 'write_todos' && msg.args?.todos) {
          todos.value = msg.args.todos as TodoItem[]
        }
      }
    })

    ws.value.on('tool_result', (msg: WsMessage) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.toolCalls) {
        const tc = last.toolCalls.find(t => t.name === msg.name && t.status === 'running')
        if (tc) {
          tc.result = msg.result
          tc.status = 'done'
          tc.duration = tc.startTime ? Date.now() - tc.startTime : undefined
          tc.resultLength = msg.result?.length || 0
        }
      }
    })

    ws.value.on('interrupt', (msg: WsMessage) => {
      interrupt.value = {
        actionRequests: msg.action_requests || [],
        reviewConfigs: msg.review_configs || [],
      }
    })

    ws.value.on('done', (msg: WsMessage) => {
      isStreaming.value = false
      const last = messages.value[messages.value.length - 1]
      if (last) {
        last.isStreaming = false
        if (last.usage && streamStartTime) {
          last.usage.totalDuration = Date.now() - streamStartTime
        }
        const usageData = (msg as any).usage as any[] | undefined
        if (usageData && usageData.length > 0 && last.usage) {
          mergeFinalUsageRounds(last.usage.rounds, usageData)
        }
        last.httpTraces = normalizeHttpTraces((msg as any).http_traces || (msg as any).httpTraces)
        if (last.httpTraces?.length) {
          last.content = ensureHttpMarkers(last.content, last.httpTraces.length)
        }
      }
    })

    ws.value.on('cancelled', () => {
      isStreaming.value = false
      const last = messages.value[messages.value.length - 1]
      if (last) last.isStreaming = false
    })

    ws.value.on('disconnected', () => {
      if (ws.value?.connected) return
      isConnected.value = false
      isStreaming.value = false
      threadId.value = null
      const last = messages.value[messages.value.length - 1]
      if (last) last.isStreaming = false
    })

    ws.value.on('error', (msg: WsMessage) => {
      isStreaming.value = false
      console.error('[Chat] Error:', msg.message)
    })

    ws.value.on('history', (msg: WsMessage) => {
      const historyMessages = (msg as any).messages || []
      messages.value = normalizeHistoryMessages(historyMessages)
    })

    ws.value.on('title_update', (msg: WsMessage) => {
      if (msg.thread_id && msg.title) {
        const sessionsStore = useSessionsStore()
        sessionsStore.updateTitleLocal(msg.thread_id, msg.title)
      }
    })

    try {
      const tid = await ws.value.connect(existingThreadId)
      threadId.value = tid
      isConnected.value = true
    } catch (e) {
      console.error('[Chat] Failed to connect:', e)
      isConnected.value = false
    }
  }

  async function sendMessage(
    content: string,
    presetId: string = '__chat__',
    modelId: string = '',
    options: SendMessageOptions = {},
  ) {
    if (!content.trim()) return

    const sessionsStore = useSessionsStore()
    const sessionId = sessionsStore.currentSessionId
    if (sessionId && sessionsStore.isLocalSession(sessionId)) {
      const isFirstMessage = sessionsStore.currentSession?.message_count === 0
      const realId = await sessionsStore.persistSession(sessionId, modelId)
      // Always reconnect with the persisted session ID
      ws.value?.disconnect()
      await connect(realId)
      // Immediately show user's message as title for new conversations
      if (isFirstMessage) {
        sessionsStore.updateTitleLocal(realId, content.trim().slice(0, 30))
      }
    } else if (!ws.value || !isConnected.value) {
      if (sessionId) await connect(sessionId)
    }

    if (!ws.value) return

    messages.value.push({
      id: createClientId(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    })

    ws.value.send({
      type: 'message',
      content: content.trim(),
      preset_id: presetId,
      model: modelId,
      replace_from_message_id: options.replaceFromMessageId,
      history: options.history,
    })
  }

  function respondToInterrupt(approved: boolean, presetId: string = '__chat__') {
    ws.value?.sendInterruptResponse(approved, presetId)
    interrupt.value = null
  }

  async function loadMessages(sessionId: string) {
    try {
      const rawMessages = await api.getSessionMessages(sessionId)
      if (!rawMessages || rawMessages.length === 0) return

      messages.value = normalizeHistoryMessages(rawMessages)
    } catch (e) {
      console.error('[Chat] Failed to load messages:', e)
    }
  }

  function stopGeneration() {
    if (ws.value && isStreaming.value) {
      ws.value.sendCancel()
    }
  }

  function clearMessages() {
    messages.value = []
    todos.value = []
  }

  function truncateAfterMessage(messageId: string) {
    const idx = messages.value.findIndex(m => m.id === messageId)
    if (idx < 0) return
    messages.value = messages.value.slice(0, idx)
  }

  function disconnect() {
    ws.value?.disconnect()
    isConnected.value = false
    isStreaming.value = false
    threadId.value = null
    todos.value = []
  }

  return {
    messages,
    isStreaming,
    isConnected,
    threadId,
    interrupt,
    lastMessage,
    todos,
    connect,
    loadMessages,
    sendMessage,
    stopGeneration,
    respondToInterrupt,
    clearMessages,
    truncateAfterMessage,
    disconnect,
  }
})
