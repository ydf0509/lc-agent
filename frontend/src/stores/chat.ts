import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ChatWebSocket, type WsMessage } from '@/api/websocket'
import { useSessionsStore } from '@/stores/sessions'
import { api } from '@/api/http'

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
          id: crypto.randomUUID(),
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
          id: crypto.randomUUID(),
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
          reasoningTokens: 0,
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
          id: crypto.randomUUID(),
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
          if (last.usage.rounds.length === 0) {
            last.usage.rounds = usageData.map((r: any) => ({
              inputTokens: r.input_tokens || 0,
              outputTokens: r.output_tokens || 0,
              totalTokens: r.total_tokens || 0,
              cacheReadTokens: r.cache_read_tokens || 0,
              reasoningTokens: r.reasoning_tokens || 0,
              duration: r.duration_ms || undefined,
            }))
          }
        }
      }
    })

    ws.value.on('cancelled', () => {
      isStreaming.value = false
      const last = messages.value[messages.value.length - 1]
      if (last) last.isStreaming = false
    })

    ws.value.on('error', (msg: WsMessage) => {
      isStreaming.value = false
      console.error('[Chat] Error:', msg.message)
    })

    ws.value.on('history', (msg: WsMessage) => {
      const historyMessages = (msg as any).messages || []
      messages.value = historyMessages.map((m: any, idx: number) => ({
        id: crypto.randomUUID(),
        role: m.role === 'human' ? 'user' : m.role === 'ai' ? 'assistant' : m.role,
        content: m.content || '',
        timestamp: Date.now() - (historyMessages.length - idx) * 1000,
      }))
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

  async function sendMessage(content: string, presetId: string = '__chat__') {
    if (!content.trim()) return

    const sessionsStore = useSessionsStore()
    const sessionId = sessionsStore.currentSessionId
    if (sessionId && sessionsStore.isLocalSession(sessionId)) {
      const isFirstMessage = sessionsStore.currentSession?.message_count === 0
      const realId = await sessionsStore.persistSession(sessionId)
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
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    })

    ws.value.send({
      type: 'message',
      content: content.trim(),
      preset_id: presetId,
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

      const loaded: ChatMessage[] = []
      for (const msg of rawMessages) {
        if (msg.role === 'human') {
          loaded.push({
            id: crypto.randomUUID(),
            role: 'user',
            content: msg.content || '',
            timestamp: Date.now(),
          })
        } else if (msg.role === 'ai') {
          const chatMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: msg.content || '',
            timestamp: Date.now(),
          }
          if (msg.tool_calls && msg.tool_calls.length > 0) {
            chatMsg.toolCalls = msg.tool_calls.map((tc: any) => ({
              name: tc.name,
              args: tc.args || {},
              status: 'done' as const,
            }))
          }
          loaded.push(chatMsg)
        } else if (msg.role === 'tool') {
          const lastAssistant = [...loaded].reverse().find(m => m.role === 'assistant')
          if (lastAssistant?.toolCalls) {
            const tc = lastAssistant.toolCalls.find(t => t.name === msg.name && !t.result)
            if (tc) {
              const resultStr = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
              tc.result = resultStr
              tc.resultLength = resultStr.length
            }
          }
        }
      }
      messages.value = loaded
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

  function disconnect() {
    ws.value?.disconnect()
    isConnected.value = false
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
    disconnect,
  }
})
