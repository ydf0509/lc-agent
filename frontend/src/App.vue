<template>
  <div class="app-container">
    <AppHeader
      :agent-name="'Default Agent'"
      :model-name="toolsStore.currentModel || 'deepseek-chat'"
      :connected="chatStore.isConnected"
    />

    <div class="app-body">
      <LeftSidebar @new-chat="handleNewChat" />

      <main class="chat-main">
        <ChatView />
      </main>

      <RightPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import { useToolsStore } from '@/stores/tools'
import AppHeader from '@/components/layout/AppHeader.vue'
import LeftSidebar from '@/components/layout/LeftSidebar.vue'
import RightPanel from '@/components/layout/RightPanel.vue'
import ChatView from '@/views/ChatView.vue'

const chatStore = useChatStore()
const toolsStore = useToolsStore()

function handleNewChat() {
  chatStore.clearMessages()
  chatStore.disconnect()
  chatStore.connect()
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
