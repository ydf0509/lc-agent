/**
 * SSE-based chat client. Drop-in replacement for ChatWebSocket.
 * Uses fetch + ReadableStream to consume server-sent events.
 */

export interface SseMessage {
  type: string
  content?: string
  thread_id?: string
  title?: string
  name?: string
  result?: string
  message?: string
  run_id?: string
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
  usage?: any[]
  http_traces?: any[]
  is_resume?: boolean
  // error fields
  error_code?: string
  detail?: string
  suggestions?: string[]
  tech_detail?: string
  // sub-agent fields
  parent_tool_run_id?: string
  sub_agent_id?: string
  sub_agent_name?: string
  task_description?: string
  summary?: string
  final_result?: string
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
    content: string,
    presetId?: string,
    model?: string,
    options?: { replaceFromMessageId?: string; history?: any[]; llmParams?: Record<string, any> | null },
  ): Promise<void> {
    if (!this._threadId) throw new Error('threadId not set')

    const body: Record<string, any> = {
      input: content,
      preset_id: presetId || '__chat__',
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
      preset_id: presetId || '__chat__',
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

    this.emit('cancelled', { type: 'cancelled' })

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
          this.emit('error', { type: 'error', title: '认证已过期', detail: '请重新登录' })
          return
        }
        const text = await response.text()
        this.emit('error', {
          type: 'error',
          title: `HTTP ${response.status}`,
          detail: text,
          error_code: 'HTTP_ERROR',
        })
        return
      }

      const receivedTerminal = await this._consumeStream(response)
      if (!receivedTerminal && this._abortController === controller) {
        this.emit('done', { type: 'done' })
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        return
      }
      this.emit('error', {
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
          if (terminalTypes.has(evt.type)) receivedTerminal = true
        }
      }

      if (buffer.trim()) {
        const events = this._parseSSE(buffer + '\n\n')
        for (const evt of events.parsed) {
          this.emit(evt.type, evt)
          if (terminalTypes.has(evt.type)) receivedTerminal = true
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
}
