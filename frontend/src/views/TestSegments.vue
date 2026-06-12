<template>
  <div style="padding:20px; background:#0d1117; min-height:100vh; color:#c9d1d9;">
    <h2>Segments Rendering Test</h2>
    <button @click="simulateStream" style="padding:8px 16px; margin:10px 0;">
      Simulate Stream (think → tool → answer)
    </button>
    <button @click="resetMsg" style="padding:8px 16px; margin:10px;">Reset</button>
    <div style="margin:10px 0; font-size:12px; color:#8b949e;">
      Segments: {{ msg.segments?.length || 0 }} | Content length: {{ msg.content.length }}
    </div>
    <ChatBubble :message="msg" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import type { ChatMessage, ToolCall } from '@/stores/chat'

const msg = ref<ChatMessage>({
  id: 'test-1',
  role: 'assistant',
  content: '',
  timestamp: Date.now(),
  isStreaming: false,
  usage: { rounds: [], toolCallCount: 0 },
})

function resetMsg() {
  msg.value = {
    id: 'test-' + Date.now(),
    role: 'assistant',
    content: '',
    timestamp: Date.now(),
    isStreaming: false,
    usage: { rounds: [], toolCallCount: 0 },
  }
}

async function simulateStream() {
  resetMsg()
  msg.value.isStreaming = true
  
  const addToken = (text: string) => {
    msg.value.content += text
    const segs = msg.value.segments!
    const last = segs[segs.length - 1]
    if (last && last.type === 'text') {
      last.text = (last.text || '') + text
    } else {
      segs.push({ type: 'text', text })
    }
  }
  
  const addTool = (name: string) => {
    const tc: ToolCall = { name, args: { query: 'test' }, status: 'running' }
    if (!msg.value.toolCalls) msg.value.toolCalls = []
    const tcIdx = msg.value.toolCalls.length
    msg.value.toolCalls.push(tc)
    msg.value.content += `\n<!--TOOL:${tcIdx}-->\n`
    msg.value.usage!.toolCallCount++
  }
  
  const finishTool = (name: string) => {
    const tc = msg.value.toolCalls?.find(t => t.name === name && t.status === 'running')
    if (tc) {
      tc.status = 'done'
      tc.result = 'Some result data...'
      tc.duration = 1234
    }
  }
  
  const delay = (ms: number) => new Promise(r => setTimeout(r, ms))
  
  // Phase 1: thinking text
  for (const char of '我来查询相关文档...\n') {
    addToken(char)
    await delay(30)
  }
  
  // Phase 2: tool call
  await delay(200)
  addTool('mcp__docs__search')
  await delay(1000)
  finishTool('mcp__docs__search')
  
  // Phase 3: more thinking
  await delay(200)
  for (const char of '继续查找更多资料...\n') {
    addToken(char)
    await delay(30)
  }
  
  // Phase 4: another tool
  await delay(200)
  addTool('mcp__reference__get_symbol')
  await delay(800)
  finishTool('mcp__reference__get_symbol')
  
  // Phase 5: final answer
  await delay(200)
  for (const char of '## 最终答案\n\n这是一个总结性回答。') {
    addToken(char)
    await delay(20)
  }
  
  msg.value.isStreaming = false
  msg.value.usage!.totalDuration = 5000
}
</script>
