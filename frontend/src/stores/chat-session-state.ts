import { ref } from 'vue'
import type { Ref } from 'vue'
import type { ChatSseClient } from '@/api/sse-client'
import type { ChatMessage, InterruptInfo, ErrorInfo, TodoItem } from './chat'

export interface SessionState {
  // Message data
  messages: Ref<ChatMessage[]>
  totalMessageCount: Ref<number>
  hasOlderMessages: Ref<boolean>
  loadingOlder: Ref<boolean>
  isHistoryLoading: Ref<boolean>

  // Streaming state
  isStreaming: Ref<boolean>
  /** 服务端是否仍在该会话上运行：本地没有流时（刷新过页面）靠轮询 /run-status 得知 */
  serverRunning: Ref<boolean>
  /** 正在请求停止（防止重复点击把状态反复改写） */
  cancelling: Ref<boolean>
  inThinking: boolean       // mutable flag, intentionally not Ref
  streamStartTime: number   // mutable, not Ref
  currentRoundStart: number // mutable, not Ref
  /** 当前轮次首个正文/reasoning token 到达时间（前端估算 TPS），0 表示本轮还没收到 token */
  currentRoundFirstTokenAt: number // mutable, not Ref
  /** 子 Agent 各 run 的首个 token 时间，key 为 tool_call_id（与 llm_usage 的 sub_session_id 对应） */
  subagentFirstTokenAt: Map<string, number> // mutable, not Ref
  /** 本轮对话轮次号（后端 conversation_round 事件回填）：给直播消息打戳，前端不再自己数轮次 */
  currentRoundNumber: number // mutable, not Ref
  todos: Ref<TodoItem[]>
  interrupt: Ref<InterruptInfo | null>
  errorMessage: Ref<ErrorInfo | null>

  // SSE client (null until connect is called)
  client: ChatSseClient | null
}

export function createSessionState(): SessionState {
  return {
    messages: ref([]),
    totalMessageCount: ref(0),
    hasOlderMessages: ref(false),
    loadingOlder: ref(false),
    isHistoryLoading: ref(false),
    isStreaming: ref(false),
    serverRunning: ref(false),
    cancelling: ref(false),
    inThinking: false,
    streamStartTime: 0,
    currentRoundStart: 0,
    currentRoundFirstTokenAt: 0,
    subagentFirstTokenAt: new Map(),
    currentRoundNumber: 0,
    todos: ref([]),
    interrupt: ref(null),
    errorMessage: ref(null),
    client: null,
  }
}
