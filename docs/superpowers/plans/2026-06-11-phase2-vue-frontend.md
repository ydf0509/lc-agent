# lc_agent Phase 2: Vue Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dark-themed, three-column Web UI that connects to the Phase 1 FastAPI backend via WebSocket, supporting streaming chat, tool/MCP/skill toggles, and agent management.

**Architecture:** Vue 3 SPA with Element Plus (dark mode), Pinia state management, WebSocket for real-time chat streaming. Frontend is built and bundled into the Python package as static files served by FastAPI.

**Tech Stack:** Vue 3 (Composition API), Vite, Element Plus, Pinia, Vue Router, markdown-it, highlight.js, WebSocket API

---

## File Structure

```
frontend/
├── package.json
├── vite.config.ts
├── index.html
├── tsconfig.json
├── env.d.ts
│
├── public/
│   └── favicon.ico
│
└── src/
    ├── main.ts                      # App entry, Element Plus, dark theme
    ├── App.vue                      # Root layout (three-column)
    ├── style.css                    # Global dark theme overrides
    │
    ├── api/
    │   ├── http.ts                  # Axios/fetch wrapper for REST
    │   └── websocket.ts            # WebSocket connection manager
    │
    ├── stores/
    │   ├── chat.ts                  # Chat messages, streaming state
    │   ├── agents.ts               # Agent presets CRUD
    │   ├── tools.ts                # Tools list + toggle state
    │   └── session.ts              # Session list + current session
    │
    ├── views/
    │   └── ChatView.vue            # Main chat view (center column)
    │
    ├── components/
    │   ├── layout/
    │   │   ├── AppHeader.vue       # Top bar: logo, agent name, model
    │   │   ├── LeftSidebar.vue     # Sessions + Agent list
    │   │   └── RightPanel.vue      # Models, Tools, MCP, Skills toggles
    │   │
    │   ├── chat/
    │   │   ├── ChatBubble.vue      # Single message bubble (user/ai)
    │   │   ├── ChatInput.vue       # Input textarea + send button
    │   │   ├── ToolCallCard.vue    # Tool call display card
    │   │   ├── ThinkingBlock.vue   # AI thinking/reasoning display
    │   │   └── InterruptDialog.vue # HITL approval dialog
    │   │
    │   ├── panels/
    │   │   ├── ModelSelector.vue   # Model switch dropdown
    │   │   ├── ToolGroupPanel.vue  # Tool groups with toggles
    │   │   ├── McpPanel.vue        # MCP servers with toggles
    │   │   └── SkillPanel.vue      # Skills with toggles
    │   │
    │   └── agents/
    │       ├── AgentList.vue       # Agent preset list
    │       └── AgentEditor.vue     # Create/edit agent dialog
    │
    └── utils/
        ├── markdown.ts             # Markdown rendering config
        └── theme.ts                # Dark theme constants
```

---

### Task 1: Vue Project Setup + Element Plus Dark Theme

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/env.d.ts`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/style.css`

- [ ] **Step 1: Initialize Vue project with Vite**

Run from `D:\codes\lc-agent`:

```bash
cd frontend
npm init -y
npm install vue@3 element-plus @element-plus/icons-vue vue-router@4 pinia @vueuse/core
npm install -D vite @vitejs/plugin-vue typescript vue-tsc unplugin-vue-components unplugin-auto-import
```

- [ ] **Step 2: Create vite.config.ts**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: '../lc_agent/web/dist',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 3: Create index.html**

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>lc_agent</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

- [ ] **Step 4: Create src/main.ts with dark theme**

```typescript
// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 5: Create src/style.css (dark theme base)**

```css
/* frontend/src/style.css */
:root {
  --lc-bg-primary: #0d1117;
  --lc-bg-secondary: #161b22;
  --lc-bg-tertiary: #21262d;
  --lc-border: #30363d;
  --lc-text-primary: #e6edf3;
  --lc-text-secondary: #8b949e;
  --lc-accent: #58a6ff;
  --lc-accent-hover: #79c0ff;
  --lc-success: #3fb950;
  --lc-warning: #d29922;
  --lc-danger: #f85149;
}

html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  background: var(--lc-bg-primary);
  color: var(--lc-text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

* {
  box-sizing: border-box;
}

::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: var(--lc-bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--lc-border);
  border-radius: 3px;
}
```

- [ ] **Step 6: Create src/App.vue (three-column layout skeleton)**

```vue
<!-- frontend/src/App.vue -->
<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-left">
        <span class="logo">⚡ lc_agent</span>
      </div>
      <div class="header-center">
        <span class="current-agent">Default Agent</span>
        <el-tag size="small" type="info">deepseek-chat</el-tag>
      </div>
      <div class="header-right">
        <el-tag size="small" effect="dark">Connected</el-tag>
      </div>
    </header>

    <div class="app-body">
      <aside class="left-sidebar">
        <div class="sidebar-section">
          <h4>会话</h4>
          <el-button type="primary" size="small" style="width:100%">+ 新对话</el-button>
        </div>
      </aside>

      <main class="chat-main">
        <div class="chat-messages">
          <p style="text-align:center; color: var(--lc-text-secondary)">
            开始新的对话...
          </p>
        </div>
        <div class="chat-input-area">
          <el-input
            type="textarea"
            placeholder="输入消息..."
            :autosize="{ minRows: 2, maxRows: 6 }"
          />
          <el-button type="primary" class="send-btn">发送</el-button>
        </div>
      </main>

      <aside class="right-panel">
        <div class="panel-section">
          <h4>模型</h4>
          <el-tag>deepseek-chat</el-tag>
        </div>
        <div class="panel-section">
          <h4>工具</h4>
          <p class="empty-hint">暂无工具</p>
        </div>
        <div class="panel-section">
          <h4>MCP</h4>
          <p class="empty-hint">暂无 MCP 服务器</p>
        </div>
        <div class="panel-section">
          <h4>Skills</h4>
          <p class="empty-hint">暂无 Skills</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--lc-bg-secondary);
  border-bottom: 1px solid var(--lc-border);
  height: 48px;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--lc-accent);
}

.current-agent {
  margin-right: 8px;
  font-weight: 500;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.left-sidebar {
  width: 240px;
  background: var(--lc-bg-secondary);
  border-right: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--lc-bg-primary);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--lc-border);
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input-area .el-textarea {
  flex: 1;
}

.send-btn {
  height: 40px;
}

.right-panel {
  width: 280px;
  background: var(--lc-bg-secondary);
  border-left: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 16px;
}

.panel-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
}

.empty-hint {
  font-size: 12px;
  color: var(--lc-text-secondary);
  margin: 4px 0;
}
</style>
```

- [ ] **Step 7: Create tsconfig.json and env.d.ts**

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "env.d.ts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

```typescript
// frontend/env.d.ts
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 8: Verify dev server starts**

Run: `cd frontend && npm run dev`
Expected: Vite dev server starts at http://localhost:5173, page renders dark theme with three-column layout

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: Vue frontend setup with Element Plus dark theme and three-column layout"
```

---

### Task 2: WebSocket Connection Manager + Chat Store

**Files:**
- Create: `frontend/src/api/websocket.ts`
- Create: `frontend/src/api/http.ts`
- Create: `frontend/src/stores/chat.ts`

- [ ] **Step 1: Create src/api/websocket.ts**

```typescript
// frontend/src/api/websocket.ts
export interface WsMessage {
  type: string
  content?: string
  thread_id?: string
  name?: string
  result?: string
  message?: string
  run_id?: string
  action_requests?: any[]
  review_configs?: any[]
}

export type WsEventHandler = (msg: WsMessage) => void

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private handlers: Map<string, WsEventHandler[]> = new Map()
  private reconnectTimer: number | null = null
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

  sendMessage(content: string) {
    this.send({ type: 'message', content })
  }

  sendInterruptResponse(decision: object) {
    this.send({ type: 'interrupt_response', decision })
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
```

- [ ] **Step 2: Create src/api/http.ts**

```typescript
// frontend/src/api/http.ts
const BASE_URL = '/api'

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }
  return response.json()
}

export const api = {
  health: () => fetchApi<{ status: string; version: string }>('/health'),
  getTools: () => fetchApi<any[]>('/tools'),
  getModels: () => fetchApi<any[]>('/models'),
  getAgents: () => fetchApi<any[]>('/agents'),
  getSessions: () => fetchApi<any[]>('/sessions'),
}
```

- [ ] **Step 3: Create src/stores/chat.ts (Pinia store)**

```typescript
// frontend/src/stores/chat.ts
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

    const tid = await ws.value.connect()
    threadId.value = tid
    isConnected.value = true
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
```

- [ ] **Step 4: Verify no TypeScript errors**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: No errors (or only minor type issues that can be fixed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/ frontend/src/stores/chat.ts
git commit -m "feat: WebSocket manager and chat Pinia store with streaming support"
```

---

### Task 3: Chat Components (Bubbles + Input + Tool Cards)

**Files:**
- Create: `frontend/src/components/chat/ChatBubble.vue`
- Create: `frontend/src/components/chat/ChatInput.vue`
- Create: `frontend/src/components/chat/ToolCallCard.vue`
- Create: `frontend/src/components/chat/ThinkingBlock.vue`
- Create: `frontend/src/components/chat/InterruptDialog.vue`
- Create: `frontend/src/views/ChatView.vue`
- Create: `frontend/src/utils/markdown.ts`

- [ ] **Step 1: Create markdown utility**

```typescript
// frontend/src/utils/markdown.ts
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight(str: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

export function renderMarkdown(text: string): string {
  return md.render(text)
}
```

- [ ] **Step 2: Create ChatBubble.vue**

```vue
<!-- frontend/src/components/chat/ChatBubble.vue -->
<template>
  <div class="chat-bubble" :class="[message.role, { streaming: message.isStreaming }]">
    <div class="bubble-avatar">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="bubble-content">
      <div v-if="message.role === 'assistant'" class="markdown-body" v-html="renderedContent" />
      <div v-else class="plain-text">{{ message.content }}</div>

      <div v-if="message.toolCalls?.length" class="tool-calls">
        <ToolCallCard
          v-for="(tc, idx) in message.toolCalls"
          :key="idx"
          :tool-call="tc"
        />
      </div>

      <span v-if="message.isStreaming" class="streaming-cursor">▊</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import ToolCallCard from './ToolCallCard.vue'
import type { ChatMessage } from '@/stores/chat'

const props = defineProps<{ message: ChatMessage }>()

const renderedContent = computed(() => renderMarkdown(props.message.content))
</script>

<style scoped>
.chat-bubble {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.chat-bubble.user {
  background: var(--lc-bg-tertiary);
}

.chat-bubble.assistant {
  background: transparent;
}

.bubble-avatar {
  font-size: 20px;
  flex-shrink: 0;
}

.bubble-content {
  flex: 1;
  overflow-wrap: break-word;
  line-height: 1.6;
}

.streaming-cursor {
  animation: blink 1s infinite;
  color: var(--lc-accent);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.tool-calls {
  margin-top: 8px;
}
</style>
```

- [ ] **Step 3: Create ToolCallCard.vue**

```vue
<!-- frontend/src/components/chat/ToolCallCard.vue -->
<template>
  <div class="tool-call-card" :class="toolCall.status">
    <div class="tool-header">
      <el-icon v-if="toolCall.status === 'running'" class="spinning">
        <Loading />
      </el-icon>
      <el-icon v-else-if="toolCall.status === 'done'" style="color: var(--lc-success)">
        <Check />
      </el-icon>
      <span class="tool-name">{{ toolCall.name }}</span>
      <el-tag size="small" :type="statusType">{{ statusLabel }}</el-tag>
    </div>
    <div v-if="toolCall.result" class="tool-result">
      <pre>{{ toolCall.result }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading, Check } from '@element-plus/icons-vue'
import type { ToolCall } from '@/stores/chat'

const props = defineProps<{ toolCall: ToolCall }>()

const statusType = computed(() => {
  switch (props.toolCall.status) {
    case 'running': return 'warning'
    case 'done': return 'success'
    case 'error': return 'danger'
    default: return 'info'
  }
})

const statusLabel = computed(() => {
  switch (props.toolCall.status) {
    case 'running': return '执行中'
    case 'done': return '完成'
    case 'error': return '错误'
    default: return '等待'
  }
})
</script>

<style scoped>
.tool-call-card {
  border: 1px solid var(--lc-border);
  border-radius: 6px;
  padding: 8px 12px;
  margin: 4px 0;
  background: var(--lc-bg-secondary);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-name {
  font-family: monospace;
  font-size: 13px;
  color: var(--lc-accent);
}

.tool-result {
  margin-top: 8px;
  padding: 8px;
  background: var(--lc-bg-primary);
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.tool-result pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
```

- [ ] **Step 4: Create ChatInput.vue**

```vue
<!-- frontend/src/components/chat/ChatInput.vue -->
<template>
  <div class="chat-input-wrapper">
    <el-input
      v-model="inputText"
      type="textarea"
      :placeholder="isStreaming ? 'AI 正在回复...' : '输入消息... (Enter发送, Shift+Enter换行)'"
      :autosize="{ minRows: 2, maxRows: 8 }"
      :disabled="isStreaming"
      @keydown="handleKeydown"
    />
    <el-button
      type="primary"
      :disabled="!inputText.trim() || isStreaming"
      :loading="isStreaming"
      @click="send"
    >
      发送
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ isStreaming: boolean }>()
const emit = defineEmits<{ send: [content: string] }>()

const inputText = ref('')

function send() {
  if (!inputText.value.trim() || props.isStreaming) return
  emit('send', inputText.value)
  inputText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<style scoped>
.chat-input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 12px 16px;
  border-top: 1px solid var(--lc-border);
  background: var(--lc-bg-secondary);
}

.chat-input-wrapper .el-textarea {
  flex: 1;
}
</style>
```

- [ ] **Step 5: Create InterruptDialog.vue**

```vue
<!-- frontend/src/components/chat/InterruptDialog.vue -->
<template>
  <el-dialog
    v-model="visible"
    title="⚠️ 工具需要审批"
    width="500px"
    :close-on-click-modal="false"
  >
    <div v-for="(action, idx) in interrupt.actionRequests" :key="idx" class="action-item">
      <p><strong>工具:</strong> {{ action.name }}</p>
      <pre class="action-args">{{ JSON.stringify(action.arguments, null, 2) }}</pre>
    </div>

    <template #footer>
      <el-button @click="reject">拒绝</el-button>
      <el-button type="primary" @click="approve">批准执行</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InterruptInfo } from '@/stores/chat'

const props = defineProps<{ interrupt: InterruptInfo | null }>()
const emit = defineEmits<{ decide: [decision: object] }>()

const visible = computed(() => props.interrupt !== null)

function approve() {
  emit('decide', { type: 'approve' })
}

function reject() {
  emit('decide', { type: 'reject', message: '用户拒绝了此操作' })
}
</script>

<style scoped>
.action-item {
  margin-bottom: 12px;
}

.action-args {
  background: var(--lc-bg-primary);
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}
</style>
```

- [ ] **Step 6: Create ChatView.vue (wires everything together)**

```vue
<!-- frontend/src/views/ChatView.vue -->
<template>
  <div class="chat-view">
    <div class="messages-area" ref="messagesRef">
      <div v-if="!messages.length" class="empty-state">
        <p>⚡ 开始新的对话</p>
      </div>
      <ChatBubble v-for="msg in messages" :key="msg.id" :message="msg" />
    </div>

    <ChatInput :is-streaming="isStreaming" @send="handleSend" />

    <InterruptDialog
      :interrupt="interrupt"
      @decide="handleInterruptDecide"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import InterruptDialog from '@/components/chat/InterruptDialog.vue'

const chatStore = useChatStore()
const { messages, isStreaming, interrupt } = storeToRefs(chatStore)
const messagesRef = ref<HTMLElement>()

onMounted(() => {
  chatStore.connect()
})

function handleSend(content: string) {
  chatStore.sendMessage(content)
}

function handleInterruptDecide(decision: object) {
  chatStore.respondToInterrupt(decision)
}

watch(messages, () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}, { deep: true })
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--lc-text-secondary);
  font-size: 18px;
}
</style>
```

- [ ] **Step 7: Install markdown dependencies**

Run: `cd frontend && npm install markdown-it highlight.js && npm install -D @types/markdown-it`

- [ ] **Step 8: Verify build succeeds**

Run: `cd frontend && npx vite build`
Expected: Build succeeds, output to `../lc_agent/web/dist/`

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/ frontend/src/views/ frontend/src/utils/
git commit -m "feat: chat components with streaming, tool cards, and interrupt dialog"
```

---

### Task 4: Right Panel (Tool/MCP/Skill Toggles)

**Files:**
- Create: `frontend/src/components/panels/ToolGroupPanel.vue`
- Create: `frontend/src/components/panels/ModelSelector.vue`
- Create: `frontend/src/components/layout/RightPanel.vue`
- Create: `frontend/src/stores/tools.ts`

- [ ] **Step 1: Create tools store**

```typescript
// frontend/src/stores/tools.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToolGroup {
  name: string
  tools: { name: string; description: string }[]
  enabled: boolean
}

export const useToolsStore = defineStore('tools', () => {
  const groups = ref<ToolGroup[]>([])
  const models = ref<{ id: string; provider: string; context_limit: number }[]>([])
  const currentModel = ref('')

  function toggleGroup(groupName: string) {
    const group = groups.value.find(g => g.name === groupName)
    if (group) group.enabled = !group.enabled
  }

  function setModel(modelId: string) {
    currentModel.value = modelId
  }

  return { groups, models, currentModel, toggleGroup, setModel }
})
```

- [ ] **Step 2: Create ToolGroupPanel.vue**

```vue
<!-- frontend/src/components/panels/ToolGroupPanel.vue -->
<template>
  <div class="tool-group-panel">
    <div v-for="group in groups" :key="group.name" class="group-item">
      <div class="group-header">
        <span class="group-name">{{ group.name }}</span>
        <el-switch
          v-model="group.enabled"
          size="small"
          @change="$emit('toggle', group.name)"
        />
      </div>
      <div class="group-tools">
        <el-tag
          v-for="tool in group.tools"
          :key="tool.name"
          size="small"
          :type="group.enabled ? '' : 'info'"
          :effect="group.enabled ? 'dark' : 'plain'"
        >
          {{ tool.name.split('__').pop() }}
        </el-tag>
      </div>
    </div>
    <p v-if="!groups.length" class="empty">暂无工具</p>
  </div>
</template>

<script setup lang="ts">
import type { ToolGroup } from '@/stores/tools'

defineProps<{ groups: ToolGroup[] }>()
defineEmits<{ toggle: [groupName: string] }>()
</script>

<style scoped>
.group-item {
  margin-bottom: 12px;
  padding: 8px;
  background: var(--lc-bg-tertiary);
  border-radius: 6px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.group-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--lc-text-primary);
}

.group-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.empty {
  color: var(--lc-text-secondary);
  font-size: 12px;
}
</style>
```

- [ ] **Step 3: Create ModelSelector.vue**

```vue
<!-- frontend/src/components/panels/ModelSelector.vue -->
<template>
  <div class="model-selector">
    <el-select
      :model-value="currentModel"
      placeholder="选择模型"
      size="small"
      style="width: 100%"
      @change="$emit('change', $event)"
    >
      <el-option
        v-for="model in models"
        :key="model.id"
        :label="model.id"
        :value="model.id"
      >
        <span>{{ model.id }}</span>
        <span style="float:right; color:var(--lc-text-secondary); font-size:11px">
          {{ Math.round(model.context_limit / 1000) }}K
        </span>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  models: { id: string; context_limit: number }[]
  currentModel: string
}>()
defineEmits<{ change: [modelId: string] }>()
</script>
```

- [ ] **Step 4: Update RightPanel in App.vue or create component**

Create `frontend/src/components/layout/RightPanel.vue`:

```vue
<!-- frontend/src/components/layout/RightPanel.vue -->
<template>
  <aside class="right-panel">
    <div class="panel-section">
      <h4>模型</h4>
      <ModelSelector
        :models="toolsStore.models"
        :current-model="toolsStore.currentModel"
        @change="toolsStore.setModel"
      />
    </div>

    <div class="panel-section">
      <h4>工具组</h4>
      <ToolGroupPanel
        :groups="toolsStore.groups"
        @toggle="toolsStore.toggleGroup"
      />
    </div>

    <div class="panel-section">
      <h4>MCP 服务器</h4>
      <p class="empty-hint">暂无 MCP 服务器</p>
    </div>

    <div class="panel-section">
      <h4>Skills</h4>
      <p class="empty-hint">暂无 Skills</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useToolsStore } from '@/stores/tools'
import ModelSelector from '@/components/panels/ModelSelector.vue'
import ToolGroupPanel from '@/components/panels/ToolGroupPanel.vue'

const toolsStore = useToolsStore()
</script>

<style scoped>
.right-panel {
  width: 280px;
  background: var(--lc-bg-secondary);
  border-left: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 16px;
}

.panel-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.empty-hint {
  font-size: 12px;
  color: var(--lc-text-secondary);
}
</style>
```

- [ ] **Step 5: Verify dev server renders correctly**

Run: `cd frontend && npm run dev`
Expected: Three-column layout with working toggle switches in right panel

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/panels/ frontend/src/components/layout/ frontend/src/stores/tools.ts
git commit -m "feat: right panel with model selector and tool group toggles"
```

---

### Task 5: Integrate App.vue + Wire ChatView + Final Build

**Files:**
- Modify: `frontend/src/App.vue` — use real components
- Create: `frontend/src/components/layout/LeftSidebar.vue`
- Create: `frontend/src/components/layout/AppHeader.vue`

- [ ] **Step 1: Create LeftSidebar.vue**

```vue
<!-- frontend/src/components/layout/LeftSidebar.vue -->
<template>
  <aside class="left-sidebar">
    <div class="sidebar-section">
      <el-button type="primary" size="small" style="width:100%" @click="$emit('newChat')">
        + 新对话
      </el-button>
    </div>
    <div class="sidebar-section">
      <h4>会话历史</h4>
      <div class="session-list">
        <div class="session-item active">
          <span>当前对话</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
defineEmits<{ newChat: [] }>()
</script>

<style scoped>
.left-sidebar {
  width: 240px;
  background: var(--lc-bg-secondary);
  border-right: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 16px;
}

.sidebar-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
}

.session-item {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--lc-text-primary);
}

.session-item:hover {
  background: var(--lc-bg-tertiary);
}

.session-item.active {
  background: var(--lc-bg-tertiary);
  border-left: 2px solid var(--lc-accent);
}
</style>
```

- [ ] **Step 2: Create AppHeader.vue**

```vue
<!-- frontend/src/components/layout/AppHeader.vue -->
<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">⚡ lc_agent</span>
    </div>
    <div class="header-center">
      <span class="current-agent">{{ agentName }}</span>
      <el-tag size="small" type="info">{{ modelName }}</el-tag>
    </div>
    <div class="header-right">
      <el-tag size="small" :type="connected ? 'success' : 'danger'" effect="dark">
        {{ connected ? '已连接' : '未连接' }}
      </el-tag>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  agentName: string
  modelName: string
  connected: boolean
}>()
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--lc-bg-secondary);
  border-bottom: 1px solid var(--lc-border);
  height: 48px;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--lc-accent);
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.current-agent {
  font-weight: 500;
}
</style>
```

- [ ] **Step 3: Update App.vue to use real components**

Update `frontend/src/App.vue` to import and use `AppHeader`, `LeftSidebar`, `ChatView`, and `RightPanel`.

- [ ] **Step 4: Build frontend**

Run: `cd frontend && npx vite build`
Expected: Build succeeds, files in `lc_agent/web/dist/`

- [ ] **Step 5: Add static file serving to FastAPI**

Modify `lc_agent/server/app.py` to serve the built frontend:

```python
# Add to create_app() in lc_agent/server/app.py
from pathlib import Path
from fastapi.staticfiles import StaticFiles

web_dist = Path(__file__).parent.parent / "web" / "dist"
if web_dist.exists():
    app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="frontend")
```

- [ ] **Step 6: Verify full stack works**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m lc_agent --port 8000`
Expected: Server starts, http://localhost:8000 shows the Vue app

- [ ] **Step 7: Run backend tests (ensure nothing broke)**

Run: `D:\ProgramData\miniconda3\envs\py312\python.exe -m pytest tests/ -v`
Expected: All 41 tests still pass

- [ ] **Step 8: Commit**

```bash
git add frontend/ lc_agent/server/app.py lc_agent/web/
git commit -m "feat: complete Vue frontend with chat UI, panels, and static serving"
```

---

## Summary

After completing all 5 tasks:
- Full dark-themed Vue 3 frontend with three-column layout
- WebSocket streaming chat with real-time token display
- Tool call cards with status indicators
- Human-in-the-loop interrupt dialog (approve/reject)
- Right panel with model selector and tool group toggles
- Frontend builds into `lc_agent/web/dist/` and is served by FastAPI
- User visits `http://localhost:8000` to see the complete UI

**Next:** Phase 3 will add the full backend CRUD APIs for agents/tools/MCP/skills, connect them to the frontend stores, and add the Agent Editor dialog for creating agents from the UI.
