/**
 * SSE-based chat client. Drop-in replacement for ChatWebSocket.
 * Uses fetch + ReadableStream to consume server-sent events.
 */

import type { ContentBlock } from '@/utils/fileUpload'

export interface SseMessage {
  type: string
  content?: string
  thread_id?: string
  title?: string
  name?: string
  subagent_type?: string
  description?: string
  result?: string
  message?: string
  run_id?: string
  tool_call_id?: string
  sub_session_id?: string
  query?: string
  status?: 'running' | 'done' | 'error' | string
  result_preview?: string
  // 工具结果里的图片张数 / 图片估算 token（图片不进 result 文本）
  image_count?: number
  image_tokens?: number
  duration?: number
  tool_count?: number
  token_count?: number
  // summarization visibility events
  summarized_count?: number
  total_count?: number
  kept_count?: number
  reason?: string
  args?: Record<string, any>
  action_requests?: any[]
  review_configs?: any[]
  data?: any[]
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  cache_read_tokens?: number
  reasoning_tokens?: number
  duration_ms?: number
  // llm_usage：轮次归属，main=主 Agent，sub=子 Agent
  role?: 'main' | 'sub' | string
  usage?: any[]
  http_traces?: any[]
  is_resume?: boolean
  is_subagent?: boolean
  is_error?: boolean
  pid?: number
  command?: string
  // error fields
  error_code?: string
  detail?: string
  suggestions?: string[]
  tech_detail?: string
}

export type SseEventHandler = (msg: SseMessage) => void


function getSseAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

function appendTokenToUrl(url: string): string {
  const token = localStorage.getItem('token') || ''
  if (!token) return url
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}token=${encodeURIComponent(token)}`
}

export class ChatSseClient {
  private baseUrl: string
  private handlers: Map<string, SseEventHandler[]> = new Map()
  private _threadId: string | null = null
  private _abortController: AbortController | null = null
  private _streaming = false
  // 每路请求一个独立标识：被更新的流取代后，旧流的迟到收尾不再补发终止事件
  private _streamToken: object | null = null
  // 本路流是否已发过终止事件（done / error / cancelled），保证只发一次
  private _terminalEmitted = false

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl || window.location.origin
  }

  get threadId() { return this._threadId }
  get connected() { return true }
  get streaming() { return this._streaming }

  setThreadId(threadId: string) {
    this._threadId = threadId
  }

  async sendMessage(
    content: ContentBlock[],
    presetId?: string,
    model?: string,
    options?: { replaceFromMessageId?: string; history?: any[]; llmParams?: Record<string, any> | null },
  ): Promise<void> {
    if (!this._threadId) throw new Error('threadId not set')

    const body: Record<string, any> = {
      input: content,
      preset_id: presetId || 'chat',
      model: model || '',
    }
    if (options?.replaceFromMessageId) {
      body.replace_from_message_id = options.replaceFromMessageId
      body.history = options.history || []
    }
    if (options?.llmParams && Object.keys(options.llmParams).length > 0) {
      body.llm_params = options.llmParams
    }

    await this._startStream(body)
  }

  async sendInterruptResponse(approved: boolean, presetId: string, model?: string): Promise<void> {
    const decisions = [{ type: approved ? 'approve' : 'reject' }]
    await this.sendInterruptResume({ decisions }, presetId, model)
  }

  async sendInterruptResume(
    resumeValue: any,
    presetId: string,
    model?: string,
    llmParams?: Record<string, any> | null,
  ): Promise<void> {
    if (!this._threadId) throw new Error('threadId not set')

    const body: Record<string, any> = {
      command: { resume: resumeValue },
      preset_id: presetId || 'chat',
      model: model || '',
    }
    if (llmParams && Object.keys(llmParams).length > 0) {
      body.llm_params = llmParams
    }

    await this._startStream(body)
  }

  async sendCancel(): Promise<void> {
    if (!this._threadId) return

    this._abortController?.abort()
    this._abortController = null
    this._streaming = false

    this._emitTerminal('cancelled', { type: 'cancelled' })

    try {
      const cancelUrl = appendTokenToUrl(`${this.baseUrl}/api/threads/${this._threadId}/runs/cancel`)
      await fetch(cancelUrl, {
        method: 'POST',
        headers: getSseAuthHeaders(),
        body: JSON.stringify({}),
      })
    } catch (e) {
      console.warn('[SSE] Cancel request failed:', e)
    }
  }

  async getState(): Promise<any> {
    if (!this._threadId) return { has_interrupts: false }
    const stateUrl = appendTokenToUrl(`${this.baseUrl}/api/threads/${this._threadId}/state`)
    const resp = await fetch(stateUrl, { headers: getSseAuthHeaders() })
    return resp.json()
  }

  on(event: string, handler: SseEventHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, [])
    }
    this.handlers.get(event)!.push(handler)
  }

  off(event: string, handler: SseEventHandler) {
    const handlers = this.handlers.get(event)
    if (handlers) {
      const idx = handlers.indexOf(handler)
      if (idx >= 0) handlers.splice(idx, 1)
    }
  }

  disconnect() {
    this._abortController?.abort()
    this._abortController = null
    this._streaming = false
    this._threadId = null
  }

  // --- Internal ---

  private async _startStream(body: Record<string, any>): Promise<void> {
    // 每次请求换一个 token：旧流的迟到收尾据此判断自己是否已被新流取代
    const token = {}
    this._streamToken = token
    this._terminalEmitted = false

    if (this._streaming) {
      console.warn('[SSE] Already streaming, aborting previous')
      this._abortController?.abort()
      if (this._threadId) {
        fetch(appendTokenToUrl(`${this.baseUrl}/api/threads/${this._threadId}/runs/cancel`), {
          method: 'POST',
          headers: getSseAuthHeaders(),
          body: JSON.stringify({}),
        }).catch(() => {})
      }
    }

    const controller = new AbortController()
    this._abortController = controller
    this._streaming = true

    const url = appendTokenToUrl(`${this.baseUrl}/api/threads/${this._threadId}/runs/stream`)

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: getSseAuthHeaders(),
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!response.ok) {
        if (response.status === 401) {
          window.dispatchEvent(new CustomEvent('auth:expired'))
          this._emitTerminal('error', { type: 'error', title: '认证已过期', detail: '请重新登录' })
          return
        }
        if (response.status === 409) {
          // 该会话已有一轮在跑：不是错误，交给上层同步"正在运行"状态
          let detail = '该会话正在运行中，请先停止或等待完成'
          try {
            const body = await response.json()
            if (body?.detail) detail = body.detail
          } catch {}
          this._emitTerminal('error', {
            type: 'error',
            title: '会话正在运行中',
            detail,
            error_code: 'run_in_progress',
          })
          return
        }
        const text = await response.text()
        this._emitTerminal('error', {
          type: 'error',
          title: `HTTP ${response.status}`,
          detail: text,
          error_code: 'HTTP_ERROR',
        })
        return
      }

      const receivedTerminal = await this._consumeStream(response)
      if (!receivedTerminal && this._abortController === controller) {
        this._emitTerminal('done', { type: 'done' })
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // 中断也必须收敛前端状态：disconnect() / 停止 / 被新流取代 都走这里。
        // 已被新流取代（token 变了）就不补发，交给新流自己收敛。
        if (this._streamToken === token) {
          this._emitTerminal('cancelled', { type: 'cancelled', reason: 'aborted' })
        }
        return
      }
      if (this._streamToken !== token) return
      this._emitTerminal('error', {
        type: 'error',
        title: '连接失败',
        detail: e.message || String(e),
        error_code: 'NETWORK_ERROR',
      })
    } finally {
      if (this._abortController === controller) {
        this._streaming = false
        this._abortController = null
      }
    }
  }

  private async _consumeStream(response: Response): Promise<boolean> {
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let receivedTerminal = false
    const terminalTypes = new Set(['done', 'error', 'cancelled'])

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const events = this._parseSSE(buffer)
        buffer = events.remaining

        for (const evt of events.parsed) {
          this.emit(evt.type, evt)
          if (terminalTypes.has(evt.type)) {
            receivedTerminal = true
            this._terminalEmitted = true
          }
        }
      }

      if (buffer.trim()) {
        const events = this._parseSSE(buffer + '\n\n')
        for (const evt of events.parsed) {
          this.emit(evt.type, evt)
          if (terminalTypes.has(evt.type)) {
            receivedTerminal = true
            this._terminalEmitted = true
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        throw e
      }
    }

    return receivedTerminal
  }

  private _parseSSE(buffer: string): { parsed: SseMessage[]; remaining: string } {
    const parsed: SseMessage[] = []
    const blocks = buffer.split('\n\n')

    // The last element might be incomplete (no trailing \n\n)
    const remaining = blocks.pop() || ''

    for (const block of blocks) {
      if (!block.trim()) continue

      // Skip heartbeat comments
      if (block.trim().startsWith(':')) continue

      let data = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('data: ')) {
          data += line.slice(6)
        } else if (line.startsWith('data:')) {
          data += line.slice(5)
        }
      }

      if (data) {
        try {
          const msg: SseMessage = JSON.parse(data)
          parsed.push(msg)
        } catch {
          console.warn('[SSE] Failed to parse event data:', data)
        }
      }
    }

    return { parsed, remaining }
  }

  private emit(event: string, msg: SseMessage) {
    const handlers = this.handlers.get(event) || []
    handlers.forEach(h => h(msg))
    const allHandlers = this.handlers.get('*') || []
    allHandlers.forEach(h => h(msg))
  }

  /**
   * 发终止事件（done / error / cancelled），同一路流只发一次。
   * 目的是保证任何中断路径（点停止、会话被释放 disconnect、连接异常）下，
   * 上层状态机都能收到唯一的终止信号并收敛，不会永远停在"流式中"。
   */
  private _emitTerminal(event: string, msg: SseMessage) {
    if (this._terminalEmitted) return
    this._terminalEmitted = true
    this.emit(event, msg)
  }
}
