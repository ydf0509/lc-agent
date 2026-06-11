import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ChatWebSocket, type WsMessage } from '@/api/websocket'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp: number
  toolCalls?: ToolCall[]
  isStreaming?: boolean
}

export interface ToolCall {
  name: string
  args?: Record<string, any>
  result?: string
  status: 'pending' | 'running' | 'done' | 'error'
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

  async function connect() {
    ws.value = new ChatWebSocket()

    ws.value.on('token', (msg: WsMessage) => {
      if (!isStreaming.value) {
        isStreaming.value = true
        messages.value.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
        })
      }
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        last.content += msg.content || ''
      }
    })

    ws.value.on('tool_call', (msg: WsMessage) => {
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (!last.toolCalls) last.toolCalls = []
        last.toolCalls.push({
          name: msg.name || '',
          status: 'running',
        })
      }
    })

    ws.value.on('tool_result', (msg: WsMessage) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.toolCalls) {
        const tc = last.toolCalls.find(t => t.name === msg.name && t.status === 'running')
        if (tc) {
          tc.result = msg.result
          tc.status = 'done'
        }
      }
    })

    ws.value.on('interrupt', (msg: WsMessage) => {
      interrupt.value = {
        actionRequests: msg.action_requests || [],
        reviewConfigs: msg.review_configs || [],
      }
    })

    ws.value.on('done', () => {
      isStreaming.value = false
      const last = messages.value[messages.value.length - 1]
      if (last) last.isStreaming = false
    })

    ws.value.on('error', (msg: WsMessage) => {
      isStreaming.value = false
      console.error('[Chat] Error:', msg.message)
    })

    try {
      const tid = await ws.value.connect()
      threadId.value = tid
      isConnected.value = true
    } catch (e) {
      console.error('[Chat] Failed to connect:', e)
      isConnected.value = false
    }
  }

  function sendMessage(content: string) {
    if (!ws.value || !content.trim()) return

    messages.value.push({
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    })

    ws.value.sendMessage(content.trim())
  }

  function respondToInterrupt(decision: object) {
    ws.value?.sendInterruptResponse(decision)
    interrupt.value = null
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
    sendMessage,
    respondToInterrupt,
    clearMessages,
    disconnect,
  }
})
