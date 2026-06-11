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
