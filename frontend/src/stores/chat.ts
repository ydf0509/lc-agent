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

  return {
    id: msg.id || createClientId(),
    role,
    content: role === 'assistant' ? ensureToolMarkers(msg.content || '', toolCalls) : msg.content || '',
    timestamp: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
    toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
    usage,
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

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const isConnected = ref(false)
  const threadId = ref<string | null>(null)
  const interrupt = ref<InterruptInfo | null>(null)
  const ws = ref<ChatWebSocket | null>(null)

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
  }

  return {
    messages,
    isStreaming,
    isConnected,
    threadId,
    interrupt,
    lastMessage,
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
