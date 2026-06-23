export interface WsMessage {
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
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  cache_read_tokens?: number
  reasoning_tokens?: number
  usage?: any[]
  http_traces?: any[]
}

export type WsEventHandler = (msg: WsMessage) => void

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private handlers: Map<string, WsEventHandler[]> = new Map()
  private _threadId: string | null = null

  constructor(baseUrl: string = '') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = baseUrl || window.location.host
    this.url = `${protocol}//${host}/ws/chat`
  }

  get threadId() { return this._threadId }
  get connected() { return this.ws?.readyState === WebSocket.OPEN }

  connect(threadId?: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const url = threadId ? `${this.url}/${threadId}` : this.url
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('[WS] Connected')
      }

      this.ws.onmessage = (event) => {
        const msg: WsMessage = JSON.parse(event.data)
        if (msg.type === 'connected') {
          this._threadId = msg.thread_id || null
          resolve(this._threadId!)
        }
        this.emit(msg.type, msg)
      }

      this.ws.onerror = (err) => {
        console.error('[WS] Error:', err)
        reject(err)
      }

      this.ws.onclose = () => {
        console.log('[WS] Disconnected')
        this.emit('disconnected', { type: 'disconnected' })
      }
    })
  }

  send(data: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  sendMessage(content: string, presetId?: string, model?: string) {
    this.send({ type: 'message', content, preset_id: presetId, model })
  }

  sendInterruptResponse(approved: boolean, presetId: string) {
    this.send({
      type: 'interrupt_response',
      approved,
      preset_id: presetId,
    })
  }

  sendCancel() {
    this.send({ type: 'cancel' })
  }

  on(event: string, handler: WsEventHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, [])
    }
    this.handlers.get(event)!.push(handler)
  }

  off(event: string, handler: WsEventHandler) {
    const handlers = this.handlers.get(event)
    if (handlers) {
      const idx = handlers.indexOf(handler)
      if (idx >= 0) handlers.splice(idx, 1)
    }
  }

  private emit(event: string, msg: WsMessage) {
    const handlers = this.handlers.get(event) || []
    handlers.forEach(h => h(msg))
    const allHandlers = this.handlers.get('*') || []
    allHandlers.forEach(h => h(msg))
  }

  disconnect() {
    this.ws?.close()
    this.ws = null
    this._threadId = null
  }
}
