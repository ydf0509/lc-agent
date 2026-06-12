<template>
  <div class="chat-view">
    <div class="messages-container">
      <div class="messages-area" ref="messagesRef">
        <div v-if="!messages.length" class="empty-state">
          <div class="empty-icon">⚡</div>
          <p>开始新的对话</p>
        </div>
        <TransitionGroup name="msg" tag="div">
          <ChatBubble
            v-for="(msg, idx) in messages"
            :key="msg.id"
            :ref="el => setBubbleRef(idx, el)"
            :message="msg"
            :show-edit="msg.role === 'user' && idx === lastUserMsgIndex && !isStreaming"
            @edit="handleEdit(idx)"
          />
        </TransitionGroup>
      </div>

      <div v-if="userMessages.length > 1" class="msg-nav">
        <div class="msg-nav-label">Q</div>
        <button
          v-for="(um, i) in userMessages"
          :key="um.idx"
          class="msg-nav-dot"
          :class="{ active: um.idx === nearestUserMsgIdx }"
          :title="um.preview"
          @click="scrollToMessage(um.idx)"
        >
          <span class="dot-num">{{ i + 1 }}</span>
        </button>
      </div>
    </div>

    <ChatInput
      :is-streaming="isStreaming"
      :edit-content="editContent"
      @send="handleSend"
      @stop="handleStop"
      @cancel-edit="handleCancelEdit"
    />

    <InterruptDialog
      :interrupt="interrupt"
      @decide="handleInterruptDecide"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import InterruptDialog from '@/components/chat/InterruptDialog.vue'

const chatStore = useChatStore()
const agentsStore = useAgentsStore()
const { messages, isStreaming, interrupt } = storeToRefs(chatStore)
const messagesRef = ref<HTMLElement>()
const userScrolledUp = ref(false)
const editContent = ref('')
const editingIndex = ref(-1)
const bubbleRefs = ref<Record<number, any>>({})
const nearestUserMsgIdx = ref(-1)

const lastUserMsgIndex = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') return i
  }
  return -1
})

const userMessages = computed(() => {
  return messages.value
    .map((msg, idx) => ({ msg, idx }))
    .filter(item => item.msg.role === 'user')
    .map(item => ({
      idx: item.idx,
      preview: item.msg.content.slice(0, 20) + (item.msg.content.length > 20 ? '...' : ''),
    }))
})

function setBubbleRef(idx: number, el: any) {
  if (el) {
    bubbleRefs.value[idx] = el
  } else {
    delete bubbleRefs.value[idx]
  }
}

function scrollToMessage(msgIdx: number) {
  const bubble = bubbleRefs.value[msgIdx]
  if (!bubble?.$el) return
  const el = bubble.$el as HTMLElement
  el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  userScrolledUp.value = true
}

onMounted(() => {
  chatStore.connect()
  messagesRef.value?.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  messagesRef.value?.removeEventListener('scroll', handleScroll)
})

function handleScroll() {
  if (!messagesRef.value) return
  const el = messagesRef.value
  const threshold = 80
  userScrolledUp.value = el.scrollHeight - el.scrollTop - el.clientHeight > threshold
  updateNearestUserMsg()
}

function updateNearestUserMsg() {
  if (!messagesRef.value) return
  const containerTop = messagesRef.value.scrollTop
  let closest = -1
  let closestDist = Infinity

  for (const um of userMessages.value) {
    const bubble = bubbleRefs.value[um.idx]
    if (!bubble?.$el) continue
    const el = bubble.$el as HTMLElement
    const dist = Math.abs(el.offsetTop - containerTop)
    if (dist < closestDist) {
      closestDist = dist
      closest = um.idx
    }
  }
  nearestUserMsgIdx.value = closest
}

function handleSend(content: string) {
  if (editingIndex.value >= 0) {
    messages.value.splice(editingIndex.value)
    editingIndex.value = -1
  }
  editContent.value = ''
  chatStore.sendMessage(content, agentsStore.currentAgentId)
  userScrolledUp.value = false
  nextTick(() => scrollToBottom())
}

function handleStop() {
  chatStore.stopGeneration()
}

function handleEdit(msgIndex: number) {
  const msg = messages.value[msgIndex]
  if (!msg) return
  editContent.value = msg.content
  editingIndex.value = msgIndex
}

function handleCancelEdit() {
  editContent.value = ''
  editingIndex.value = -1
}

function handleInterruptDecide(decision: { type: string }) {
  chatStore.respondToInterrupt(decision.type === 'approve', agentsStore.currentAgentId)
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

watch(messages, () => {
  if (!userScrolledUp.value) {
    nextTick(() => scrollToBottom())
  }
}, { deep: true })
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.messages-area {
  height: 100%;
  overflow-y: auto;
  padding: 20px 24px;
}

.msg-nav {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px 4px;
  background: rgba(22, 27, 34, 0.85);
  border: 1px solid #30363d;
  border-radius: 12px;
  backdrop-filter: blur(6px);
  z-index: 10;
}

.msg-nav-label {
  font-size: 9px;
  font-weight: 700;
  color: #58a6ff;
  margin-bottom: 2px;
  user-select: none;
}

.msg-nav-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid #30363d;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  padding: 0;
}

.msg-nav-dot:hover {
  border-color: #58a6ff;
  background: rgba(88, 166, 255, 0.1);
}

.msg-nav-dot.active {
  border-color: #58a6ff;
  background: rgba(88, 166, 255, 0.2);
}

.dot-num {
  font-size: 9px;
  font-weight: 600;
  color: #8b949e;
  line-height: 1;
}

.msg-nav-dot:hover .dot-num,
.msg-nav-dot.active .dot-num {
  color: #58a6ff;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--lc-text-secondary);
  gap: 8px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.4;
}

.empty-state p {
  font-size: 16px;
  opacity: 0.6;
}

.msg-enter-active {
  animation: float-in var(--lc-transition-slow) ease both;
}
</style>
